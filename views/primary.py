"""cube-specific primary & related views

:organization: Logilab
:copyright: 2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement, division

import math

from cwtags.tag import div, h2, table

from logilab.mtconverter import xml_escape

from cubicweb.schema import display_name
from cubicweb.selectors import is_instance
from cubicweb.web.views import primary, baseviews, tabs
from cubicweb.web.views.basecontrollers import jsonize, JSonController

from cubes.timeseries.utils import get_formatter

_ = unicode

class TimeSeriesPrimaryView(tabs.TabsMixin, primary.PrimaryView):
    __select__ = is_instance('TimeSeries')
    tabs = [_('ts_summary'), _('ts_plot'), _('ts_values')]
    default_tab = 'ts_summary'

    def cell_call(self, row, col):
        entity = self.cw_rset.complete_entity(row, col)
        self._cw.demote_to_html()
        self.render_entity_toolbox(entity)
        self.render_entity_title(entity)
        if entity.is_constant:
            self.w(div(u'%s: %s' % (self._cw._('constant value'), self._cw.format_float(entity.first))))
        else:
            self.render_tabs(self.tabs, self.default_tab, entity)

class TimeSeriesSummaryViewTab(tabs.PrimaryTab):
    __regid__ = 'ts_summary'
    __select__ = is_instance('TimeSeries')

    characteristics_attrs = ('unit', 'granularity',)

    def summary(self, entity):
        self.w(h2(_('Summary')))
        self.wview('summary', entity.as_rset())

    def _prepare_side_boxes(self, entity):
        return []

    def render_entity_attributes(self, entity):
        w = self.w; _ = self._cw._
        w(h2(_('Characteristics')))
        with table(w):
            for attr in self.characteristics_attrs:
                self.field(display_name(self._cw, attr), entity.view('reledit', rtype=attr),
                           tr=True, table=True)
            self.field(_('calendar'), entity.use_calendar, tr=True, table=True)
        w(h2(_('Preview')))
        self.wview('sparkline', entity.as_rset())

class TimeSeriesSummaryView(baseviews.EntityView):
    __regid__ = 'summary'
    __select__ = is_instance('TimeSeries')
    summary_attrs = (_('start_date'), _('end_date'),
                     _('min_unit'), _('max_unit'),
                     _('average_unit'), _('count'))

    def display_constant_fields(self, entity):
        self.field('constant', entity.first_unit,
                   show_label=True, tr=True, table=True)

    def cell_call(self, row, col, **kwargs):
        entity = self.cw_rset.get_entity(row, col)
        w = self.w
        with table(w):
            if entity.is_constant:
                self.display_constant_fields(entity)
            else:
                for attr in self.summary_attrs:
                    # XXX getattr because some are actually properties
                    value = getattr(entity, attr)
                    if isinstance(value, float):
                        value = self._cw.format_float(value)
                    self.field(attr, getattr(entity, attr),
                                   show_label=True, tr=True, table=True)


@jsonize
def get_ts_values_data(self):
    form = self._cw.form
    page = int(form.get('page'))
    rows = int(form.get('rows'))
    sortcol = ['date', 'value'].index(form.get('sidx'))
    reversesortorder = form.get('sord') == 'desc'
    def sortkey(col):
        return col[sortcol]
    entity = self._cw.execute(form.get('rql')).get_entity(0,0)
    dateformat, numformat, numformatter = get_formatter(self._cw, entity)
    # build output
    values = [{'id': str(idx + 1),
               'cell': (date.strftime(dateformat), numformat % numformatter(value))}
               for idx, (date, value) in enumerate(sorted(entity.timestamped_array(),
                                                          reverse=reversesortorder,
                                                          key=sortkey))]
    start = (page - 1)  * rows
    end = page * rows
    out = {'total': str(math.ceil(len(values) / rows)),
           'page': page,
           'records': str(len(values)),
           'rows': values[start:end]}
    return out
JSonController.js_get_ts_values_data = get_ts_values_data

class TimeSeriesValuesView(baseviews.EntityView):
    __regid__ = 'ts_values'
    __select__ = is_instance('TimeSeries')
    title = None

    onload = u"init_ts_grid('tsvalue', '%(url)s');"

    def cell_call(self, row, col):
        req = self._cw
        if not req.json_request:
            req.demote_to_html()
        entity = self.cw_rset.get_entity(row, col)
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js(('cubes.timeseries.js', 'grid.locale-en.js', 'jquery.jqGrid.js'))
        req.add_css(('jquery-ui-1.7.2.custom.css', 'ui.jqgrid.css'))
        url = entity.absolute_url('json') + '&fname=get_ts_values_data'
        req.html_headers.add_onload(self.onload % {'url': xml_escape(url)})
        self.w(table(id='tsvalue', cubicweb__type='unprepared'))
        self.w(div(id='pager'))
