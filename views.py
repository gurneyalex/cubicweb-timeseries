"""cube-specific forms/views/actions/components

:organization: Logilab
:copyright: 2001-2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement, division
import math
import numpy

from cwtags.tag import div, h2, table, input, button

from logilab.common.date import datetime2ticks
from logilab.mtconverter import xml_escape

from cubicweb import Binary, ValidationError
from cubicweb.utils import json_dumps as dumps

from cubicweb.web import uicfg
from cubicweb.schema import display_name
from cubicweb.selectors import is_instance
from cubicweb.web import formwidgets as fw, formfields as ff
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
        self.w(h2(_('summary')))
        self.wview('summary', entity.as_rset())

    def _prepare_side_boxes(self, entity):
        return []

    def render_entity_attributes(self, entity):
        w = self.w; _ = self._cw._
        w(h2(_('characteristics')))
        with table(w):
            for attr in self.characteristics_attrs:
                self.field(display_name(self._cw, attr), entity.view('reledit', rtype=attr),
                           tr=True, table=True)
            self.field(_('calendar'), entity.use_calendar, tr=True, table=True)

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

class TimeSeriesPlotView(baseviews.EntityView):
    __regid__ = 'ts_plot'
    __select__ = is_instance('TimeSeries')
    title = None
    onload = u"init_ts_plot('%(figid)s', [%(plotdata)s]);"

    def dump_plot(self, plot):
        plot = [(datetime2ticks(x), y) for x,y in plot]
        return dumps(plot)

    def call(self, width=None, height=None):
        req = self._cw; w=self.w
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js(('jquery.flot.js',
                    'jquery.flot.selection.js',
                    'cubes.timeseries.js'))
        width = width or req.form.get('width', 700)
        height = height or req.form.get('height', 400)
        figid = u'figure%s' % req.varmaker.next()
        w(div(id='main%s' % figid, style='width: %spx; height: %spx;' % (width, height)))
        w(div(id='overview%s' % figid, style='width: %spx; height: %spx;' % (width, height/3)))
        w(button(req._('Reset'), id='reset'))
        plotdata = ("{label: '%s', data: %s}" % (xml_escape(ts.dc_title()),
                                                 self.dump_plot(ts.compressed_timestamped_array()))
                    for ts in self.cw_rset.entities())
        req.html_headers.add_onload(self.onload %
                                    {'figid': figid,
                                     'plotdata': ','.join(plotdata)})

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



# XXX hack to work around https://www.cubicweb.org/ticket/1381203

class DataFileField(ff.FileField):
    """ FileField sucks, teach it good the manners """

    def _process_form_value(self, form):
        widget = self.get_widget(form)
        value = widget.process_field_data(form, self)
        return self._ensure_correctly_typed(form, value)

    def _process_form_value_with_suffix(self, form, suffix=u''):
        """ add suffix parameter & use it """
        posted = form._cw.form
        if self.input_name(form, u'__detach') in posted:
            # drop current file value on explictily asked to detach
            return None
        try:
            value = posted[self.input_name(form, suffix)]
        except KeyError:
            # raise UnmodifiedField instead of returning None, since the later
            # will try to remove already attached file if any
            raise ff.UnmodifiedField()
        # value is a 2-uple (filename, stream)
        try:
            filename, stream = value
        except ValueError:
            raise ff.UnmodifiedField()
        # XXX avoid in memory loading of posted files. Requires Binary handling changes...
        value = Binary(stream.read())
        if not value.getvalue(): # usually an unexistant file
            value = None
        else:
            # set filename on the Binary instance, may be used later in hooks
            value.filename = ff.normalize_filename(filename)
        return value

def __new__(cls, *args, **kwargs):
    """depending on the attribute name we dispatch
    to DataFileField class
    """
    if kwargs.get('name') == 'data':
        cls = DataFileField
    return ff.StringField.__new__(cls, **kwargs)
ff.FileField.__new__ = staticmethod(__new__)

# /hack

def interpret_constant(entity, str_value):
    try:
        return entity.python_value(str_value)
    except (ValueError, TypeError):
        _ = entity._cw._
        raise ValidationError(entity.eid, {'data': _('accepted type: %s') % _(entity.data_type)})

class ConstantDataInput(fw.TextInput):

    def typed_value(self, form, field):
        entity = form.edited_entity
        granularity = entity.granularity
        if granularity != 'constant':
            return ''
        return entity.array[0]

class DataWidget(fw.Input):
    """ depending on granularity being constant,
    either show/process a simple input field or a file field
    """
    needs_js = fw.Input.needs_js + ('cubes.timeseries.js',)
    field_id_tmpl = '%s-subject%s:%s' # (field name, suffix, eid)

    # let's keep this open for easy subclassing
    VariableInputClass = fw.FileInput
    ConstantInputClass = ConstantDataInput

    def _render(self, form, field, renderer):
        """ provide two input widgets
        the switch will be made in js-land where the shadows^W
        the live value of the granularity will be used
        to present the appropriate widget
        """
        formid = form.domid
        eid = form.edited_entity.eid
        data_fileinput_domid = self.field_id_tmpl % ('granularity', '', eid)
        form._cw.add_onload("init_data_widget('%s', '%s', '%s')" %
                            (self.field_id_tmpl % ('granularity', '', eid),
                             self.field_id_tmpl % ('data', '-non-constant', eid),
                             self.field_id_tmpl % ('data', '-constant', eid)))
        nonconstwidget = self.VariableInputClass(suffix='-non-constant')
        constwidget = self.ConstantInputClass(suffix='-constant')
        return '<div id="%s">%s\n%s</div>' % (field.dom_id(form),
                                              constwidget.render(form, field, renderer),
                                              nonconstwidget.render(form, field, renderer))

    def process_field_data(self, form, field):
        value = super(DataWidget, self).process_field_data(form, field)
        req = form._cw
        granularity = req.form.get('granularity-subject:%s' % form.edited_entity.eid)
        constant_value = req.form.get(field.input_name(form, '-constant')).strip() or None
        if granularity == 'constant':
            value = numpy.array([interpret_constant(form.edited_entity, constant_value)])
            return value
        field = ff.FileField(name='data', eidparam=True, required=True, role='subject')
        return field._process_form_value_with_suffix(form, suffix=u'-non-constant')

uicfg.autoform_field_kwargs.tag_subject_of(('TimeSeries', 'data', '*'),
                                           {'widget': DataWidget})
