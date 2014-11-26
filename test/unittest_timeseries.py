from __future__ import division

from datetime import datetime, timedelta

import numpy

from logilab.common.testlib import tag

from cubicweb.devtools.testlib import CubicWebTC

from cubes.timeseries.entities.utils import get_next_date


class TimeSeriesTC(CubicWebTC):

    def _create_ts(self, data=numpy.arange(10), granularity=None,
                   start_date=datetime(2009, 10, 1)):
        req = self.request()
        return req.create_entity('TimeSeries', data_type=u'Float',
                                 granularity=granularity, start_date=start_date,
                                 data=data)

    def _create_npts(self, data=numpy.arange(10), timestamps=None,
                     granularity='daily', start_date=datetime(2009, 10, 1)):
        req = self.request()
        if timestamps is None:
            date = start_date
            timestamps = []
            for _qv in data:
                timestamps.append(date)
                date = get_next_date(granularity, date)
        timestamps = numpy.array(timestamps)
        return req.create_entity('NonPeriodicTimeSeries', data_type=u'Float',
                                 data=data, timestamps=timestamps)


class NPTSTC(TimeSeriesTC):

    def test_creation(self):
        ts = self._create_npts()
        self.assertEqual(ts.timestamped_array(), [(datetime(2009, 10, 1, 0, 0), 0.0),
                                                  (datetime(2009, 10, 2, 0, 0), 1.0),
                                                  (datetime(2009, 10, 3, 0, 0), 2.0),
                                                  (datetime(2009, 10, 4, 0, 0), 3.0),
                                                  (datetime(2009, 10, 5, 0, 0), 4.0),
                                                  (datetime(2009, 10, 6, 0, 0), 5.0),
                                                  (datetime(2009, 10, 7, 0, 0), 6.0),
                                                  (datetime(2009, 10, 8, 0, 0), 7.0),
                                                  (datetime(2009, 10, 9, 0, 0), 8.0),
                                                  (datetime(2009, 10, 10, 0, 0), 9.0)])
        self.assertEqual(ts.start_date, datetime(2009, 10, 1, 0, 0))
        start = (datetime(2009, 10, 1) - datetime(2000, 1, 1)).days
        ts2 = self._create_npts(timestamps=numpy.arange(start, start+ 10))
        self.assertEqual(ts2.timestamped_array(), ts.timestamped_array())
        ts3 = self._create_ts(granularity=u'daily')
        self.assertEqual(ts3.timestamped_array(), ts.timestamped_array())

    def test_no_timestamps(self):
        with self.assertRaises(ValueError) as cm:
            self._create_npts(timestamps=range(10, 0, -1))
        self.assertEqual(str(cm.exception), 'time stamps must be a strictly ascendant vector')

    def test_size_mismatch(self):
        with self.assertRaises(ValueError) as cm:
            self._create_npts(timestamps=range(9))
        self.assertEqual(str(cm.exception), 'data/timestamps vectors size mismatch')

    def test_bad_timestamps(self):
        with self.assertRaises(ValueError) as cm:
            self._create_npts(timestamps=range(10, 0, -1))
        self.assertEqual(str(cm.exception), 'time stamps must be a strictly ascendant vector')


class TSaccessTC(TimeSeriesTC):
    def setup_database(self):
        self.constantts = self._create_ts(data= numpy.array([0]), granularity=u'constant')
        self.hourlyts = self._create_ts(granularity=u'hourly')
        self.dailyts = self._create_ts(granularity=u'daily')
        self.monthlyts = self._create_ts(granularity=u'monthly')
        self.yearlyts = self._create_ts(granularity=u'yearly')
        self.weeklyts = self._create_ts(granularity=u'weekly', start_date=datetime(2009, 10, 5))

    @tag('constant')
    def test_end_date_constant(self):
        expected_end = self.constantts.start_date + timedelta.resolution
        self.assertEqual(self.constantts.end_date, expected_end)

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

    @tag('constant')
    def test_make_relative_index_constant(self):
        ts = self.constantts
        date = datetime(2009, 10, 2, 12)
        calendar = ts.calendar
        granularity = ts.granularity
        delta = calendar.get_offset(date, granularity) - ts._start_offset
        self.assertEqual(delta, 0)

    @tag('constant')
    def test_get_by_date_constant(self):
        date = datetime(2009, 10, 2, 12)
        self.assertEqual(self.constantts.get_by_date(date), self.constantts.array[0])

    @tag('constant')
    def test_get_by_date_constant_slice(self):
        date1 = datetime(2009, 10, 2, 12)
        date2 = datetime(2009, 10, 4, 6)
        self.assertEqual(self.constantts.get_by_date(slice(date1, date2)).tolist(),
                          self.constantts.array[0:1].tolist())
    @tag('constant')
    def test_get_by_date_constant_slice_none(self):
        self.assertEqual(self.constantts.get_by_date(slice(None, None)).tolist(),
                          self.constantts.array[0:1].tolist())

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
        # expected = (data[1] + data[2] + data[3]) / (3.)
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
        expected = (coefs*data[3:6]).sum()/coefs.sum()    # weighted average
        # expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertEqual(result, expected)

    def test_not_weighted_aggregated_value_average(self):
        date1 = datetime(2010, 1, 31, 20)
        date2 = datetime(2010, 3, 2, 0)
        _date, result = self.monthlyts.aggregated_value([(date1, date2)], 'average')
        data = self.monthlyts.array
        coefs = numpy.array([4.0/(31*24), 1.0, 24.0/(31*24)])
        expected = (coefs*data[3:6]).sum()/coefs.sum()    # average
        # expected = (data[1] + data[2] + data[3]) / (3.)
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

