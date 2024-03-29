from logilab.mtconverter import xml_escape

from cwtags import tag as t

from cubicweb.predicates import is_instance
from cubicweb.view import EntityView

import unicodedata as udata


class ExcelPreferencesInContextView(EntityView):
    __regid__ = 'incontext'
    __select__ = is_instance('ExcelPreferences')
    noseparator = u'<no separator>'

    def cell_call(self, row, col, **kwargs):
        entity = self.cw_rset.get_entity(row, col)
        th_sep = entity.thousands_separator
        if not th_sep:
            th_sep = self.noseparator
        else:
            th_sep = udata.name(th_sep)
        self.w(xml_escape(self._cw._('separators: decimal = %s, thousands = %s, csv = %s')) %
               (t.span(xml_escape(udata.name(entity.decimal_separator)), klass='highlight'),
                t.span(xml_escape(th_sep), klass='highlight'),
                t.span(xml_escape(udata.name(entity.csv_separator)), klass='highlight')))
