from __future__ import division

import numpy
from datetime import datetime, timedelta

from cubicweb.devtools.testlib import CubicWebTC
from logilab.common.testlib import unittest_main

class TSaccessTC(CubicWebTC):
    def setup_database(self):
        data = numpy.arange(10)
        start_date = datetime(2009, 10, 1)
        self.hourlyts = self.execute('INSERT TimeSeries SP: '
                               'SP data_type "Float", SP granularity "hourly", '
                               'SP start_date %(s)s, SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)
        self.dailyts = self.execute('INSERT TimeSeries SP: '
                               'SP data_type "Float", SP granularity "daily", '
                               'SP start_date %(s)s, SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)
        self.monthlyts = self.execute('INSERT TimeSeries SP: '
                               'SP data_type "Float", SP granularity "monthly", '
                               'SP start_date %(s)s, SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)

        self.yearlyts = self.execute('INSERT TimeSeries SP: '
                               'SP data_type "Float", SP granularity "yearly", '
                               'SP start_date %(s)s, SP data %(d)s',
                               {'d': data,
                                's': start_date}).get_entity(0, 0)

        self.weeklyts = self.execute('INSERT TimeSeries SP: '
                               'SP data_type "Float", SP granularity "weekly", '
                               'SP start_date %(s)s, SP data %(d)s',
                               {'d': data,
                                's': datetime(2009, 10, 5)}).get_entity(0, 0)

    def test_end_date_daily(self):
        expected_end = self.dailyts.start_date + timedelta(days=10)
        self.assertEqual(self.dailyts.end_date, expected_end)

    def test_end_date_hourly(self):
        expected_end = self.dailyts.start_date + timedelta(hours=10)
        self.assertEqual(self.hourlyts.end_date, expected_end)

    def test_end_date_weekly(self):
        expected_end = self.weeklyts.start_date + timedelta(days=10*7)
        self.assertEqual(self.weeklyts.end_date, expected_end)

    def test_end_date_monthly(self):
        expected_end = datetime(2010, 8, 1)
        self.assertEqual(self.monthlyts.end_date, expected_end)

    def test_end_date_yearly(self):
        expected_end = datetime(2019, 10, 1)
        self.assertEqual(self.yearlyts.end_date, expected_end)



    def test_make_relative_index_daily(self):
        date = datetime(2009, 10, 2, 12)
        calendar = self.dailyts.calendar
        granularity = self.dailyts.granularity
        delta = calendar.get_offset(date, granularity) - self.dailyts._start_offset
        self.assertEqual(delta, 1.5)

    def test_get_by_date_daily(self):
        date = datetime(2009, 10, 2, 12)
        self.assertEqual(self.dailyts.get_by_date(date), self.dailyts.array[1])

    def test_get_by_date_daily_slice(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 4, 6)
        self.assertEqual(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:4].tolist())

    def test_get_by_date_daily_slice_end_exact(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 4, 0)
        self.assertEqual(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:3].tolist())

    def test_get_by_date_daily_slice_below_gran(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 2, 18)
        self.assertEqual(self.dailyts.get_by_date(slice(date1, date2)).tolist(),
                          self.dailyts.array[1:2].tolist())


    def test_make_relative_index_monthly(self):
        date = datetime(2009, 11, 2, 12)
        calendar = self.monthlyts.calendar
        granularity = self.monthlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.monthlyts._start_offset
        self.assertAlmostEqual(delta, 1 + 36/(30*24))

    def test_get_by_date_monthly(self):
        date = datetime(2009, 11, 2, 12)
        self.assertEqual(self.monthlyts.get_by_date(date), self.monthlyts.array[1])

    def test_get_by_date_monthly_slice(self):
        date1 = datetime(2009, 11, 2, 12)
        date2 = datetime(2010, 1, 4, 6)
        self.assertEqual(self.monthlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.monthlyts.array[1:4].tolist())

    def test_get_by_date_monthly_slice_below_gran(self):
        date1 = datetime(2009, 11, 2, 12)
        date2 = datetime(2009, 11, 14, 18)
        self.assertEqual(self.monthlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.monthlyts.array[1:2].tolist())


    def test_make_relative_index_yearly(self):
        date = datetime(2010, 11, 2, 12)
        calendar = self.yearlyts.calendar
        granularity = self.yearlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.yearlyts._start_offset
        self.assertAlmostEqual(delta, (365 + 31 + 36/24)/365)

    def test_get_by_date_yearly(self):
        date = datetime(2010, 11, 2, 12)
        self.assertEqual(self.yearlyts.get_by_date(date), self.yearlyts.array[1])

    def test_get_by_date_yearly_slice(self):
        date1 = datetime(2010, 11, 2, 12)
        date2 = datetime(2013, 1, 4, 6)
        self.assertEqual(self.yearlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.yearlyts.array[1:4].tolist())

    def test_get_by_date_yearly_slice_below_gran(self):
        date1 = datetime(2010, 11, 2, 12)
        date2 = datetime(2011, 1, 14, 18)
        self.assertEqual(self.yearlyts.get_by_date(slice(date1, date2)).tolist(),
                          self.yearlyts.array[1:2].tolist())



    def test_make_relative_index_weekly(self):
        date = datetime(2009, 10, 14, 12)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertAlmostEqual(delta, (7 + 2 + 12/24)/7)

    def test_make_relative_index_weekly2(self):
        date = datetime(2009, 10, 19, 0)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertAlmostEqual(delta, 2)

    def test_get_by_date_weekly(self):
        date = datetime(2009, 10, 14, 12)
        self.assertEqual(self.weeklyts.get_by_date(date), self.weeklyts.array[1])

    def test_get_by_date_weekly_slice(self):
        date1 = datetime(2009, 10, 14, 12)
        date2 = datetime(2009, 11, 1, 18)
        self.assertEqual(self.weeklyts.get_by_date(slice(date1, date2)).tolist(),
                          self.weeklyts.array[1:4].tolist())

    def test_get_by_date_weekly_slice_below_gran(self):
        date1 = datetime(2009, 10, 14, 12)
        date2 = datetime(2009, 10, 14, 18)
        self.weeklyts.get_by_date(date1)
        self.weeklyts.get_by_date(date2)
        self.assertEqual(self.weeklyts.get_by_date(slice(date1, date2)).tolist(),
                          self.weeklyts.array[1:2].tolist())

    def test_aggregated_value_average(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        data = self.dailyts.array
        coefs = numpy.array([18.0/24, 1, 6.0/24])
        expected = (coefs*data[1:4]).sum()/coefs.sum()    # average = weighted average in this case
#        expected = (data[1] + data[2] + data[3]) / (3.)

        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'average')
        self.assertEqual(result, expected)
        
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'weighted_average')
        self.assertEqual(result, expected)
    
        
    def test_weighted_aggregated_value_average(self):
        date1 = datetime(2010, 1, 31, 20)
        date2 = datetime(2010, 3, 2, 0)
        _date, result = self.monthlyts.aggregated_value([(date1, date2)], 'weighted_average')
        data = self.monthlyts.array
        coefs = numpy.array([1.0/6, 28.0, 1.0])
        print coefs
        expected = (coefs*data[3:6]).sum()/coefs.sum()    # weighted average