class NPTSaccessTC(TSaccessTC):
    """same test as above but for NonPeriodicTimeSeries"""
    _create_ts = TSaccessTC._create_npts

    @tag('constant')
    def test_end_date_constant(self):
        self.skipTest('Non relevant.')
    test_make_relative_index_constant = test_end_date_constant
    test_get_by_date_constant = test_end_date_constant
    test_get_by_date_constant_slice = test_end_date_constant
    test_get_by_date_constant_slice_none = test_end_date_constant

    def test_end_date_daily(self):
        expected_end = self.dailyts.start_date + timedelta(days=9)
        self.assertEqual(self.dailyts.end_date, expected_end)

    def test_end_date_hourly(self):
        expected_end = self.dailyts.start_date + timedelta(hours=9)
        self.assertEqual(self.hourlyts.end_date, expected_end)

    def test_end_date_weekly(self):
        expected_end = self.weeklyts.start_date + timedelta(days=9*7)
        self.assertEqual(self.weeklyts.end_date, expected_end)

    def test_end_date_monthly(self):
        expected_end = datetime(2010, 7, 1)
        self.assertEqual(self.monthlyts.end_date, expected_end)

    def test_end_date_yearly(self):
        expected_end = datetime(2018, 10, 1)
        self.assertEqual(self.yearlyts.end_date, expected_end)


    # XXX: I'm really not sure these tests have a meaning with NPTS
    def test_make_relative_index_yearly(self):
        date = datetime(2010, 11, 2, 12)
        calendar = self.yearlyts.calendar
        granularity = self.yearlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.yearlyts._start_offset
        self.assertAlmostEqual(delta, (365 + 31 + 36/24))


    def test_make_relative_index_weekly(self):
        date = datetime(2009, 10, 14, 12)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertAlmostEqual(delta, (7 + 2 + 12/24))

    def test_make_relative_index_weekly2(self):
        date = datetime(2009, 10, 19, 0)
        calendar = self.weeklyts.calendar
        granularity = self.weeklyts.granularity
        delta = calendar.get_offset(date, granularity) - self.weeklyts._start_offset
        self.assertAlmostEqual(delta, 2*7)

    def test_make_relative_index_monthly(self):
        date = datetime(2009, 11, 2, 12)
        calendar = self.monthlyts.calendar
        granularity = self.monthlyts.granularity
        delta = calendar.get_offset(date, granularity) - self.monthlyts._start_offset
        self.assertAlmostEqual(delta, 32.5)

    def test_offset_for_granularity_with_dash(self):
        date = datetime(2009, 10, 5, 0)
        calendar = self.yearlyts.calendar
        self.assertEqual(calendar.get_offset(date, 'time-vector'), calendar.get_offset(date, 'time_vector'))

