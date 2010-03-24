from cubicweb.server.hook import Hook
from cubicweb.selectors import implements

class TimeSeriesDataReadHook(Hook):
    __regid__ = 'timeseries_data_read_hook'
    __select__ = Hook.__select__ & implements('TimeSeries')
    events = ('before_update_entity', 'before_add_entity')

    def __call__(self):
        if 'data' in self.entity.edited_attributes:
            self.entity.grok_data()
