"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2009-2011 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division, with_statement

import pickle
import zlib
import csv
# TODO: remove datetime and use our own calendars
import datetime
from datetime import timedelta
from math import floor, ceil
from bisect import bisect_left
from itertools import izip
from cStringIO import StringIO

import numpy
import xlrd
from xlwt import Workbook

from logilab.common.date import days_in_month, days_in_year
from logilab.common.decorators import cached

from cubicweb import Binary, ValidationError
from cubicweb.selectors import is_instance, ExpectedValueSelector
from cubicweb.view import EntityAdapter
from cubicweb.entities import AnyEntity, fetch_config

from cubes.timeseries.calendars import (
    get_calendar, TIME_DELTAS,
    timedelta_to_days, timedelta_to_seconds, datetime_to_seconds)
from cubes.timeseries.utils import get_formatter

_ = unicode

def boolint(value):
    """ ensuring such boolean like values
    are properly summable and plotable
    0, 0.0 => 0
    1, 42.0 => 11
    """
    return int(bool(float(value)))


class TimeSeries(AnyEntity):
    __regid__ = 'TimeSeries'
    fetch_attrs, fetch_order = fetch_config(['data_type', 'unit', 'granularity', 'start_date'])

    _dtypes_in = {'Float': numpy.float64,
                  'Integer': numpy.int32,
                  'Boolean': numpy.bool}
    _dtypes_out = {'Float': float,
                   'Integer': int,
                   'Boolean': boolint}

    @property
    #@cached(cacheattr='_array') XXX once lgc 0.56 is out
    def array(self):
        if not hasattr(self, '_array'):
            raw_data = self.data.getvalue()
            try:
                raw_data = zlib.decompress(raw_data)
            except zlib.error:
                # assume uncompressed data
                pass
            self._array = pickle.loads(raw_data)
        return self._array

    def dc_title(self):
        return 'TS %s' % self.eid #pylint:disable-msg=E1101

    @property
    def is_constant(self):
        return self.granularity == u'constant' #pylint:disable-msg=E1101

    def dc_long_title(self):
        if self.is_constant:
            return self._cw._(u'Constant time series (value: %s)' % self._cw.format_float(self.first))
        return self._cw._(u'Time series %s starting on %s with %d values' %
                          (self.dc_title(), self.start_date, self.count)) #pylint:disable-msg=E1101

    def grok_data(self):
        """
        called in a before_{update|add}_entity_hook

        self.data is something such as an excel file or CSV data or a pickled
        numpy array. Ensure it's a pickle numpy array before storing object in
        db.
        """
        #pylint:disable-msg=E1101,E0203
        try:
            filename = self.data.filename.lower()
        except AttributeError:
            # XXX this is a bit dangerous as we break encapsulation doing this
            #     did the provider not cheat about the inner data type ?
            #     we should probably check it
            data = self.data
            if isinstance(data, Binary):
                return
            numpy_array = data
        else:
            if filename.endswith('.csv'):
                numpy_array = self._numpy_from_csv(self.data, filename)
            elif filename.endswith('.xls'):
                numpy_array = self._numpy_from_excel(self.data, filename)
            elif filename.endswith('.txt'):
                numpy_array = self._numpy_from_txt(self.data, filename)
            else:
                raise ValueError('Unsupported file type %s' % self.data.filename)

        if numpy_array.ndim != 1:
            raise ValidationError(self.eid,
                                  {'data': _('data must be a 1-dimensional array')})
        if numpy_array.size == 0:
            raise ValidationError(self.eid,
                                  {'data': _('data must have at least one value')})
        data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        data.write(compressed_data)
        self.cw_edited['data'] = data
        self._array = numpy_array

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
        return get_next_date(self.granularity, date)

    def get_next_month(self, date):
        return get_next_month(date)

    def get_next_year(self, date):
        return get_next_year(date)

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
        as an entry/input method as Boolean really should be
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


    # import/conversion method

    def _numpy_from_txt(self, file, filename):
        try:
            return numpy.array([float(x.strip().split()[-1]) for x in file],
                               dtype=self.dtype)
        except ValueError:
            raise ValueError('invalid data in %s (expecting one number per line '
                             '(with optionally a date in the first column), '
                             'with . as the decimal separator)' % filename)

    def _snif_csv_dialect(self, file):
        sniffer = csv.Sniffer()
        raw_data = file.read()
        try:
            dialect = sniffer.sniff(raw_data, sniffer.preferred)
            has_header = sniffer.has_header(raw_data)
        except csv.Error, exc:
            self.exception('Problem sniffing file %s', file.filename) #pylint:disable-msg=E1101
            dialect = csv.excel
            has_header = False
        file.seek(0)
        return dialect, has_header

    def _numpy_from_csv(self, file, filename, dialect=None, has_header=False):
        if dialect is None:
            dialect, has_header = self._snif_csv_dialect(file)
        else:
            assert dialect in csv.list_dialects()
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        # TODO: check granularity if we have a date column
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        th_sep = prefs.thousands_separator or ''
        for line, values in enumerate(reader):
            if len(values) not in (1, 2):
                raise ValueError('Too many columns in %s' % filename)
            try:
                strval = values[-1].replace(th_sep, '').replace(dec_sep, '.')
                val = float(strval)
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', filename) #pylint:disable-msg=E1101
                    continue # assume there was a header
                else:
                    raise ValueError('Invalid data type for value %s on line %d of %s' %
                                     (values[-1], reader.line_num, filename))
            series.append(val)
        return numpy.array(series, dtype=self.dtype)

    def _numpy_from_excel(self, file, filename):
        xl_data = file.read()
        wb = xlrd.open_workbook(filename=file.filename,
                                file_contents=xl_data)
        sheet = wb.sheet_by_index(0)
        values = []
        col = sheet.ncols - 1
        for row in xrange(sheet.nrows):
            cell_value = sheet.cell_value(row, col)
            try:
                cell_value = float(cell_value)
            except ValueError:
                raise ValueError('Invalid data type in cell (%d, %d) of %s' % (row, col, filename))
            values.append(cell_value)
        if not values:
            raise ValueError('Unable to read a Timeseries in %s' % filename)
        return numpy.array(values, dtype=self.dtype)