#        expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertEqual(result, expected)
        
    def test_not_weighted_aggregated_value_average(self):
        date1 = datetime(2010, 1, 31, 20)
        date2 = datetime(2010, 3, 2, 0)
        _date, result = self.monthlyts.aggregated_value([(date1, date2)], 'average')
        data = self.monthlyts.array
        coefs = numpy.array([4.0/(31*24), 1.0, 24.0/(31*24)])
        print coefs
        expected = (coefs*data[3:6]).sum()/coefs.sum()    # average
#        expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertAlmostEqual(result, expected, 10)

    def test_aggregated_value_sum(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'sum')
        expected = (.75*self.dailyts.array[1] + 1*self.dailyts.array[2] + .25*self.dailyts.array[3])
        self.assertEqual(result, expected)

    def test_aggregated_value_last(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 4, 6)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'last')
        expected = self.dailyts.array[3]
        self.assertEqual(result, expected)

    def test_aggregated_value_last_multiple_interval(self):
        interval1 = (datetime(2009, 10, 2, 6), datetime(2009, 10, 4, 6))
        interval2 = (datetime(2009, 10, 5, 6), datetime(2009, 10, 7, 6))
        interval3 = (datetime(2009, 10, 8, 6), datetime(2009, 10, 9, 6))
        intervals = [interval1, interval2, interval3]
        self.assertRaises(ValueError, self.dailyts.aggregated_value, intervals, 'last')

    def test_aggregated_value_last_use_last_interval(self):
        interval1 = (datetime(2009, 10, 2, 6), datetime(2009, 10, 4, 6))
        interval2 = (datetime(2009, 10, 5, 6), datetime(2009, 10, 7, 6))
        interval3 = (datetime(2009, 10, 8, 6), datetime(2009, 10, 9, 6))
        intervals = [interval1, interval2, interval3]
        _date, result = self.dailyts.aggregated_value(intervals, 'last', use_last_interval=True)
        expected = self.dailyts.array[8]
        self.assertEqual(result, expected)

    def test_aggregated_value_last_before_start(self):
        date1 = datetime(2009, 9, 2, 6)
        date2 = datetime(2009, 10, 1, 0)
        self.assertRaises(IndexError, self.dailyts.aggregated_value, [(date1, date2)], 'last')

    def test_aggregated_value_average_below_gran(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 2, 18)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'average')
        expected = (.5*self.dailyts.array[1]) / (.5)
        self.assertEqual(result, expected)

    def test_aggregated_value_sum_below_gran(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 2, 18)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'sum')
        expected = .5*self.dailyts.array[1]
        self.assertEqual(result, expected)

    def test_aggregated_value_sum_exact_start(self):
        date1 = datetime(2009, 10, 2, 0)
        date2 = datetime(2009, 10, 4, 6)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'sum')
        expected = (1*self.dailyts.array[1] + 1*self.dailyts.array[2] + .25*self.dailyts.array[3])
        self.assertEqual(result, expected)

    def test_aggregated_value_sum_exact_end(self):
        date1 = datetime(2009, 10, 2, 6)
        date2 = datetime(2009, 10, 5, 0)
        _date, result = self.dailyts.aggregated_value([(date1, date2)], 'sum')
        expected = (.75*self.dailyts.array[1] + 1*self.dailyts.array[2] + 1*self.dailyts.array[3])
        self.assertEqual(result, expected)



