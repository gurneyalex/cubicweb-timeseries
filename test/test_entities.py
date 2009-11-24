from __future__ import division

import numpy
from datetime import datetime

from cubicweb.devtools.apptest import EnvBasedTC
from logilab.common.testlib import unittest_main

class TSaccessTC(EnvBasedTC):
    def setup_database(self):
        data = numpy.arange(10)
        start_date = datetime(2009, 10, 1)
        self.dailyts = self.execute('INSERT TimeSeries SP: SP name "tsdaily", '
                               'SP data_type "Float", SP granularity "daily", '
                               'SP use_calendar "gregorian", SP start_date %(s)s, '
                               'SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)
        self.monthlyts = self.execute('INSERT TimeSeries SP: SP name "tsmonthly", '
                               'SP data_type "Float", SP granularity "monthly", '
                               'SP use_calendar "gregorian", SP start_date %(s)s, '
                               'SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)

        self.yearlyts = self.execute('INSERT TimeSeries SP: SP name "tsyearly", '
                               'SP data_type "Float", SP granularity "yearly", '
                               'SP use_calendar "gregorian", SP start_date %(s)s, '
                               'SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)

        self.weeklyts = self.execute('INSERT TimeSeries SP: SP name "tsweekly", '
                               'SP data_type "Float", SP granularity "weekly", '
                               'SP use_calendar "gregorian", SP start_date %(s)s, '
                               'SP data %(d)s',
                               {'d': data,
                                's': datetime(2009, 10, 5)}).get_entity(0, 0)

    def test_make_relative_index_daily(self):
        date = datetime(2009, 10, 2, 12)
        calendar = self.dailyts.calendar
        granularity = self.dailyts.granularity
        delta = calendar.get_offset(date, granularity) - self.dailyts._start_offset
        self.assertEquals(delta, 1.5)

    def test_get_by_date_daily(self):
        date = datetime(2009, 10, 2, 12)
        self.assertEquals(self.dailyts.get_by_date(date), self.dailyts.array[1])

    def test_get_by_date_daily_slice(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 4, 6)
        self.assertEquals(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:4].tolist())

    def test_get_by_date_daily_slice_end_exact(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 4, 0)
        self.assertEquals(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:3].tolist())

    def test_get_by_date_daily_slice_below_gran(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 2, 18)
        self.assertEquals(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:2].tolist())


    def test_make_relative_index_monthly(self):
        date = datetime(2009, 11, 2, 12)
        calendar = self.monthlyts.calendar
        granularity = self.monthlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.monthlyts._start_offset
        self.assertFloatAlmostEquals(delta, 1 + 36/(30*24))

    def test_get_by_date_monthly(self):
        date = datetime(2009, 11, 2, 12)
        self.assertEquals(self.monthlyts.get_by_date(date), self.monthlyts.array[1])

    def test_get_by_date_monthly_slice(self):
        date1 = datetime(2009, 11, 2, 12)
        date2 = datetime(2010, 1, 4, 6)
        self.assertEquals(self.monthlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.monthlyts.array[1:4].tolist())

    def test_get_by_date_monthly_slice_below_gran(self):
        date1 = datetime(2009, 11, 2, 12)
        date2 = datetime(2009, 11, 14, 18)
        self.assertEquals(self.monthlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.monthlyts.array[1:2].tolist())


    def test_make_relative_index_yearly(self):
        date = datetime(2010, 11, 2, 12)
        calendar = self.yearlyts.calendar
        granularity = self.yearlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.yearlyts._start_offset
        self.assertFloatAlmostEquals(delta, (365 + 31 + 36/24)/365)

    def test_get_by_date_yearly(self):
        date = datetime(2010, 11, 2, 12)
        self.assertEquals(self.yearlyts.get_by_date(date), self.yearlyts.array[1])

    def test_get_by_date_yearly_slice(self):
        date1 = datetime(2010, 11, 2, 12)
        date2 = datetime(2013, 1, 4, 6)
        self.assertEquals(self.yearlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.yearlyts.array[1:4].tolist())

    def test_get_by_date_yearly_slice_below_gran(self):
        date1 = datetime(2010, 11, 2, 12)
        date2 = datetime(2011, 1, 14, 18)
        self.assertEquals(self.yearlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.yearlyts.array[1:2].tolist())



    def test_make_relative_index_weekly(self):
        date = datetime(2009, 10, 14, 12)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertFloatAlmostEquals(delta, (7 + 2 + 12/24)/7)

    def test_make_relative_index_weekly2(self):
        date = datetime(2009, 10, 19, 0)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertFloatAlmostEquals(delta, 2)

    def test_get_by_date_weekly(self):
        date = datetime(2009, 10, 14, 12)
        self.assertEquals(self.weeklyts.get_by_date(date), self.weeklyts.array[1])

    def test_get_by_date_weekly_slice(self):
        date1 = datetime(2009, 10, 14, 12)
        date2 = datetime(2009, 11, 1, 18)
        self.assertEquals(self.weeklyts.get_by_date(slice(date1, date2)).tolist(),
                          self.weeklyts.array[1:4].tolist())

    def test_get_by_date_weekly_slice_below_gran(self):
        date1 = datetime(2009, 10, 14, 12)
        date2 = datetime(2009, 10, 14, 18)
        self.weeklyts.get_by_date(date1)
        self.weeklyts.get_by_date(date2)
        self.assertEquals(self.weeklyts.get_by_date(slice(date1, date2)).tolist(),
                          self.weeklyts.array[1:2].tolist())





    def test_aggregated_value_average(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        date, result = self.dailyts.aggregated_value(date1, date2, 'average')
        expected = (.75*self.dailyts.array[1] + 1*self.dailyts.array[2] + .25*self.dailyts.array[3]) / (.75+1+.25)
        self.assertEquals(result, expected)

    def test_aggregated_value_sum(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        date, result = self.dailyts.aggregated_value(date1, date2, 'sum')
        expected = (.75*self.dailyts.array[1] + 1*self.dailyts.array[2] + .25*self.dailyts.array[3])
        self.assertEquals(result, expected)

    def test_aggregated_value_last(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        date, result = self.dailyts.aggregated_value(date1, date2, 'last')
        expected = self.dailyts.array[3]
        self.assertEquals(result, expected)

    def test_aggregated_value_last_before_start(self):
        date1 = datetime(2009, 9, 2, 6)
        date2 = datetime(2009, 10, 1, 0)
        self.assertRaises(IndexError, self.dailyts.aggregated_value,date1, date2, 'last')

    def test_aggregated_value_average_below_gran(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 2, 18)
        date, result = self.dailyts.aggregated_value(date1, date2, 'average')
        expected = (.5*self.dailyts.array[1]) / (.5)
        self.assertEquals(result, expected)

    def test_aggregated_value_sum_below_gran(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 2, 18)
        date, result = self.dailyts.aggregated_value(date1, date2, 'sum')
        expected = .5*self.dailyts.array[1]
        self.assertEquals(result, expected)

    def test_aggregated_value_sum_exact_start(self):
        date1 = datetime(2009, 10, 2, 0)
        date2 = datetime(2009, 10, 4, 6)
        date, result = self.dailyts.aggregated_value(date1, date2, 'sum')
        expected = (1*self.dailyts.array[1] + 1*self.dailyts.array[2] + .25*self.dailyts.array[3])
        self.assertEquals(result, expected)

    def test_aggregated_value_sum_exact_end(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 5, 0)
        date, result = self.dailyts.aggregated_value(date1, date2, 'sum')
        expected = (.75*self.dailyts.array[1] + 1*self.dailyts.array[2] + 1*self.dailyts.array[3])
        self.assertEquals(result, expected)



class ComputeSumAverageTC(EnvBasedTC):

    def setup_database(self):
        start_date = datetime(2009, 10, 1, 0)
        yearly_start_date = datetime(2009, 1, 1, 0)
        self.yearly_ts = self.execute('INSERT TimeSeries SP: SP name "tsyearly", '
                                      'SP data_type "Float", SP granularity "yearly", '
                                      'SP use_calendar "gregorian", SP start_date %(s)s, '
                                      'SP data %(d)s',
                                      {'d': numpy.arange(3)*10,
                                       's': yearly_start_date}).get_entity(0, 0)
        self.monthly_ts = self.execute('INSERT TimeSeries SP: SP name "tsmonthly", '
                                     'SP data_type "Float", SP granularity "monthly", '
                                     'SP use_calendar "gregorian", SP start_date %(s)s, '
                                     'SP data %(d)s',
                                     {'d': numpy.arange(12),
                                      's': start_date}).get_entity(0, 0)
        self.weekly_ts = self.execute('INSERT TimeSeries SP: SP name "tsweekly", '
                                     'SP data_type "Float", SP granularity "weekly", '
                                     'SP use_calendar "gregorian", SP start_date %(s)s, '
                                     'SP data %(d)s',
                                     {'d': numpy.arange(10),
                                      's':  datetime(2009, 9, 28, 6)}).get_entity(0, 0)

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
                                      'SP data_type "Float", SP granularity "15min", '
                                      'SP use_calendar "gregorian", SP start_date %(s)s, '
                                      'SP data %(d)s',
                                      {'d': numpy.arange(2880),
                                       's': start_date}).get_entity(0, 0)

    def test_start_date_error(self):
        start_date = datetime(2009, 9, 3)
        end_date = datetime(2009, 10, 23)
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, start_date, end_date, 'sum')
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, start_date, end_date, 'average')

    def test_end_date_error(self):
        start_date = datetime(2009, 12, 3)
        end_date = datetime(2009, 12, 23)
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, start_date, end_date, 'sum')
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, start_date, end_date, 'average')

    def test_yearly_sum(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        date, sum_res = self.yearly_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.yearly_ts.array
        self.assertFloatAlmostEquals(sum_res, data[0] + data[1])

    def test_yearly_average(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        date, average = self.yearly_ts.aggregated_value(start_date, end_date, 'average')
        data = self.yearly_ts.array
        self.assertFloatAlmostEquals(average, (data[0] + data[1])/2)

    def test_monthly_sum(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        date, sum_res = self.monthly_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.monthly_ts.array
        self.assertFloatAlmostEquals(sum_res, (1-2/30)*data[1] + 1*data[2] + 22/31*data[3])

    def test_monthly_average(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        date, average = self.monthly_ts.aggregated_value(start_date, end_date, 'average')
        data = self.monthly_ts.array
        expected = ((1-2/30)*data[1] + 1*data[2] + 22/31*data[3]) / (1-2/30+1+22/31)
        self.assertFloatAlmostEquals(average,  expected)

    def test_weekly_sum(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, sum_res = self.weekly_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.weekly_ts.array
        self.assertFloatAlmostEquals(sum_res, 2/7*data[1] + 1*data[2] + 4/7*data[3])

    def test_weekly_average(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, average = self.weekly_ts.aggregated_value(start_date, end_date, 'average')
        data = self.weekly_ts.array
        expected = (2/7*data[1] + 1*data[2] + 4/7*data[3]) / (2/7+1+4/7)
        self.assertFloatAlmostEquals(average, expected)

    def test_daily_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, sum_res = self.daily_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.daily_ts.array
        self.assertFloatAlmostEquals(sum_res, data[2:22].sum())

    def test_daily_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, average = self.daily_ts.aggregated_value(start_date, end_date, 'average')
        data = self.daily_ts.array
        self.assertFloatAlmostEquals(average, data[2:22].mean())

    def test_hourly_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, sum_res = self.hourly_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.hourly_ts.array
        self.assertFloatAlmostEquals(sum_res, data[2*24:22*24].sum())

    def test_hourly_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, average = self.hourly_ts.aggregated_value(start_date, end_date, 'average')
        data = self.hourly_ts.array
        self.assertFloatAlmostEquals(average, data[2*24:22*24].mean())

    def test_15min_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, sum_res = self.quart_ts.aggregated_value(start_date, end_date, 'sum')
        data = self.quart_ts.array
        self.assertFloatAlmostEquals(sum_res, data[2*24*4:22*24*4].sum())

    def test_15min_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        date, average = self.quart_ts.aggregated_value(start_date, end_date, 'average')
        data = self.quart_ts.array
        self.assertFloatAlmostEquals(average, data[2*24*4:22*24*4].mean())



class TimeSeriesTC(EnvBasedTC):
    def test_auto_name(self):
        data=numpy.arange(10)
        ts = self.add_entity('TimeSeries', data=data)
        self.assert_(ts.name.startswith(u'TS_%s' % ts.eid))

if __name__ == '__main__':
    unittest_main()
