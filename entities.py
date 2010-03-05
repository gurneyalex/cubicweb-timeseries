"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

from cubicweb import Binary
from cubicweb.entities import AnyEntity, fetch_config

from cubes.timeseries.calendars import get_calendar

import pickle
import zlib
import csv
from math import floor, ceil

# TODO: remove datetime and use our own calendars
import datetime

import numpy
import xlrd

TIME_DELTAS = {'15min': datetime.timedelta(minutes=15),
               'hourly': datetime.timedelta(hours=1),
               'daily': datetime.timedelta(days=1),
               'weekly': datetime.timedelta(weeks=1),
               # monthly and yearly do not have a fixed length
               }

class TimeSeries(AnyEntity):
    __regid__ = 'TimeSeries'

    _dtypes = {'Float': numpy.float64,
               'Integer': numpy.int32,
               'Boolean': numpy.bool,
               }
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

        self.data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        self.data.write(compressed_data)

    def timestamped_array(self):
        date = self.start_date #pylint:disable-msg=E1101
        data = []
        for v in self.array:
            data.append((date, self.python_value(v)))
            date = self.get_next_date(date)
        return data

    @property
    def end_date(self):
        return self.get_next_date(self.timestamped_array()[-1][0])

    def aggregated_value(self, start, end, mode):
        #pylint:disable-msg=E1101
        if self.granularity == 'constant':
            if mode == 'sum':
                raise ValueError("sum can't be computed with a constant granularity")
            return start, self.first
        if end < self.start_date:
            raise IndexError("%s date is before the time series's "
                             "start date (%s)" % (start, self.start_date))
        values = self.get_by_date(slice(start, end))
        if len(values) == 0:
            raise IndexError()
        if mode == 'last':
            last_index = self.get_rel_index(end - datetime.timedelta(seconds=1))
            tstamp = self.timestamped_array()[last_index][0]
            return tstamp, values[-1]
        coefs = numpy.ones(values.shape, float)
        start_frac =  self.calendar.get_frac_offset(start, self.granularity)
        end_frac =  self.calendar.get_frac_offset(end, self.granularity)
        coefs[0] -= start_frac
        if end_frac != 0:
            coefs[-1] -= 1-end_frac
        sigma = (values*coefs).sum()
        if mode == 'sum':
            return start, sigma
        elif mode == 'average':
            return start, sigma / sum(coefs)
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
        """
        eliminates duplicated values in piecewise constant timeseries
        """
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
        _dtypes = {'Float': float,
                   'Integer': int,
                   'Boolean': bool,
                   }
        return _dtypes[self.data_type](v) #pylint:disable-msg=E1101

    @property
    def dtype(self):
        return self._dtypes[self.data_type] #pylint:disable-msg=E1101

    @property
    def first(self):
        return self.array[0]

    @property
    def last(self):
        return self.array[-1]

    @property
    def count(self):
        return self.array.size

    @property
    def min(self):
        return self.array.min()

    @property
    def max(self):
        return self.array.max()

    @property
    def sum(self):
        return self.array.sum()

    @property
    def average(self):
        return self.array.mean()

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

    def _numpy_from_txt(self, file, filename):
        try:
            return numpy.array([float(x.strip()) for x in file])
        except ValueError:
            raise ValueError('invalid data in %s (expecting one number per line, with . as the decimal separator)', filename)

    def _numpy_from_csv(self, file, filename):
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
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        # TODO: check granularity if we have a date column
        for line, values in enumerate(reader):
            if len(values) not in (1, 2):
                raise ValueError('Too many columns in %s' % filename)
            try:
                val = float(values[-1])
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', filename) #pylint:disable-msg=E1101
                    continue # assume there was a header
                else:
                    raise ValueError('unable to read value on line %d of %s' % (reader.line_num, filename))
            series.append(val)

        return numpy.array(series, dtype = self.dtype)


    def _numpy_from_excel(self, file, filename):
        xl_data = file.read()
        wb = xlrd.open_workbook(filename=file.filename,
                                file_contents=xl_data)
        sheet = wb.sheet_by_index(0)
        values = []
        for row in xrange(sheet.nrows):
            cell_value = sheet.cell_value(row, 0)
            try:
                float(cell_value)
            except ValueError:
                raise ValueError('Invalid data type in cell (%d, %d) of %s' % (row, 0, filename))
            values.append(sheet.cell_value(row, 0))
        if not values:
            raise ValueError('Unable to read a Timeseries in %s' % filename)
        return numpy.array(values, dtype=self.dtype)

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
                stop = int(ceil(abs_index.stop - self._start_offset))
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



#
# Below is some work in progress, not yet used in Pylos
#

class TSConstantExceptionBlock(AnyEntity):
    __regid__ = 'TSConstantExceptionBlock'
    fetch_attrs, fetch_order = fetch_config(['start_date', 'stop_date', 'value'])

    def dc_title(self):
        return u'[%s; %s] : %s' % (self.printable_value('start_date'),
                                   self.printable_value('stop_date'),
                                   self.printable_value('value'))

class TSConstantBlock(AnyEntity):
    __regid__ = 'TSConstantBlock'
    fetch_attrs, fetch_order = fetch_config(['start_date', 'value'])

    def dc_title(self):
        return self._cw._(u'from %s: %s') % (self.printable_value('start_date'),
                                             self.printable_value('value'))


