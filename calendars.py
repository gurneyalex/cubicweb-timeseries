"""

"""

import numpy
import datetime

from cubicweb.utils import days_in_month, days_in_year


__ALL_CALENDARS = {}

def register_calendar(name, calendar):
    __ALL_CALENDARS[name] = calendar

def get_calendar(name):
    return __ALL_CALENDARS[name]

class AbstractCalendar:

    def get_offset(self, date, granularity):
        offset_method = getattr(self, '_get_offset_%s' % granularity)
        return offset_method(date) + self.get_frac_offset(date, granularity)

    def get_frac_offset(self, date, granularity):
        frac_offset_method = getattr(self, '_get_frac_offset_%s' % granularity)
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
        ordinal = self.ordinal(date)
        start_of_month = datetime.datetime(date.year, date.month, 1)
        delta = date - start_of_month
        seconds = delta.days*3600*24 + delta.seconds
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
        return date.second+60*date.minute + 3600*date.hour

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

register_calendar('gregorian', GregorianCalendar())



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

register_calendar('normalized', NormalizedCalendar())

