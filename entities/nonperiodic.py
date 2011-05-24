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

from bisect import bisect_left
from itertools import izip

import numpy

from logilab.common.decorators import cached

from cubicweb import Binary
from cubicweb.entities import fetch_config

from cubes.timeseries.entities import timeseries

from cubes.timeseries.calendars import timedelta_to_days, timedelta_to_seconds

from cubes.timeseries.entities import utils
_ = unicode

def boolint(value):
    """ ensuring such boolean like values
    are properly summable and plotable
    0, 0.0 => 0
    1, 42.0 => 11
    """
    return int(bool(float(value)))

class NonPeriodicTimeSeries(timeseries.TimeSeries):
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
        tstamp_data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        tstamp_data.write(compressed_data)
        self.cw_edited['timestamps'] = tstamp_data
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

    def _numpy_from_txt(self, file, filename):
        return self._numpy_from_csv(file, filename)

    def _numpy_from_csv(self, file, filename, dialect=None, has_header=False):
        if dialect is None:
            dialect, has_header = self._snif_csv_dialect(file)
        else:
            assert dialect in csv.list_dialects()
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        tstamps = []
        # TODO: check granularity if we have a date column
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        th_sep = prefs.thousands_separator or ''
        for line, values in enumerate(reader):
            if len(values) != 2:
                raise ValueError('Expecting exactly 2 columns (timestamp, value), found %d in %s' % (len(values), filename))
            try:
                strval = values[1].replace(th_sep, '').replace(dec_sep, '.')
                val = float(strval)
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', filename) #pylint:disable-msg=E1101
                    continue # assume there was a header
                else:
                    raise ValueError('Invalid data type for value %s on line %d of %s' %
                                     (values[-1], reader.line_num, filename))
            try:
                tstamp_datetime = self._cw.parse_datetime(values[0])
                tstamp = self.calendar.datetime_to_timestamp(tstamp_datetime)
            except ValueError:
                raise
            series.append(val)
            tstamps.append(tstamp)
        self.timestamps = numpy.array(tstamps)
        return numpy.array(series, dtype=self.dtype)

    def _numpy_from_xls(self, file, filename):
        xl_data = file.read()
        wb = utils.xlrd.open_workbook(filename=file.filename,
                                file_contents=xl_data)
        sheet = wb.sheet_by_index(0)
        values = []
        tstamps = []
        datacol = sheet.ncols - 1
        tstampcol = sheet.ncols - 2
        for row in xrange(sheet.nrows):
            cell_value = sheet.cell_value(row, datacol)
            cell_tstamp = sheet.cell_value(row, tstampcol)
            try:
                cell_value = float(cell_value)
            except ValueError:
                raise ValueError('Invalid data type in cell (%d, %d) of %s' % (row, datacol, filename))
            try:
                cell_tstamp = datetime.datetime(*utils.xlrd.xldate_as_tuple(cell_tstamp, wb.datemode))
            except ValueError, exc:
                raise ValueError('Invalid data type in cell (%d, %d) of %s' % (row, tstampcol, filename))
            values.append(cell_value)
            tstamps.append(self.calendar.datetime_to_timestamp(cell_tstamp))
        if not values:
            raise ValueError('Unable to read a Timeseries in %s' % filename)
        self.timestamps = numpy.array(tstamps)
        return numpy.array(values, dtype=self.dtype)

    def _numpy_from_xlsx(self, *args):
        raise NotImplementedError
