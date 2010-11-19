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


class ExcelPreferencesCoherency(Hook):
    __regid__ = 'pylos.excel_prefs_coherency'
    events = ('after_add_entity', 'after_update_entity')
    __select__ = Hook.__select__ & is_instance('ExcelPreferences')

    def __call__(self):
        self.debug('hook %s', self.__class__.__name__)
        entity = self.entity
        if entity.thousands_separator == entity.decimal_separator:
            msg = self._cw._('thousands separator must not be the same as decimal separator')
            raise ValidationError(entity.eid, {'thousands_separator': msg})

class SetupExcelPreferences(Hook):
    __regid__ = 'pylos.setup_excel_prefs'
    events = ('after_add_entity',)
    __select__ = Hook.__select__ & is_instance('CWUser')

    def __call__(self):
        self.debug('hook %s', self.__class__.__name__)
        self.entity.set_relations(format_preferences=self._cw.create_entity('ExcelPreferences'))
