"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

from cubicweb import Binary
from cubicweb.entities import AnyEntity, fetch_config
from cubicweb.utils import days_in_month, days_in_year

import pickle
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
    id = 'TimeSeries'

    _dtypes = {'Float': numpy.float64,
               'Integer': numpy.int32,
               'Boolean': numpy.bool,
               }
    @property
    def array(self):
        if not hasattr(self, '_array'):
            self._array = pickle.load(self.data)
        return self._array

    def dc_title(self):
        return self.name

    @property
    def is_constant(self):
        return self.granularity == u'constant'

    def dc_long_title(self):
        if self.is_constant:
            return self.req._(u'Constant time series (value: %.2f)' % self.first)
        return self.req._(u'Time series %s starting on %s with %d values' %
                          (self.name, self.start_date, self.length))

    def grok_data(self):
        """
        called in a before_{update|add}_entity_hook

        self.data is something such as an excel file or CSV data or a
        pickled numpy array. Ensure it a pickle numpy array before
        storing object in db.
        """
        try:
            filename = self.data.filename.lower()
        except AttributeError:
            numpy_array = self.data
        else:
            if filename.endswith('.csv'):
                numpy_array = self._numpy_from_csv(self.data)
            elif filename.endswith('.xls'):
                numpy_array = self._numpy_from_excel(self.data)
            elif filename.endswith('.txt'):
                pass
            else:
                raise ValueError('Unsupported file type %s' % self.data.filename)

        self.data = Binary()
        pickle.dump(numpy_array, self.data)

    def timestamped_array(self):
        date = self.start_date
        data = []
        for v in self.array:
            data.append((date, self.python_value(v)))
            date = self.get_next_date(date)
        return data

    def aggregated_value(self, start, end, mode):
        if self.granularity == 'constant':
            if mode == 'sum':
                raise ValueError("sum can't be computed with a constant granularity")
            return self.first
        if start < self.start_date:
            raise IndexError('%s date is before the time series\'s'
                             'start date (%s)' % (start, self.start_date))
        values = self.get_by_date(slice(start,end))
        coefs = numpy.ones(values.shape, float)
        start_frac =  self.calendar.get_frac_offset(start, self.granularity)
        end_frac =  self.calendar.get_frac_offset(end, self.granularity)
        coefs[0] -= start_frac
        if end_frac != 0:
            coefs[-1] -= 1-end_frac
        sigma = (values*coefs).sum()
        if mode == 'sum':
            return sigma
        elif mode == 'average':
            return sigma / sum(coefs)
        else:
            raise ValueError('unknown mode %s' % mode)


    def get_next_date(self, date):
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
        for date, value in data[1:]:
            previous_value = compressed_data[-1][1]
            if value != previous_value:
                compressed_data.append((date - delta, previous_value))
                compressed_data.append((date, value))
            elif date == last_date:
                compressed_data.append((date, value))
        return compressed_data

    def python_value(self, v):
        _dtypes = {'Float': float,
                   'Integer': int,
                   'Boolean': bool,
                   }
        return _dtypes[self.data_type](v)

    @property
    def dtype(self):
        return self._dtypes[self.data_type]

    @property
    def first(self):
        return self.array[0]

    @property
    def last(self):
        return self.array[-1]

    @property
    def length(self):
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
    def calendar(self):
        return ALL_CALENDARS[self.use_calendar]

    def get_values_between(self, start_date, end_date):
        values = []
        if start_date is None:
            start_date = self.start_date
        for tstamp, value in self.timestamped_array():
            if tstamp < start_date:
                continue
            elif end_date is not None and tstamp >= end_date:
                break
            values.append(value)
        return numpy.array(values)

    def _numpy_from_csv(self, file):
        sniffer = csv.Sniffer()
        raw_data = file.read()
        try:
            dialect = sniffer.sniff(raw_data, sniffer.preferred)
            has_header = sniffer.has_header(raw_data)
        except csv.Error, exc:
            self.exception('Problem sniffing file %s', file.filename)
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
                raise ValueError('Too many columns in %s' % file.filename)
            try:
                val = float(values[-1])
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', file.filename)
                    continue # assume there was a header
                else:
                    raise ValueError('unable to read value on line %d of %s' % (reader.line_num, file.filename))
            series.append(val)

        return numpy.array(series, dtype = self.dtype)


    def _numpy_from_excel(self, file):
        xl_data = file.read()
        wb = xlrd.open_workbook(filename=file.filename,
                                file_contents=xl_data
                                )
        sheet = wb.sheet_by_index(0)
        dates = []
        values = []
        for row in xrange(sheet.nrows):
            if sheet.cell_type(row, 0) != xlrd.XL_CELL_DATE:
                continue
            dates.append(sheet.cell_value(row, 0))
            values.append(sheet.cell_value(row, 1))
        if not dates or not values:
            raise ValueError('Unable to read a Timeseries in %s' % file.filename)
        return numpy.array(values, dtype=self.dtype)

    def get_absolute(self, index):
        index = self._make_relative_index(index)
        return self.get_relative(index)

    def get_by_date(self, date):
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

    def _make_relative_index(self, index):
        if isinstance(index, (int, float)):
            return int(floor(index - self._start_offset))
        elif type(index) is slice:
            if index.start is None:
                start = None
            else:
                start = int(floor(index.start - self._start_offset))
            if index.stop is None:
                stop = None
            else:
                stop = int(ceil(index.stop - self._start_offset))
                if stop > len(self.array):
                    raise IndexError('stop is too big')
            return slice(start, stop, index.step)
        else:
            raise TypeError('Unsupported index type %s' % type(index))

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
            self.__start_offset = self.calendar.get_offset(self.start_date, self.granularity)
            return self.__start_offset


