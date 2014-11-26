"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2009-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

# TODO: remove datetime and use our own calendars
from datetime import timedelta
from math import floor, ceil


import numpy

from logilab.common.decorators import cached

from cubicweb.entities import AnyEntity, fetch_config

from cubes.timeseries.calendars import get_calendar, TIME_DELTAS
from cubes.timeseries.entities import utils, abstract

_ = unicode



class TimeSeries(abstract.AbstractTSMixin, AnyEntity):
    __regid__ = 'TimeSeries'
    fetch_attrs, cw_fetch_order = fetch_config(['data_type', 'unit', 'granularity', 'start_date'])
    _dtypes_in = {'Float': numpy.float64,
                  'Integer': numpy.int32,
                  'Boolean': numpy.bool}
    _dtypes_out = {'Float': float,
                   'Integer': int,
                   'Boolean': utils.boolint}


    def dc_title(self):
        return u'TS %s' % self.eid

    @property
    def is_constant(self):
        return self.granularity == u'constant'

    def dc_long_title(self):
        if self.is_constant:
            return self._cw._(u'Constant time series (value: %s)' % self._cw.format_float(self.first))
        return self._cw._(u'Time series %s starting on %s with %d values' %
                          (self.dc_title(), self.start_date, self.count))


    @cached
    def timestamped_array(self):
        date = self.start_date #pylint:disable-msg=E1101
        data = []
        for v in self.array:
            data.append((date, self.output_value(v)))
            date = self.get_next_date(date)
        return data

    @property
    def end_date(self):
        if self.granularity in TIME_DELTAS:
            return self.start_date + self.count * TIME_DELTAS[self.granularity]
        return self.get_next_date(self.timestamped_array()[-1][0])

    def _check_intervals(self, intervals):
        for start, end in intervals:
            if end < self.start_date:
                raise IndexError("%s date is before the time series's "
                                 "start date (%s)" % (end, self.start_date))

    supported_modes = frozenset(('sum', 'average', 'weighted_average',
                                 'last', 'sum_realized', 'max'))
    def aggregated_value(self, intervals, mode, use_last_interval=False):
        #pylint:disable-msg=E1101
        assert mode in self.supported_modes, 'unsupported mode'
        if use_last_interval and mode != 'last':
            raise AssertionError, '"use_last_interval" may be True only if mode is "last"'
        if self.is_constant:
            if mode == 'sum':
                raise ValueError("sum can't be computed with a constant granularity")
            return intervals[0][0], self.first
        if mode == 'last' and len(intervals) != 1 and not use_last_interval:
            raise ValueError('"last" aggregation method cannot be used with more than 1 interval')
        self._check_intervals(intervals)
        values = []
        flat_values = []
        for start, end in intervals:
            interval_date_values = self.get_by_date(slice(start, end), with_dates=True)
            values.append((start, end, numpy.array(interval_date_values)))
            interval_values = [date_value[1] for date_value in interval_date_values]
            flat_values += interval_values
            if len(interval_values) == 0:
                raise IndexError()
        flat_values = numpy.array(flat_values)
        start = intervals[0][0]
        end = intervals[-1][1]
        if mode == 'last':
            last_index = self.get_rel_index(end - timedelta(seconds=1))
            tstamp = end - timedelta(seconds=1)
            value = self.timestamped_array()[last_index][1]
            return tstamp, value
        elif mode == 'max':
            return start, flat_values.max()
        elif mode == 'sum_realized':
            return start, flat_values.sum()
        elif mode in ('sum', 'average', 'weighted_average'):
            nums = []
            denoms = []
            for start, end, interval_date_values in values:

                interval_values = interval_date_values[:,1]
                coefs = numpy.ones(interval_values.shape, float)
                start_frac = self.get_frac_offset(start)
                end_frac = self.get_frac_offset(end)
                coefs[0] -= start_frac
                if end_frac != 0:
                    coefs[-1] -= 1 - end_frac

                if mode == 'weighted_average':
                    interval_dates = interval_date_values[:,0]
                    weights = [self.get_duration_in_days(date)
                               for date in interval_dates]
                    coefs *= weights

                num = (interval_values * coefs).sum()
                nums.append(num)
                denom = coefs.sum()
                denoms.append(denom)

            if mode == 'sum':
                return start, sum(nums)
            elif mode in ('average', 'weighted_average'):
                return start, sum(nums) / sum(denoms)
        else:
            raise ValueError('unknown mode %s' % mode)

    def get_offset(self, date):
        return self.calendar.get_offset(date, self.granularity)

    def get_frac_offset(self, date):
        return self.calendar.get_frac_offset(date, self.granularity)

    def get_duration_in_days(self, date):
        return self.calendar.get_duration_in_days(self.granularity, date)

    def get_next_date(self, date):
        return utils.get_next_date(self.granularity, date)

    def get_next_month(self, date):
        return utils.get_next_month(date)

    def get_next_year(self, date):
        return utils.get_next_year(date)

    def compressed_timestamped_array(self):
        """ eliminates duplicated values in piecewise constant timeseries """
        data = self.timestamped_array()
        compressed_data = [data[0]]
        delta = timedelta(seconds=1)
        last_date = data[-1][0]
        if len(data) != 1:
            for date, value in data[1:]:
                previous_value = compressed_data[-1][1]
                if value != previous_value:
                    compressed_data.append((date - delta, previous_value))
                    compressed_data.append((date, value))
                if date == last_date:
                    if value != previous_value:
                        compressed_data.append((date, value))
                        compressed_data.append((self.get_next_date(date), value))
                    else:
                        compressed_data.append((self.get_next_date(date), value))
        else:
            end_date = self.get_next_date(last_date)
            value = data[-1][1]
            compressed_data.append((end_date, value))
        return compressed_data

    def python_value(self, v):
        self.warning('python_value is deprecated, use output_value instead')
        return self.output_value(v)

    def output_value(self, v):
        """ use this for external representation purposes, but NOT
        as an entry/input method as Boolean really should be
        a boolean internally
        """
        return self._dtypes_out[self.data_type](v) #pylint:disable-msg=E1101

    def input_value(self, v):
        """ if you need to update some data piecewise, use this
        to get it to the correct input type """
        return self._dtypes_in[self.data_type](v) #pylint:disable-msg=E1101

    @property
    def dtype(self):
        """ provides the correct python data type
        for input purposes
        """
        return self._dtypes_in.get(self.data_type, numpy.float64)

    @property
    def safe_unit(self):
        # XXX maybe we just want '' as default ?
        if self.unit is None:
            return u''
        return self.unit

    @property
    def first(self):
        return self.array[0]

    @property
    def first_unit(self):
        return '%s%s' % (self.first, self.safe_unit)

    @property
    def last(self):
        return self.array[-1]

    @property
    def last_unit(self):
        return '%s%s' % (self.last, self.safe_unit)

    @property
    def count(self):
        return self.array.size

    @property
    def min(self):
        return self.array.min()

    @property
    def min_unit(self):
        return '%s%s' % (self.output_value(self.min), self.safe_unit)

    @property
    def max(self):
        return self.array.max()

    @property
    def max_unit(self):
        return '%s%s' % (self.output_value(self.max), self.safe_unit)

    @property
    def sum(self):
        return self.array.sum()

    @property
    def sum_unit(self):
        return '%s%s' % (self.sum, self.safe_unit)

    @property
    def average(self):
        return self.array.mean()

    @property
    def average_unit(self):
        return '%s%s' % (self.average, self.safe_unit)

    @property
    def use_calendar(self):
        return 'gregorian'

    @property
    def calendar(self):
        return get_calendar(self.use_calendar) #pylint:disable-msg=E1101

    def get_values_between(self, start_date, end_date):
        #pylint:disable-msg=E1101
        if start_date is None:
            start_date = self.start_date
        if self.is_constant:
            return [(start_date, self.first), ]
        values = []
        for tstamp, value in self.timestamped_array():
            if tstamp < start_date:
                continue
            elif end_date is not None and tstamp >= end_date:
                break
            values.append((tstamp, value))
        return values

    def get_absolute(self, abs_index, with_dates=False):
        index = self._make_relative_index(abs_index)
        return self.get_relative(index, with_dates)


    def get_rel_index(self, date):
        abs_index = self.get_offset(date)
        return self._make_relative_index(abs_index)

    def get_by_date(self, date, with_dates=False):
        #pylint:disable-msg=E1101
        if type(date) is slice:
            assert date.step is None
            if self.is_constant:
                date = slice(None, None)
            if date.start is None:
                start = None
            else:
                #start = self.get_rel_index(date.start)
                start = self.get_offset(date.start)
            if date.stop is None:
                stop = None
            else:
                #stop = self.get_rel_index(date.stop)
                stop = self.get_offset(date.stop)
            index = slice(start, stop, None)
        else:
            #index = self.get_rel_index(date)
            index = self.get_offset(date)
        #return self.get_relative(index, with_dates)
        return self.get_absolute(index, with_dates)

    def _make_relative_index(self, abs_index):
        if isinstance(abs_index, (int, float)):
            return int(floor(abs_index - self._start_offset))
        elif type(abs_index) is slice:
            if abs_index.start is None:
                start = None
            else:
                start = max(0, int(floor(abs_index.start - self._start_offset)))
            if abs_index.stop is None:
                stop = None
            else:
                stop = max(0, int(ceil(abs_index.stop - self._start_offset)))
            if start > len(self.array):
                raise IndexError('start is too big')
            return slice(start, stop, abs_index.step)
        else:
            raise TypeError('Unsupported index type %s' % type(abs_index))

    def get_relative(self, index, with_dates=False):
        try:
            if with_dates:
                return self.timestamped_array()[index]
            else:
                return self.array[index]
        except IndexError, exc:
            raise IndexError(exc.args + (index,))

    @property
    @cached
    def _start_offset(self):
        return self.get_offset(self.start_date)