class ComputeSumAverageTC(TimeSeriesTC):

    def setup_database(self):
        self.yearlyts = self._create_ts(granularity=u'yearly',
                                        data=numpy.arange(3)*10,
                                        start_date=datetime(2009, 1, 1, 0))
        self.monthlyts = self._create_ts(granularity=u'monthly', data=numpy.arange(12))
        self.weeklyts = self._create_ts(granularity=u'weekly',
                                         data=numpy.arange(10),
                                         start_date=datetime(2009, 9, 28, 6))
        self.dailyts = self._create_ts(granularity=u'daily',
                                         data=numpy.arange(60))
        self.hourlyts = self._create_ts(granularity=u'hourly',
                                         data=numpy.arange(720))
        self.quartts = self._create_ts(granularity=u'15min',
                                         data=numpy.arange(2880))


    def test_end_date_error(self):
        start_date = datetime(2009, 12, 3)
        end_date = datetime(2009, 12, 23)
        self.assertRaises(IndexError, self.dailyts.aggregated_value, [(start_date, end_date)], 'sum')
        self.assertRaises(IndexError, self.dailyts.aggregated_value, [(start_date, end_date)], 'average')

    def test_yearly_sum(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        _date, sum_res = self.yearlyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.yearlyts.array
        self.assertAlmostEqual(sum_res, data[0] + data[1])

    def test_yearly_average(self):
        start_date = datetime(2009, 1, 1, 0)
        end_date = datetime(2011, 1, 1, 0)
        _date, average = self.yearlyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.yearlyts.array
        self.assertAlmostEqual(average, (data[0] + data[1])/2)

    def test_monthly_sum(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        _date, sum_res = self.monthlyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.monthlyts.array
        self.assertAlmostEqual(sum_res, (1-2/30)*data[1] + 1*data[2] + 22/31*data[3])

    def test_monthly_sum2(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2009, 11, 23, 0)
        _date, sum_res = self.monthlyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.monthlyts.array
        self.assertAlmostEqual(sum_res, (20/30)*data[1])

    def test_monthly_average(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2010, 1, 23, 0)
        _date, average = self.monthlyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.monthlyts.array
        coefs = numpy.array([float(30-2)/30, 1, 22.0/31])
        expected = (coefs*data[1:4]).sum()/coefs.sum()    # weighted average
        # expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertAlmostEqual(average,  expected)

    def test_monthly_average2(self):
        start_date = datetime(2009, 11, 3, 0)
        end_date = datetime(2009, 11, 23, 0)
        _date, average = self.monthlyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.monthlyts.array
        self.assertAlmostEqual(average,  data[1])

    def test_weekly_sum(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.weeklyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.weeklyts.array
        self.assertAlmostEqual(sum_res, 2/7*data[1] + 1*data[2] + 4/7*data[3])

    def test_weekly_average(self):
        start_date = datetime(2009, 10, 10, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.weeklyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.weeklyts.array
        coefs = numpy.array([2.0/7, 1, 4.0/7])
        expected = (coefs*data[1:4]).sum()/coefs.sum()    # weighted average
        # expected = (data[1] + data[2] + data[3]) / (3.)
        self.assertAlmostEqual(average, expected)

    def test_daily_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.dailyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.dailyts.array
        self.assertAlmostEqual(sum_res, data[2:22].sum())

    def test_daily_sum2(self):
        start_date = datetime(2009, 10, 3, 2)
        end_date = datetime(2009, 10, 3, 10)
        _date, sum_res = self.dailyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.dailyts.array
        self.assertAlmostEqual(sum_res, data[2]*8/24)

    def test_daily_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.dailyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.dailyts.array
        self.assertAlmostEqual(average, data[2:22].mean())

    def test_daily_average2(self):
        start_date = datetime(2009, 10, 3, 2)
        end_date = datetime(2009, 10, 3, 10)
        _date, sum_res = self.dailyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.dailyts.array
        self.assertAlmostEqual(sum_res, data[2])

    def test_hourly_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.hourlyts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.hourlyts.array
        self.assertAlmostEqual(sum_res, data[2*24:22*24].sum())

    def test_hourly_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.hourlyts.aggregated_value([(start_date, end_date)], 'average')
        data = self.hourlyts.array
        self.assertAlmostEqual(average, data[2*24:22*24].mean())

    def test_15min_sum(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, sum_res = self.quartts.aggregated_value([(start_date, end_date)], 'sum')
        data = self.quartts.array
        self.assertAlmostEqual(sum_res, data[2*24*4:22*24*4].sum())

    def test_15min_average(self):
        start_date = datetime(2009, 10, 3, 0)
        end_date = datetime(2009, 10, 23, 0)
        _date, average = self.quartts.aggregated_value([(start_date, end_date)], 'average')
        data = self.quartts.array
        self.assertAlmostEqual(average, data[2*24*4:22*24*4].mean())


class NPTSComputeSumAverageTC(ComputeSumAverageTC):
    """same test as above but for NonPeriodicTimeSeries"""
    _create_ts = ComputeSumAverageTC._create_npts

    def test_weekly_sum(self):
        self.skipTest('need update for non-periodic time-series')

    def test_weekly_average(self):
        self.skipTest('need update for non-periodic time-series')


if __name__ == '__main__':
    from logilab.common.testlib import unittest_main
    unittest_main()