class ComputeSumAverageTC(CubicWebTC):

    def setup_database(self):
        start_date = datetime(2009, 10, 1, 0)
        yearly_start_date = datetime(2009, 1, 1, 0)
        self.yearly_ts = self.execute('INSERT TimeSeries SP: '
                                      'SP data_type "Float", SP granularity "yearly", '
                                      'SP start_date %(s)s, SP data %(d)s',
                                      {'d': numpy.arange(3)*10,
                                       's': yearly_start_date}).get_entity(0, 0)
        self.monthly_ts = self.execute('INSERT TimeSeries SP: '
                                     'SP data_type "Float", SP granularity "monthly", '
                                     'SP start_date %(s)s, SP data %(d)s',
                                     {'d': numpy.arange(12),
                                      's': start_date}).get_entity(0, 0)
        self.weekly_ts = self.execute('INSERT TimeSeries SP: '
                                     'SP data_type "Float", SP granularity "weekly", '
                                     'SP start_date %(s)s, SP data %(d)s',
                                     {'d': numpy.arange(10),
                                      's':  datetime(2009, 9, 28, 6)}).get_entity(0, 0)

        self.daily_ts = self.execute('INSERT TimeSeries SP: '
                                     'SP data_type "Float", SP granularity "daily", '
                                     'SP start_date %(s)s, SP data %(d)s',
                                     {'d': numpy.arange(60),
                                      's': start_date}).get_entity(0, 0)
        self.hourly_ts = self.execute('INSERT TimeSeries SP: '
                                      'SP data_type "Float", SP granularity "hourly", '
                                      'SP start_date %(s)s, SP data %(d)s',
                                      {'d': numpy.arange(720),
                                       's': start_date}).get_entity(0, 0)
        self.quart_ts = self.execute('INSERT TimeSeries SP: '
                                      'SP data_type "Float", SP granularity "15min", '
                                      'SP start_date %(s)s, SP data %(d)s',
                                      {'d': numpy.arange(2880),
                                       's': start_date}).get_entity(0, 0)


    def test_end_date_error(self):
        start_date = datetime(2009, 12, 3)
        end_date = datetime(2009, 12, 23)
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, [(start_date, end_date)], 'sum')
        self.assertRaises(IndexError, self.daily_ts.aggregated_value, [(start_date, end_date)], 'average')

    def test_yearly_sum(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        _date, sum_res = self.yearly_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.yearly_ts.array
        self.assertAlmostEqual(sum_res, data[0] + data[1])

    def test_yearly_average(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        _date, average = self.yearly_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.yearly_ts.array
        self.assertAlmostEqual(average, (data[0] + data[1])/2)

    def test_monthly_sum(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        _date, sum_res = self.monthly_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.monthly_ts.array
        self.assertAlmostEqual(sum_res, (1-2/30)*data[1] + 1*data[2] + 22/31*data[3])

    def test_monthly_sum2(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2009, 11, 23, 0)
        _date, sum_res = self.monthly_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.monthly_ts.array
        self.assertAlmostEqual(sum_res, (20/30)*data[1])

    def test_monthly_average(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        _date, average = self.monthly_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.monthly_ts.array
        coefs = numpy.array([float(30-2)/30, 1, 22.0/31])
        expected = (coefs*data[1:4]).sum()/coefs.sum()    # weighted average
#        expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertAlmostEqual(average,  expected)

    def test_monthly_average2(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2009, 11, 23, 0)
        _date, average = self.monthly_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.monthly_ts.array
        self.assertAlmostEqual(average,  data[1])

    def test_weekly_sum(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.weekly_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.weekly_ts.array
        self.assertAlmostEqual(sum_res, 2/7*data[1] + 1*data[2] + 4/7*data[3])

    def test_weekly_average(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.weekly_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.weekly_ts.array
        coefs = numpy.array([2.0/7, 1, 4.0/7])
        expected = (coefs*data[1:4]).sum()/coefs.sum()    # weighted average
#        expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertAlmostEqual(average, expected)

    def test_daily_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.daily_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.daily_ts.array
        self.assertAlmostEqual(sum_res, data[2:22].sum())

    def test_daily_sum2(self):
        start_date = datetime(2009, 10, 3, 2)
        end_date = datetime(2009, 10, 3, 10)
        _date, sum_res = self.daily_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.daily_ts.array
        self.assertAlmostEqual(sum_res, data[2]*8/24)

    def test_daily_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.daily_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.daily_ts.array
        self.assertAlmostEqual(average, data[2:22].mean())

    def test_daily_average2(self):
        start_date = datetime(2009, 10, 3, 2)
        end_date = datetime(2009, 10, 3, 10)
        _date, sum_res = self.daily_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.daily_ts.array
        self.assertAlmostEqual(sum_res, data[2])

    def test_hourly_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.hourly_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.hourly_ts.array
        self.assertAlmostEqual(sum_res, data[2*24:22*24].sum())

    def test_hourly_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.hourly_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.hourly_ts.array
        self.assertAlmostEqual(average, data[2*24:22*24].mean())

    def test_15min_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.quart_ts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.quart_ts.array
        self.assertAlmostEqual(sum_res, data[2*24*4:22*24*4].sum())

    def test_15min_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.quart_ts.aggregated_value([(start_date, end_date)], 'average')
        data = self.quart_ts.array
        self.assertAlmostEqual(average, data[2*24*4:22*24*4].mean())


if __name__ == '__main__':
    unittest_main()
