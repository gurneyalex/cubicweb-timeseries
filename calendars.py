from __future__ import division
import numpy
import math
import datetime

from logilab.common.date import days_in_month, days_in_year
try:
    from logilab.common.date import (datetime_to_seconds,
                                     timedelta_to_days, timedelta_to_seconds)
except ImportError:
    def datetime_to_seconds(date):
        return date.second+60*date.minute + 3600*date.hour
    def timedelta_to_days(delta):
        return delta.days + delta.seconds / (3600*24)
    def timedelta_to_seconds(delta):
        return delta.days*(3600*24) + delta.seconds

__ALL_CALENDARS = {}

TIME_DELTAS = {'15min': datetime.timedelta(minutes=15),
               'hourly': datetime.timedelta(hours=1),
               'daily': datetime.timedelta(days=1),
               'weekly': datetime.timedelta(weeks=1),
               # constant, monthly and yearly do not have a fixed length
               }

def register_calendar(name, calendar):
    __ALL_CALENDARS[name] = calendar

def get_calendar(name):
    return __ALL_CALENDARS[name]

def get_all_calendars():
    return __ALL_CALENDARS.values()


class AbstractCalendar(object):
    seconds = staticmethod(datetime_to_seconds)

    def get_offset(self, date, granularity):
        offset_method = getattr(self, '_get_offset_%s' % granularity.replace('-', '_'))
        return offset_method(date) + self.get_frac_offset(date, granularity)

    def get_frac_offset(self, date, granularity):
        frac_offset_method = getattr(self, '_get_frac_offset_%s' % granularity.replace('-', '_'))
        return frac_offset_method(date)

    def _get_offset_15min(self, date):
        return (self.ordinal(date)*24+date.hour)*4 + self.seconds(date)//(15*60)

    def _get_offset_hourly(self, date):
        return self.ordinal(date)*24 + self.seconds(date)//3600 # XXX DST!

    def _get_offset_daily(self, date):
        return self.ordinal(date)

    def _get_offset_weekly(self, date):
        ordinal = self.ordinal(date) - 1
        return ordinal//7

    def _get_offset_monthly(self, date):
        ordinal = self.ordinal(date)
        date = datetime.date.fromordinal(ordinal)
        return (date.year-1)*12 + date.month-1

    def _get_offset_yearly(self, date):
        return date.year-1

    def _get_offset_time_vector(self, date):
        return int(self.datetime_to_timestamp(date))

    def _get_offset_constant(self, date):
        return 0

    def _get_frac_offset_time_vector(self, date):
        offset = self.datetime_to_timestamp(date)
        return offset - math.floor(offset)

    def _get_frac_offset_15min(self, date):
        rem = self.seconds(date) % (15*60)
        return rem / (15*60)

    def _get_frac_offset_hourly(self, date):
        rem = self.seconds(date) % 3600
        return rem / 3600

    def _get_frac_offset_daily(self, date):
        rem = self.seconds(date)
        return rem / (3600*24)

    def _get_frac_offset_weekly(self, date):
        ordinal = self.ordinal(date) - 1
        return (ordinal % 7) / 7 + self.seconds(date)/(3600*24*7)

    def _get_frac_offset_monthly(self, date):
        start_of_month = datetime.datetime(date.year, date.month, 1)
        delta = date - start_of_month
        seconds = timedelta_to_seconds(delta)
        return seconds / (days_in_month(start_of_month)*3600*24)

    def _get_frac_offset_yearly(self, date):
        frac_ordinal = self.ordinal(date) + self.seconds(date) / (3600*24)
        start_of_year = self.ordinal(datetime.datetime(date.year, 1, 1))
        return  (frac_ordinal-start_of_year) / days_in_year(date)

    def _get_frac_offset_constant(self, date):
        return 0

    def get_duration_in_days(self, granularity, date):
        '''
        Compute the duration of the time interval associated to
        (granularity, date) in days
        '''
        if granularity in TIME_DELTAS.keys():
            delta = TIME_DELTAS[granularity]
            return timedelta_to_days(delta)
        elif granularity == 'monthly':
            date = self.prev_month_start(date)
            return days_in_month(date)
        elif granularity == 'yearly':
            date = self.prev_year_start(date)
            return days_in_year(date)

    def ordinal(self, date):
        """
        return the number of days since Jan 1st, 0001 (this one being having ordinal 0)
        """
        raise NotImplementedError

    def day_of_week(self, date):
        """
        return the day of week for a given date as an integer (0 is monday -> 6 is sunday)
        """
        raise NotImplementedError

    def iso_day_of_week(self, date):
        """
        return the day of week for a given date as an integer (1 is monday -> 7 is sunday)
        """
        return self.day_of_week(date) + 1

    def start_of_day(self, tstamp):
        """
        return datetime of the begining of day for tstamp
        """
        raise NotImplementedError

    def is_day_start(self, tstamp):
        raise NotImplementedError

    def is_month_start(self, tstamp):
        raise NotImplementedError

    def is_year_start(self, tstamp):
        raise NotImplementedError

    def next_week_start(self, date):
        """
        return a datetime object on next monday
        """
        raise NotImplementedError

    def next_month_start(self, date):
        """
        return a datetime object on the first day of the next month
        """
        raise NotImplementedError

    def prev_month_start(self, date):# XXX rename to month_start?
        raise NotImplementedError

    def next_year_start(self, date):
        raise NotImplementedError

    def prev_year_start(self, date):# XXX rename to year_start?
        raise NotImplementedError

    def prev_year_start(self, date):
        raise NotImplementedError

    def strftime(self, date, fmt):
        return date.strftime(fmt)

    def date_to_datetime(self, date):
        return datetime.datetime.combine(date, datetime.time(0))

    def get_month_number(self, date):
        raise NotImplementedError


    ORIGIN = datetime.datetime(2000, 1, 1)
    @staticmethod
    def datetime_to_timestamp(datetime, epoch=ORIGIN):
        """return datetime as a fraction of days since an epoch"""
        return timedelta_to_days(datetime - epoch)

    @staticmethod
    def timestamp_to_datetime(timestamp, epoch=ORIGIN):
        """return a datetime from a fraction of days since an epoch"""
        return epoch + datetime.timedelta(days=timestamp)


