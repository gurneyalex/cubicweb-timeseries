"""cube-specific primary & related views

:organization: Logilab
:copyright: 2010-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

import math
import datetime

from logilab.mtconverter import xml_escape

from cubicweb import tags
from cubicweb.schema import display_name
from cubicweb.predicates import is_instance
from cubicweb.web.views import primary, baseviews, tabs
from cubicweb.web.views.ajaxcontroller import ajaxfunc

from cubes.timeseries.utils import get_formatter

_ = unicode

class TimeSeriesPrimaryView(tabs.TabsMixin, primary.PrimaryView):
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
    tabs = [_('ts_summary'), _('ts_plot')]
    default_tab = 'ts_summary'

    def cell_call(self, row, col):
        entity = self.cw_rset.complete_entity(row, col)
        self._cw.demote_to_html()
        self.render_entity_toolbox(entity)
        self.render_entity_title(entity)
        self.render_tabs(self.tabs, self.default_tab, entity)

class TimeSeriesSummaryViewTab(tabs.PrimaryTab):
    __regid__ = 'ts_summary'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')

    characteristics_attrs = ('granularity',)

    def summary(self, entity):
        pass

    def _prepare_side_boxes(self, entity):
        return []

    def render_entity_attributes(self, entity):
        w = self.w; _ = self._cw._
        w(u'<table class="table table-bordered"><tr><td style="padding-right: 1cm">')
        w(tags.h2(_('Summary')))
        entity.view('summary', w=w)
        w(tags.h2(_('Characteristics')))
        w(u'<table  class="table table-bordered">')
        for attr in self.characteristics_attrs:
            self.field(display_name(self._cw, attr),
                       entity.view('reledit', rtype=attr),
                       tr=True, table=True)
        # XXX maybe we want reledit on this in the timeseries cube,
        # but not in the only user of this cube for now...
        self.field(_('unit'), entity.unit, tr=True, table=True)
        self.field(_('calendar'), entity.use_calendar, tr=True, table=True)
        w(u'</table>')
        w(tags.h2(_('Preview')))
        entity.view('sparkline', w=w)
        w(u'</td><td>')
        if not entity.is_constant:
            w(tags.h2(_('ts_values')))
            self.wview('ts_values', self.cw_rset)
        w(u'</td></tr></table>')

def format_value(cw, value):
    if isinstance(value, float):
        value = cw.format_float(value)
    elif isinstance(value, datetime.datetime):
        value = cw.format_date(value, time=True)
    elif isinstance(value, datetime.date):
        value = cw.format_date(value)
    return value

class TimeSeriesSummaryView(baseviews.EntityView):
    __regid__ = 'summary'
    __select__ = is_instance('TimeSeries')
    summary_attrs = (_('start_date'), _('end_date'),
                     _('min_unit'), _('max_unit'),
                     _('average_unit'), _('count'))
    editable_summary_attrs = set((_('start_date'),))

    def display_constant_fields(self, entity):
        self.field('constant', entity.first_unit,
                   show_label=True, tr=True, table=True)

    def cell_call(self, row, col, **kwargs):
        entity = self.cw_rset.get_entity(row, col)
        self.w(u'<table class="table table-bordered">')
        if entity.is_constant:
            self.display_constant_fields(entity)
        else:
            for attr in self.summary_attrs:
                if attr in self.editable_summary_attrs:
                    self.field(display_name(self._cw, attr),
                               entity.view('reledit', rtype=attr),
                               tr=True, table=True)
                    continue
                if attr == 'average_unit' and entity.data_type == 'Boolean':
                    continue
                # XXX getattr because some are actually properties
                value = getattr(entity, attr)
                value = format_value(self._cw, value)
                self.field(attr, value,
                           show_label=True, tr=True, table=True)
        self.w(u'</table>')


class NonPeriodicTimeSeriesSummaryView(TimeSeriesSummaryView):
    __select__ = is_instance('NonPeriodicTimeSeries')
    editable_summary_attrs = set()


@ajaxfunc(output_type='json')
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


class TimeSeriesValuesView(baseviews.EntityView):
    __regid__ = 'ts_values'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
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
        self.w(u'<table id="tsvalue" cubicweb:type="unprepared" class="table table-bordered"></table>')
        self.w(tags.div(None, id='pager'))
