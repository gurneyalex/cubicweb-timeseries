"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2009-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

import pickle
import zlib

from bisect import bisect_left
from itertools import izip

from logilab.common.decorators import cachedproperty, cached, clear_cache

from cubicweb.entities import fetch_config

from cubes.timeseries.entities import timeseries
from cubes.timeseries.calendars import timedelta_to_days, timedelta_to_seconds

_ = unicode

class NonPeriodicTimeSeries(timeseries.TimeSeries):
    __regid__ = 'NonPeriodicTimeSeries'
    fetch_attrs, cw_fetch_order = fetch_config(['data_type', 'unit', 'granularity'])

    is_constant = False

    @cachedproperty
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

    @cachedproperty
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

    def cw_clear_all_caches(self):
        super(NonPeriodicTimeSeries, self).cw_clear_all_caches()
        if 'start_date' in vars(self):
            del self.start_date
        if 'timestamps_array' in vars(self):
            del self.timestamps_array
        clear_cache(self, 'timestamped_array')

