from datetime import datetime

from logilab.common.testlib import TestCase, unittest_main

# this import is for apycot
import cubicweb.devtools

from cubes.timeseries.calendars import GregorianCalendar

class GasCalendarDateFunctionsTC(TestCase):

    def setUp(self):
        self.calendar = GregorianCalendar()

    def test_start_of_day_before(self):
        tstamp = datetime(2009, 10, 28, 4)
        start = self.calendar.start_of_day(tstamp)
        self.assertEqual(start, datetime(2009, 10, 28, 0))

    def test_next_month_start(self):
        tstamp = datetime(2009, 10, 28, 8)
        start = self.calendar.next_month_start(tstamp)
        self.assertEqual(start, datetime(2009, 11, 1, 0))

    def test_timestamp_datetime_roundtrip0(self):
        date = datetime(2000, 1, 1)
        timestamp = self.calendar.datetime_to_timestamp(date)
        self.assertEqual(self.calendar.timestamp_to_datetime(timestamp), date)

    def test_timestamp_datetime_roundtrip1(self):
        date = datetime(2010, 12, 31)
        timestamp = self.calendar.datetime_to_timestamp(date)
        self.assertEqual(self.calendar.timestamp_to_datetime(timestamp), date)

    def test_timestamp_datetime_roundtrip2(self):
        date = datetime(1990, 1, 1, 1, 1, 2)
        timestamp = self.calendar.datetime_to_timestamp(date)
        self.assertEqual(self.calendar.timestamp_to_datetime(timestamp), date)

    def test_0(self):
        self.assertEqual(self.calendar.timestamp_to_datetime(self.calendar.datetime_to_timestamp(datetime(2000, 1, 1))),
                         datetime(2000, 1, 1))

    def test_1(self):
        self.assertEqual(self.calendar.timestamp_to_datetime(self.calendar.datetime_to_timestamp(datetime(2010, 12, 31))),
                         datetime(2010, 12, 31))

    def test_2(self):
        self.assertEqual(self.calendar.timestamp_to_datetime(self.calendar.datetime_to_timestamp(datetime(1990, 1, 1, 1, 1, 2))),
                         datetime(1990, 1, 1, 1, 1, 2))

if __name__ == '__main__':
    unittest_main()
