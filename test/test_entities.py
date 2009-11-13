import numpy
from datetime import datetime

from cubicweb.devtools.apptest import EnvBasedTC

class ComputeSumAverageTC(EnvBasedTC):

    def setup_database(self):
        start_date = datetime(2009, 10, 01)
        self.yearly_ts = self.execute('INSERT TimeSeries SP: SP name "tsyearly", '
                                      'SP data_type "Float", SP granularity "yearly", '
                                      'SP use_calendar "gregorian", SP start_date %(s)s, '
                                      'SP data %(d)s',
                                      {'d': numpy.arange(3)*10,
                                       's': start_date}).get_entity(0, 0)
        self.monthly_ts = self.execute('INSERT TimeSeries SP: SP name "tsmonthly", '
                                     'SP data_type "Float", SP granularity "monthly", '
                                     'SP use_calendar "gregorian", SP start_date %(s)s, '
                                     'SP data %(d)s',
                                     {'d': numpy.arange(3),
                                      's': start_date}).get_entity(0, 0)
        self.weekly_ts = self.execute('INSERT TimeSeries SP: SP name "tsweekly", '
                                     'SP data_type "Float", SP granularity "weekly", '
                                     'SP use_calendar "gregorian", SP start_date %(s)s, '
                                     'SP data %(d)s',
                                     {'d': numpy.arange(10),
                                      's': start_date}).get_entity(0, 0)

        self.daily_ts = self.execute('INSERT TimeSeries SP: SP name "tsdaily", '
                                     'SP data_type "Float", SP granularity "daily", '
                                     'SP use_calendar "gregorian", SP start_date %(s)s, '
                                     'SP data %(d)s',
                                     {'d': numpy.arange(60),
                                      's': start_date}).get_entity(0, 0)
        self.hourly_ts = self.execute('INSERT TimeSeries SP: SP name "tshourly", '
                                      'SP data_type "Float", SP granularity "hourly", '
                                      'SP use_calendar "gregorian", SP start_date %(s)s, '
                                      'SP data %(d)s',
                                      {'d': numpy.arange(720),
                                       's': start_date}).get_entity(0, 0)
        self.quart_ts = self.execute('INSERT TimeSeries SP: SP name "ts15min", '
                                      'SP data_type "Float", SP granularity "15 min", '
                                      'SP use_calendar "gregorian", SP start_date %(s)s, '
                                      'SP data %(d)s',
                                      {'d': numpy.arange(2880),
                                       's': start_date}).get_entity(0, 0)

    def test_start_date_error(self):
        start_date = datetime(2009, 9, 03)
        end_date = datetime(2009, 10, 23)
        self.assertRaises(ValueError, self.daily_ts.compute_sum_average, start_date, end_date, 'sum')
        self.assertRaises(ValueError, self.daily_ts.compute_sum_average, start_date, end_date, 'average')

    def test_end_date_error(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 12, 23)
        self.assertRaises(ValueError, self.daily_ts.compute_sum_average, start_date, end_date, 'sum')
        self.assertRaises(ValueError, self.daily_ts.compute_sum_average, start_date, end_date, 'average')

    def test_yearly(self):
        start_date = datetime(2009, 10, 01)
        end_date = datetime(2010, 10, 01)
        sum_res = self.yearly_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatAlmostEquals(sum_res, 10)
        average = self.yearly_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 0.027397260273972601)

    def test_monthly(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 10, 23)
        sum_res = self.monthly_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatAlmostEquals(sum_res, 0.64516129032258063)
        average = self.monthly_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 0.032258064516129031)

    def test_weekly(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 10, 23)
        sum_res = self.weekly_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatEquals(sum_res, 3.4285714285714284)
        average = self.weekly_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 1.2)

    def test_daily(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 10, 23)
        sum_res = self.daily_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatAlmostEquals(sum_res, 230)
        average = self.daily_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 11)

    def test_hourly(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 10, 23)
        sum_res = self.hourly_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatAlmostEquals(sum_res, 230)
        average = self.hourly_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 11)

    def test_15min(self):
        start_date = datetime(2009, 10, 03)
        end_date = datetime(2009, 10, 23)
        sum_res = self.quart_ts.compute_sum_average(start_date, end_date, 'sum')
        self.assertFloatAlmostEquals(sum_res, 230)
        average = self.quart_ts.compute_sum_average(start_date, end_date, 'average')
        self.assertFloatAlmostEquals(average, 11)
