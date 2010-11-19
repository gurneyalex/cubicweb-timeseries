from logilab.mtconverter import xml_escape
from cwtags.tag import span

from cubicweb.selectors import is_instance
from cubicweb.view import EntityView

class ExcelPreferencesInContextView(EntityView):
    __regid__ = 'incontext'
    __select__ = is_instance('ExcelPreferences')
    noseparator = xml_escape('<no separator>')

    def cell_call(self, row, col, **kwargs):
        entity = self.cw_rset.get_entity(row, col)
        self.w(xml_escape(self._cw._('separators: decimal = %s, thousands = %s')) %
               (span(entity.decimal_separator, Class='highlight'),
                span(entity.thousands_separator or self.noseparator, Class='highlight')))