class AbstractCalendar:

    def get_offset(self, date, granularity):
        offset_method = getattr(self, '_get_offset_%s'%granularity)
        return offset_method(date) + self.get_frac_offset(date, granularity)

    def get_frac_offset(self, date, granularity):
        frac_offset_method = getattr(self, '_get_frac_offset_%s'%granularity)
        return frac_offset_method(date)

    def _get_offset_15min(self, date):
        return (self.ordinal(date)*24+date.hour)*4 + self.seconds(date)//(15*60) 

    def _get_offset_hourly(self, date):
        return self.ordinal(date)*24+self.seconds(date)//3600 # XXX DST!

    def _get_offset_daily(self, date):
        return self.ordinal(date)

    def _get_offset_weekly(self, date):
        ordinal = self.ordinal(date) - 1
        return ordinal//7 

    def _get_offset_monthly(self, date):
        ordinal = self.ordinal(date)
        date = datetime.date.fromordinal(ordinal)
        return (date.year-1)*12+date.month-1

    def _get_offset_yearly(self, date):
        return date.year-1

    def _get_frac_offset_15min(self, date):
        rem = self.seconds(date) % (15*60)
        return rem / (15*60)

    def _get_frac_offset_hourly(self, date):
        rem = self.seconds(date) % 3600
        return rem/3600

    def _get_frac_offset_daily(self, date):
        rem = self.seconds(date)
        return rem/(3600*24)

    def _get_frac_offset_weekly(self, date):
        ordinal = self.ordinal(date) - 1 
        return (ordinal % 7) / 7 + self.seconds(date)/(3600*24*7)

    def _get_frac_offset_monthly(self, date):
        ordinal = self.ordinal(date)
        start_of_month = datetime.datetime(date.year, date.month, 1)
        delta = date - start_of_month
        seconds = delta.days*3600*24+delta.seconds
        return seconds / (days_in_month(start_of_month)*3600*24)

    def _get_frac_offset_yearly(self, date):
        frac_ordinal = self.ordinal(date) + self.seconds(date) / (3600*24)
        start_of_year = self.ordinal(datetime.datetime(date.year, 1, 1))
        return  (frac_ordinal-start_of_year) / days_in_year(date)

    def ordinal(self, date):
        """
        return the number of days since Jan 1st, 0001 (this one being having ordinal 0)
        """
        raise NotImplementedError

    def seconds(self, date):
        """
        return the number of seconds since the begining of the day for that date
        """
        return date.second+60*date.minute+3600*date.hour

    def day_of_week(self, date):
        """
        return the day of week for a given date as an integer (0 is monday -> 6 is sunday)
        """
        raise NotImplementedError


class GregorianCalendar(AbstractCalendar):
    def ordinal(self, date):
        return date.toordinal()

    def day_of_week(self, date):
        return date.weekday()



class GasCalendar(AbstractCalendar):
    def __init__(self):
        self.day_offset = datetime.timedelta(hours=6)
        self.year_month_offset = datetime.timedelta(days=31+30+31)

    def ordinal(self, date):
        return (date-self.day_offset).toordinal()

    def seconds(self, date):
        """
        return the number of seconds since the begining of the day for that date
        """
        date = date - self.day_offset
        return date.second+60*date.minute+3600*date.hour

    def day_of_week(self, date):
        return datetime.fromordinal(self.ordinal(date)).weekday()

    def _get_offset_yearly(self, date):
        return (date - self.year_month_offset - self.day_offset).year-1

    def _get_frac_offset_yearly(self, date):
        if date.month < 10:
            year = date.year - 1
            nb_days = days_in_year(date)
        else:
            year = date.year
            nb_days = days_in_year(date+self.year_month_offset)
        start_of_year = datetime.datetime(year, 10, 1, 6)
        delta = date - start_of_year
        return  (delta.days + delta.seconds/(3600*24)) / nb_days

    def _get_frac_offset_monthly(self, date):
        ordinal = self.ordinal(date)
        date_ = datetime.datetime.fromordinal(ordinal)
        start_of_month = datetime.datetime(date_.year, date_.month, 1, 6)
        delta = date - start_of_month
        seconds = delta.days*3600*24+delta.seconds
        return seconds / (days_in_month(start_of_month)*3600*24)


class NormalizedCalendar(AbstractCalendar):
    """
    Normalized calendar has 365 days, and starts on monday
    XXX: DST ?
    """
    def __init__(self):
        self.month_length = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        self.cum_month_length =  [0] + numpy.cumsum(self.month_length[:-1]).tolist()

    def ordinal(self, date):
        return (date.year-1)*365 + self.cum_month_length[date.month-1] + date.day-1

    def day_of_week(self, date):
        return (self.cum_month_length[date.month-1] + date.day-1) % 7

ALL_CALENDARS = {'gregorian': GregorianCalendar(),
                 'normalized': NormalizedCalendar(),
                 'gas': GasCalendar(),
                 }


class TSConstantExceptionBlock(AnyEntity):
    id = 'TSConstantExceptionBlock'
    fetch_attrs, fetch_order = fetch_config(['start_date', 'stop_date', 'value'])

    def dc_title(self):
        return u'[%s; %s] : %s' % (self.printable_value('start_date'),
                                   self.printable_value('stop_date'),
                                   self.printable_value('value'))

class TSConstantBlock(AnyEntity):
    id = 'TSConstantBlock'
    fetch_attrs, fetch_order = fetch_config(['start_date', 'value'])

    def dc_title(self):
        return self.req._(u'from %s: %s') % (self.printable_value('start_date'),
                                             self.printable_value('value'))


