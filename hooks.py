from cubicweb import ValidationError
from cubicweb.server.hook import Hook
from cubicweb.selectors import is_instance

class TimeSeriesDataReadHook(Hook):
    __regid__ = 'timeseries_data_read_hook'
    __select__ = Hook.__select__ & is_instance('TimeSeries')
    events = ('before_update_entity', 'before_add_entity')

    def __call__(self):
        if 'data' in self.entity.edited_attributes:
            self.entity.grok_data()

class ConstantTimeSeriesValidationHook(Hook):
    __regid__ = 'constant_ts_hook'
    __select__ = Hook.__select__ & is_instance('TimeSeries')
    events = ('after_update_entity', 'after_add_entity')

    def __call__(self):
        if self.entity.is_constant:
            if self.entity.count != 1:
                raise ValidationError(self.entity, {'granularity':
                                                    'TimeSeries is constant, but has more than one value'})
