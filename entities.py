"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from cubicweb import Binary
from cubicweb.entities import AnyEntity

import pickle
import csv

# TODO: remove datetime and use our own calendars
import datetime

import numpy
import xlrd

TIME_DELTAS = {'15 min': datetime.timedelta(minutes=15),
               'hourly': datetime.timedelta(hours=1),
               'daily': datetime.timedelta(days=1),
               'weekly': datetime.timedelta(weeks=1),
               'monthly': datetime.timedelta(days=30), # XXX
               'yearly': datetime.timedelta(days=365),
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
    
    def dc_long_title(self):
        return self.req._(u'Time series %s starting on %s with %d values' %
                          (self.name, self.start_date, self.length))

    def grok_data(self):
        """
        called in a before_{update|add}_entity_hook

        self.data is something such as an excel file or CSV data or a
        pickled numpy array. Ensure it a pickle numpy array before
        storing object in db.
        """
        filename = self.data.filename.lower()
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
        step = TIME_DELTAS[self.granularity]
        date = self.start_date
        data = []
        for v in self.array:
            data.append((date, v))
            date += step
        return data

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

class AbstractCalendar:
    
    def get_offset(self, date, granularity):
        if isinstance(date, str):
            date = self._parse_iso(date)
        offset_method = getattr(self, '_get_offset_%s'%granularity)
        return offset_method(date)

    def _get_offset_15min(self, date):
        return (date._ordinal*24+date.hour)*4 + date.minute//15

    def _get_offset_1h(self, date):
        return date._ordinal*24+date.hour # XXX DST!

    def _get_offset_1d(self, date):
        return date._ordinal

    def _get_offset_1w(self, date):
        return date._ordinal//7

    def _get_offset_1m(self, date):
        return (date.year-1)*12+date.month-1

    def _get_offset_1y(self, date):
        return date.year-1

    def _parse_iso(self, isodate):
        if len(isodate) == 8: # just a date
            date = isodate
            hour = 0
            minute = 0
            second = 0
        else:
            assert isodate[8] == 'T'
            date, time = isodate.split('T')
            hour, minute, sec = time.split(':')
            hour = int(hour)
            minute = int(minute)
            second = int(floor(float(sec)))
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])

        return DateTime(year, month, day, hour, minute, second, self, isodate)

    def date_from_ordinal_and_seconds(self, ordinal, seconds=0):
        """
        return a DateTime instance with the given ordinal ans seconds
        """
        year, day, month = self._ymd_from_ordinal(ordinal)
        hour, minute, second = self._hms_from_seconds(seconds)
        return DateTime(year, month, day, hour, minute, second, self)

    def _ymd_from_ordinal(self, ordinal):
        raise NotImplementedError
    
    def _hms_from_seconds(self, seconds):
        hour, rem_secs = divmod(seconds, 3600)
        minute, second = divmod(rem_secs, 60)
        return hour, minute, second

    def ordinal(self, date):
        """
        return the number of days since Jan 1st, 0001 (this one being having ordinal 0)
        """
        raise NotImplementedError

    def seconds(self, date):
        """
        return the number of seconds since the begining of the day for that date
        """
        return date.second+60*date.minute+3600*date.hour # XXX DST

    def day_of_week(self, date):
        """
        return the day of week for a given date as an integer (0 is monday -> 6 is sunday)
        """
        raise NotImplementedError
                  
class DateTime:
    """
    representation of a date + time, linked to a calendar.
    Meant to be immutable. Please consider the attributes read-only.

    XXX timezone management (core work required in calendar)
    
    """
    def __init__(self, year, month, day, hour, minute, second, calendar, iso_str=None):
        # boundary checks
        assert 0 < year < 3000
        assert 1 <= month <= 12
        assert 1 <= day <= 31 # could be enhanced
        assert 0 <= hour < 24
        assert 0 <= minute < 60
        assert 0 <= second < 60
        
        self._calendar = calendar
        if iso_str is None:
            iso_str = '%d%d%dT%d:%d:%d' % (year, month, day, hour, minute, second)
        self._iso_str = iso_str
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        # self._ordinal : integer giving the number of days since the epoch
        self._ordinal = calendar.ordinal(self)
        # self._seconds : integer giving the number of seconds since the beginning of day
        self._seconds = calendar.seconds(self)

    def __repr__(self):
        return "<DateTime %s>" % self._iso_str

    def as_iso(self):
        return self._iso_str

    def as_datetime(self):
        return datetime.datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)

    def day_of_week(self):
        return self._calendar.day_of_week(self)

    def __eq__(self, other):
        if not isinstance(other, DateTime):
            return NotImplemented
        # XXX can we safely use identity of calendars ?
        return self._calendar is other._calendar and \
               self._ordinal == other._ordinal and \
               self._seconds == other._seconds



    

class GregorianCalendar(AbstractCalendar):
    def ordinal(self, date):        
        return self.__as_datetime(date).toordinal()

    @staticmethod
    def __as_datetime(date):
        return datetime.datetime(date.year, date.month, date.day,
                                 date.hour, date.minute, date.second)

    def day_of_week(self, date):
        return self.__as_datetime(date).weekday()

    def _ymd_from_ordinal(self, ordinal):
        date = datetime.fromordinal(ordinal)
        return date.year, date.month, date.day
        
class GasCalendar(AbstractCalendar):
    pass

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

    def _ymd_from_ordinal(self, ordinal):
        year, days = divmod(ordinal, 365)
        year = year+1
        for month, cumdays in enumerate(self.cum_month_length):
            if days < cumdays:
                break
        day = days - self.cum_month_length[month-1] + 1
        return year, day, month

ALL_CALENDARS = {'gregorian': GregorianCalendar(),
                 'normalized': NormalizedCalendar(),
                 'gas': GasCalendar(),
                 }
