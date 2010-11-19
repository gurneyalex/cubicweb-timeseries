"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division, with_statement

from cStringIO import StringIO

import pickle
import zlib
import csv
from math import floor, ceil

# TODO: remove datetime and use our own calendars
import datetime

import numpy
import xlrd
from xlwt import Workbook

from cubicweb import Binary, ValidationError
from cubicweb.selectors import is_instance, ExpectedValueSelector
from cubicweb.view import EntityAdapter
from cubicweb.entities import AnyEntity, fetch_config

from cubes.timeseries.calendars import get_calendar
from cubes.timeseries.utils import numpy_val_map, get_formatter

_ = unicode

TIME_DELTAS = {'15min': datetime.timedelta(minutes=15),
               'hourly': datetime.timedelta(hours=1),
               'daily': datetime.timedelta(days=1),
               'weekly': datetime.timedelta(weeks=1),
               # monthly and yearly do not have a fixed length
               }

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

        self.data is something such as an excel file or CSV data or a
        pickled numpy array. Ensure it a pickle numpy array before
        storing object in db.
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
        self.data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        self.data.write(compressed_data)
        self._array = numpy_array

    def timestamped_array(self):
        if not hasattr(self, '_timestamped_array'):
            date = self.start_date #pylint:disable-msg=E1101
            data = []
            for v in self.array:
                data.append((date, self.output_value(v)))
                date = self.get_next_date(date)
            self._timestamped_array = data
        return self._timestamped_array

    @property
    def end_date(self):
        if self.granularity in TIME_DELTAS:
            return self.start_date + self.count*TIME_DELTAS[self.granularity]
        return self.get_next_date(self.timestamped_array()[-1][0])

    def _check_intervals(self, intervals):
        for start, end in intervals:
            if end < self.start_date:
                raise IndexError("%s date is before the time series's "
                                 "start date (%s)" % (end, self.start_date))

    def aggregated_value(self, intervals, mode, use_last_interval=False):
        #pylint:disable-msg=E1101
        assert mode in ('sum', 'average', 'last', 'sum_realized', 'max'), 'unsupported mode'
        if use_last_interval and mode != 'last':
            raise AssertionError, '"use_last_interval" may be True only if mode is "last"'
        if self.granularity == 'constant':
            if mode == 'sum':
                raise ValueError("sum can't be computed with a constant granularity")
            return intervals[0][0], self.first
        if mode == 'last' and len(intervals) != 1 and not use_last_interval:
            raise ValueError('"last" aggregation method cannot be used with more than 1 interval')
        self._check_intervals(intervals)
        values = []
        flat_values = []
        for start, end in intervals:
            interval_values = self.get_by_date(slice(start, end))
            values.append((start, end, interval_values))
            flat_values += interval_values.tolist()
            if len(interval_values) == 0:
                raise IndexError()
        flat_values = numpy.array(flat_values)
        start = intervals[0][0]
        end = intervals[-1][1]
        if mode == 'last':
            last_index = self.get_rel_index(end - datetime.timedelta(seconds=1))
            tstamp = self.timestamped_array()[last_index][0]
            return tstamp, flat_values[-1]
        elif mode == 'sum':
            sigmas = []
            for start, end, interval_values in values:
                coefs = numpy.ones(interval_values.shape, float)
                start_frac =  self.calendar.get_frac_offset(start, self.granularity)
                end_frac =  self.calendar.get_frac_offset(end, self.granularity)
                coefs[0] -= start_frac
                if end_frac != 0:
                    coefs[-1] -= 1-end_frac
                sigma = (interval_values*coefs).sum()
                sigmas.append(sigma)
            return start, sum(sigmas)
        elif mode == 'average':
            return start, flat_values.mean()
        elif mode == 'max':
            return start, flat_values.max()
        elif mode == 'sum_realized':
            return start, flat_values.sum()
        else:
            raise ValueError('unknown mode %s' % mode)


    def get_next_date(self, date):
        #pylint:disable-msg=E1101
        if self.granularity in TIME_DELTAS:
            return date + TIME_DELTAS[self.granularity]
        elif self.granularity == 'monthly':
            return self.get_next_month(date)
        elif self.granularity == 'yearly':
            return self.get_next_year(date)
        else:
            raise ValueError(self.granularity)

    def get_next_month(self, date):
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

    def get_next_year(self, date):
        year = date.year + 1
        month = date.month
        day = date.day

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


    def compressed_timestamped_array(self):
        """ eliminates duplicated values in piecewise constant timeseries """
        data = self.timestamped_array()
        compressed_data = [data[0]]
        delta = datetime.timedelta(seconds=1)
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
        if self.granularity == 'constant':
            return [(start_date, self.first), ]
        values = []
        for tstamp, value in self.timestamped_array():
            if tstamp < start_date:
                continue
            elif end_date is not None and tstamp >= end_date:
                break
            values.append((tstamp, value))
        return values

    def get_absolute(self, abs_index):
        index = self._make_relative_index(abs_index)
        return self.get_relative(index)

    def get_rel_index(self, date):
        abs_index = self.calendar.get_offset(date, self.granularity) #pylint:disable-msg=E1101
        return self._make_relative_index(abs_index)

    def get_by_date(self, date):
        #pylint:disable-msg=E1101
        if type(date) is slice:
            assert date.step is None
            if date.start is None:
                start = None
            else:
                start = self.calendar.get_offset(date.start, self.granularity)
            if date.stop is None:
                stop = None
            else:
                stop = self.calendar.get_offset(date.stop, self.granularity)
            index = slice(start, stop, None)
        else:
            index = self.calendar.get_offset(date, self.granularity)
        return self.get_absolute(index)

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

    def get_relative(self, index):
        try:
            return self.array[index]
        except IndexError, exc:
            raise IndexError(exc.args+(index,))

    @property
    def _start_offset(self):
        try:
            return self.__start_offset
        except AttributeError:
            self.__start_offset = self.calendar.get_offset(self.start_date, self.granularity) #pylint:disable-msg=E1101
            return self.__start_offset

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


class TimeSeriesExportAdapter(EntityAdapter):
    __regid__ = 'ITimeSeriesExporter'
    __abstract__ = True

    def export(self):
        raise NotImplementedError

class mimetype(ExpectedValueSelector):

    def _get_value(self, cls, req, **kwargs):
        return kwargs.get('mimetype')

class TimeSeriesCSVexport(TimeSeriesExportAdapter):
    """ export timestamped array to paste-into-excel-friendly csv """
    __select__ = is_instance('TimeSeries') & mimetype('text/csv')

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
        workbook = Workbook()
        sheet = workbook.add_sheet(('TS_%s' % tsbox.name)[:31])
        outrows = []
        class Writer(object):
            def write(self, data):
                """ callback to comply to workbook.save api """
                outrows.append(data)
        for rownum, val in enumerate(entity.array):
            sheet.write(rownum, 0, numpy_val_map(val))
        workbook.save(Writer())
        return ''.join(outrows)


