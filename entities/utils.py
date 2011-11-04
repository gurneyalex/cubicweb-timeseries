import datetime

from cubes.timeseries.calendars import TIME_DELTAS


try:
    import xlrd
    import xlwt
except ImportError:
    HANDLE_XLS = False
else:
    HANDLE_XLS = True

try:
    import openpyxl
    try:
        openpyxl.reader
        openpyxl.workbook
    except AttributeError:
        raise ImportError('installed openpyxl version is too old')
except ImportError:
    HANDLE_XLSX = False
else:
    HANDLE_XLSX = True


def boolint(value):
    """ ensuring such boolean like values
    are properly summable and plotable
    0, 0.0 => 0
    1, 42.0 => 11
    """
    return int(bool(float(value)))


def get_next_date(granularity, date):
    #pylint:disable-msg=E1101
    if granularity in TIME_DELTAS:
        return date + TIME_DELTAS[granularity]
    elif granularity == 'monthly':
        return get_next_month(date)
    elif granularity == 'yearly':
        return get_next_year(date)
    elif granularity == 'constant':
        return date + datetime.timedelta.resolution
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
