from cubicweb.predicates import is_instance, one_line_rset
from cubicweb.view import EntityView
from cubicweb.web import action

_ = unicode

class TimeSeriesExcelExport(EntityView):
    __regid__ = 'tsxlexport'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
    content_type = 'application/vnd.ms-excel'
    file_ext = 'xls'
    templatable = False
    binary = True

    def set_request_content_type(self):
        """overriden to set a .xls filename"""
        entity = self.cw_rset.get_entity(0, 0)
        exporter = self._cw.vreg['adapters'].select('ITimeSeriesExporter', self._cw,
                                                    entity=entity, mimetype=self.content_type)
        filename = exporter.filename
        self._cw.set_content_type(self.content_type, filename=filename)

    def call(self, written_eid=None, etype_dict=None):
        entity = self.cw_rset.get_entity(0, 0)
        exporter = self._cw.vreg['adapters'].select('ITimeSeriesExporter', self._cw,
                                                    entity=entity, mimetype=self.content_type)
        self.w(exporter.export())

class TimeSeriesCSVExport(TimeSeriesExcelExport):
    __regid__ = 'tscsvexport'
    content_type = 'text/csv'
    file_ext = 'csv'

class ExcelTSExportAction(action.Action):
    __regid__ = 'tsexportaction'
    title = _('export to excel')
    __select__ = one_line_rset() & is_instance('TimeSeries', 'NonPeriodicTimeSeries')

    def url(self):
        return self.cw_rset.get_entity(0, 0).absolute_url(vid='tsxlexport')