class GregorianCalendar(AbstractCalendar):
    def ordinal(self, date):
        return date.toordinal()

    def day_of_week(self, date):
        return date.weekday()
    
    def iso_day_of_week(self, date):
        return date.isoweekday()

    def start_of_day(self, tstamp):
        """
        return datetime of the begining of day for tstamp
        """
        return datetime.datetime(tstamp.year, tstamp.month, tstamp.day, 0)

    def is_day_start(self, tstamp):
        return tstamp.hour == 0 and tstamp.minute == 0 and tstamp.second == 0

    def is_month_start(self, tstamp):
        return tstamp.day == 1 and self.is_day_start(tstamp)

    def is_year_start(self, tstamp):
        return tstamp.month == 1  and self.is_month_start(tstamp)

    def next_week_start(self, date):
        """
        return a datetime object on next monday
        """
        date = self.start_of_day(date)
        monday = date + datetime.timedelta(days=7-date.weekday())
        if monday.weekday() != 0:
            raise RuntimeError('severe problem in next_week_start implementation')
        return monday

    def next_month_start(self, date):
        """
        return a datetime object on the first day of the next month
        """
        date = self.start_of_day(date)
        return date + datetime.timedelta(days=(days_in_month(date)-date.day+1))

    def prev_month_start(self, date):# XXX rename to month_start?
        return datetime.datetime(date.year, date.month, 1, 0)

    def next_year_start(self, date):
        return datetime.datetime(date.year + 1, 1, 1, 0)

    def prev_year_start(self, date):# XXX rename to year_start?
        return datetime.datetime(date.year, 1, 1, 0)

    def get_month_number(self, date):
        return date.month

register_calendar('gregorian', GregorianCalendar())

