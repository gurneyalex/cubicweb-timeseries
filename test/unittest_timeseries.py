from cubicweb.devtools.apptest import EnvBasedTC
from cubicweb import Binary

class TimeSeriesTC(EnvBasedTC):
    def test_auto_name(self):
        binary = Binary()
        binary.filename='toto.csv'
        ts = self.add_entity('TimeSeries', data=binary)
        self.assert_(ts.name.startswith(u'TS_%s' % ts.eid))