class NonPeriodicTimeSeries(TimeSeries):
    __regid__ = 'NonPeriodicTimeSeries'
    fetch_attrs, fetch_order = fetch_config(['data_type', 'unit', 'granularity'])

    is_constant = False

    @property
    @cached
    def timestamps_array(self):
        # XXX turn into datetime here ?
        raw_data = self.timestamps.getvalue()
        raw_data = zlib.decompress(raw_data)
        return pickle.loads(raw_data)

    @cached
    def timestamped_array(self):
        data = []
        for t, v in izip(self.timestamps_array, self.array):
            data.append((self.calendar.timestamp_to_datetime(t), self.output_value(v)))
        return data

    @property
    @cached
    def start_date(self):
        return self.calendar.timestamp_to_datetime(self.timestamps_array[0])

    def get_next_date(self, date):
        index = bisect_left(self.timestamps_array, self.calendar.datetime_to_timestamp(date))
        # XXX what if out of bound
        return self.calendar.timestamp_to_datetime(self.timestamps_array[index])

    def get_rel_index(self, date, offset=-1):
        timestamp = self.calendar.datetime_to_timestamp(date)
        array = self.timestamps_array
        idx = bisect_left(array, timestamp)
        # unless this is an exact match, add offset if any to mimick periodic ts
        # behaviour
        if timestamp != array[idx]:
            return max(idx + offset, 0)
        return idx

    def get_by_date(self, date, with_dates=False):
        #pylint:disable-msg=E1101
        if type(date) is slice:
            assert date.step is None
            if date.start is None:
                start = None
            else:
                start = self.get_rel_index(date.start, -1)
            if date.stop is None:
                stop = None
            else:
                stop = self.get_rel_index(date.stop, 0)
            index = slice(start, stop, None)
        else:
            index = self.get_rel_index(date)
        return self.get_relative(index, with_dates)

    def get_duration_in_days(self, date):
        idx = self.get_rel_index(date)
        array = self.timestamped_array()
        return timedelta_to_days(array[idx+1][0] - array[idx][0])

    def get_frac_offset(self, date):
        idx = self.get_rel_index(date)
        array = self.timestamped_array()
        try:
            totalsecs = timedelta_to_seconds(array[idx+1][0] - array[idx][0])
        except IndexError:
            # date out of bound, consider previous interval
            totalsecs = timedelta_to_seconds(array[idx][0] - array[idx-1][0])
        deltasecs = timedelta_to_seconds(date - array[idx][0])
        return deltasecs / max(totalsecs, deltasecs)

    @property
    def _start_offset(self):
        return self.calendar.get_offset(self.start_date, self.granularity)

    def get_offset(self, datetime):
        timestamp = self.calendar.datetime_to_timestamp(datetime)
        array = self.timestamps_array
        idx = bisect_left(array, timestamp)
        return idx

    def grok_data(self):
        # XXX when data is a csv/txt/xl file, we want to read timestamps in there to
        # XXX hooks won't catch change to timestamps
        super(NonPeriodicTimeSeries, self).grok_data()
        numpy_array = self.grok_timestamps()
        data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        data.write(compressed_data)
        self.cw_edited['timestamps'] = data
        self._timestamps_array = numpy_array

    def grok_timestamps(self):
        timestamps = self.timestamps
        if len(timestamps) != self.count:
            raise ValueError('data/timestamps vectors size mismatch')
        if isinstance(timestamps[0], (datetime.datetime, datetime.date)):
            timestamps = [self.calendar.datetime_to_timestamp(v) for v in timestamps]
        else:
            assert isinstance(timestamps[0], (int, float))
        tstamp_array = numpy.array(timestamps, dtype=numpy.float64)
        if not (tstamp_array[:-1] < tstamp_array[1:]).all():
            raise ValueError('time stamps must be an strictly ascendant vector')
        return tstamp_array



