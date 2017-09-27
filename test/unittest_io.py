from datetime import datetime

import numpy

from cubicweb import Binary, NoSelectableObject
from cubicweb.devtools.testlib import CubicWebTC

from cubes.timeseries.entities import utils

def is_supported(ext):
    if ext == '.xls':
        return utils.HANDLE_XLS
    if ext == '.xlsx':
        return utils.HANDLE_XLSX
    return True

class TimeSeriesTC(CubicWebTC):

    def _create_ts(self, cnx, data=numpy.arange(10), granularity=None,
                   start_date=datetime(2009, 10, 1)):
        return cnx.create_entity('TimeSeries', data_type=u'Float',
                                 granularity=granularity, start_date=start_date,
                                 data=data)

    def _create_npts(self, cnx, data=numpy.arange(10), timestamps=None,
                     granularity='daily', start_date=datetime(2009, 10, 1)):
        if timestamps is None:
            date = start_date
            timestamps = []
            for _qv in data:
                timestamps.append(date)
                date = utils.get_next_date(granularity, date)
        timestamps = numpy.array(timestamps)
        return cnx.create_entity('NonPeriodicTimeSeries', data_type=u'Float',
                                 data=data, timestamps=timestamps)

class RoundTripTC(TimeSeriesTC):

    def test_ts_export(self):
        with self.admin_access.web_request() as req:
            ts = self._create_ts(req, granularity=u'daily')
            req.cnx.commit()
            for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                             ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                             ('.csv', 'text/csv')):
                try:
                    exporter = self.vreg['adapters'].select('ITimeSeriesExporter', req,
                                                            entity=ts, mimetype=fmt)
                except NoSelectableObject:
                    continue
                out = exporter.export()
                self.failIf(len(out) == 0)

    def test_npts_export(self):
        with self.admin_access.web_request() as req:
            ts = self._create_npts(req)
            req.cnx.commit()
            for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                             ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                             ('.csv', 'text/csv')):
                try:
                    exporter = self.vreg['adapters'].select('ITimeSeriesExporter', req,
                                                            entity=ts, mimetype=fmt)
                except NoSelectableObject:
                    continue
                out = exporter.export()
                self.failIf(len(out) == 0)

    def test_ts_import(self):
        with self.admin_access.repo_cnx() as cnx:
            orig = self._create_ts(cnx, granularity=u'daily')
            cnx.commit()
            for ext, fmt in (('.xls', 'application/vnd.ms-excel'),
                             ('.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                             ('.csv', 'text/csv')):
                if not is_supported(ext):
                    continue
                fname = self.datapath('ts' + ext)
                blob = Binary(open(fname, 'rb').read())
                blob.filename = fname
                ts = cnx.create_entity('TimeSeries',
                                       granularity=u'daily',
                                       start_date=datetime(2009, 10, 1),
                                       data=blob)
                self.assertEqual(orig.timestamped_array(), ts.timestamped_array())

    def test_npts_import(self):
        with self.admin_access.repo_cnx() as cnx:
            orig = self._create_npts(cnx)
            cnx.commit()
            for ext, fmt in (('.csv', 'text/csv'),):
                if not is_supported(ext):
                    continue
                fname = self.datapath('npts' + ext)
                blob = Binary(open(fname, 'rb').read())
                blob.filename = fname
                ts = cnx.create_entity('NonPeriodicTimeSeries', data=blob)
                self.assertEqual(orig.timestamped_array(), ts.timestamped_array())


if __name__ == '__main__':
    import unittest
    unittest.main()
