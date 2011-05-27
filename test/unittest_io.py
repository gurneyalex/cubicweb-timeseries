import tempfile
import os.path as osp
from datetime import datetime

import numpy

from cubicweb import Binary
from cubicweb.devtools.testlib import CubicWebTC

from cubes.timeseries.entities import utils

DATADIR = osp.join(osp.dirname(__name__), 'data')

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
                date = utils.get_next_date(granularity, date)
        timestamps = numpy.array(timestamps)
        return req.create_entity('NonPeriodicTimeSeries', data_type=u'Float',
                                 data=data, timestamps=timestamps)

class RoundTripTC(TimeSeriesTC):

    def test_ts_export(self):
        ts = self._create_ts(granularity=u'daily')
        self.commit()
        req = self.request()
        for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                         ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                         ('.csv', 'text/csv')):
            exporter = self.vreg['adapters'].select('ITimeSeriesExporter', req,
                                                    entity=ts, mimetype=fmt)
            if not exporter:
                pass
            out = exporter.export()
            self.failIf(len(out) == 0)

    def test_npts_export(self):
        ts = self._create_npts()
        self.commit()
        req = self.request()
        for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                         ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                         ('.csv', 'text/csv')):
            exporter = self.vreg['adapters'].select('ITimeSeriesExporter', req,
                                                entity=ts, mimetype=fmt)
            if not exporter:
                pass
            out = exporter.export()
            self.failIf(len(out) == 0)

    def test_ts_import(self):
        req = self.request()
        orig = self._create_ts(granularity=u'daily')
        self.commit()
        for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                         ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                         ('.csv', 'text/csv')):
            fname = osp.join(DATADIR, 'ts' + ext)
            blob = Binary(open(fname, 'rb').read())
            blob.filename = fname
            ts = req.create_entity('TimeSeries',
                                   granularity=u'daily',
                                   start_date=datetime(2009, 10, 1),
                                   data=blob)
            self.assertEqual(orig.timestamped_array(), ts.timestamped_array())

    def test_npts_import(self):
        req = self.request()
        orig = self._create_npts()
        self.commit()
        for ext, fmt in (('.csv', 'text/csv'),):
            fname = osp.join(DATADIR, 'npts' + ext)
            blob = Binary(open(fname, 'rb').read())
            blob.filename = fname
            ts = req.create_entity('NonPeriodicTimeSeries', data=blob)
            self.assertEqual(orig.timestamped_array(), ts.timestamped_array())


if __name__ == '__main__':
    from logilab.common.testlib import unittest_main
    unittest_main()
