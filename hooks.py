from cubicweb import ValidationError
from cubicweb.server.hook import Hook
from cubicweb.predicates import is_instance

class TimeSeriesDataReadHook(Hook):
    __regid__ = 'timeseries_data_read_hook'
    __select__ = Hook.__select__ & is_instance('TimeSeries', 'NonPeriodicTimeSeries')
    events = ('before_update_entity', 'before_add_entity')
    category = 'timeseries'

    def __call__(self):
        entity = self.entity
        if 'data' in entity.cw_edited:
            importer = entity.cw_adapt_to('TimeSeriesImporter')
            importer.grok_data()

class ConstantTimeSeriesValidationHook(Hook):
    __regid__ = 'constant_ts_hook'
    __select__ = Hook.__select__ & is_instance('TimeSeries')
    events = ('after_update_entity', 'after_add_entity')
    category = 'timeseries'

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
        errors = {}
        if entity.thousands_separator == entity.decimal_separator:
            msg = self._cw._('thousands separator must not be the same as decimal separator')
            errors['thousands_separator'] =msg
        if entity.csv_separator == entity.decimal_separator:
            msg = self._cw._('column separator must not be the same as decimal separator')
            errors['csv_separator'] =msg
        if errors:
            raise ValidationError(entity.eid, errors)

class SetupExcelPreferences(Hook):
    __regid__ = 'pylos.setup_excel_prefs'
    events = ('after_add_entity',)
    __select__ = Hook.__select__ & is_instance('CWUser')

    def __call__(self):
        self.debug('hook %s', self.__class__.__name__)
        try:
            self.entity.cw_set(format_preferences=self._cw.create_entity('ExcelPreferences'))
        except Exception, e:
            # while migrating from a pre 0.15 version, it can happen
            # that some users are fetched from LDAP and created
            # but at this moment the schema has not yet been updated
            # and this will fail
            self.warning('ExcelPreferences creation failed (%s)', e)