class TimeSeriesExportAdapter(EntityAdapter):
    __regid__ = 'ITimeSeriesExporter'
    __abstract__ = True
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')

    def export(self):
        raise NotImplementedError

class mimetype(ExpectedValueSelector):

    def _get_value(self, cls, req, **kwargs):
        return kwargs.get('mimetype')

class TimeSeriesCSVexport(TimeSeriesExportAdapter):
    """ export timestamped array to paste-into-excel-friendly csv """
    __select__ = TimeSeriesExportAdapter.__select__ & mimetype('text/csv')

    def export(self):
        entity = self.entity
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        out = StringIO()
        dateformat, _numformat, _numformatter = get_formatter(self._cw, entity)
        writer = csv.writer(out, dialect='excel', delimiter='\t')
        for date, value in entity.timestamped_array():
            outvalue = str(entity.output_value(value)).replace('.', dec_sep)
            writer.writerow([date.strftime(dateformat), outvalue])
        return out.getvalue()

class TimeSeriesXLExport(TimeSeriesExportAdapter):
    __select__ = TimeSeriesExportAdapter.__select__ & mimetype('application/vnd.ms-excel')

    def export(self):
        # XXX timestamps ?
        entity = self.entity
        tsbox = entity.reverse_ts_variant[0]
        workbook = Workbook() # XXX XLSX
        sheet = workbook.add_sheet(('TS_%s' % tsbox.name)[:31])
        outrows = []
        class Writer(object):
            def write(self, data):
                """ callback to comply to workbook.save api """
                outrows.append(data)
        for rownum, val in enumerate(entity.array):
            sheet.write(rownum, 0, entity.output_value(val))
        workbook.save(Writer())
        return ''.join(outrows)

def get_next_date(granularity, date):
    #pylint:disable-msg=E1101
    if granularity in TIME_DELTAS:
        return date + TIME_DELTAS[granularity]
    elif granularity == 'monthly':
        return get_next_month(date)
    elif granularity == 'yearly':
        return get_next_year(date)
    else:
        raise ValueError(granularity)

def get_next_month(date):
    year = date.year
    month = date.month
    day = date.day
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1
    while True:
        try:
            newdate = datetime.date(year, month, day)
        except ValueError:
            day -= 1
        else:
            break

    if isinstance(date, datetime.datetime):
        return datetime.datetime.combine(newdate, date.time())
    else:
        return date

def get_next_year(date):
    """ date => date, datetime => datetime
    if date == bisextile year, february's last
    day may be adjusted to yield a valid date
    but NOT the other way around
    """
    year = date.year + 1
    month = date.month
    day = date.day
    try:
        newdate = datetime.date(year, month, day)
    except ValueError:
        # date was last day of a bisextile year's february
        newdate = datetime.date(year, month, day - 1)
    if isinstance(date, datetime.datetime):
        return datetime.datetime.combine(newdate, date.time())
    else:
        return date
