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

if __name__ == '__main__':
    unittest_main()
