"""cube-specific forms/views/actions/components

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement
_ = unicode
from logilab.mtconverter import xml_escape
from cwtags.tag import span, div, h2, table, tr, td, th, input
from cubicweb.web import uicfg, formfields
from cubicweb.schema import display_name
from cubicweb.selectors import implements

from simplejson import dumps

from cubicweb.web.views import primary, baseviews, plots, tabs
from cubes.timeseries.plots import TSFlotPlotWidget

class TimeSeriesPrimaryView(tabs.TabsMixin, primary.PrimaryView):
    __select__ = implements('TimeSeries')
    tabs = [_('ts_summary'), _('ts_plot'), _('ts_values')]
    default_tab = 'ts_summary'

    def cell_call(self, row, col):
        entity = self.cw_rset.complete_entity(row, col)
        self.render_entity_toolbox(entity)
        self.render_entity_title(entity)
        if entity.is_constant:
            self.w(div(u'%s: %s' % (self._cw._('constant value'), self._cw.format_float(entity.first))))
        else:
            self.render_tabs(self.tabs, self.default_tab, entity)

class TimeSeriesSummaryViewTab(tabs.PrimaryTab):
    __regid__ = 'ts_summary'
    __select__ = implements('TimeSeries')

    characteristics_attrs = ('granularity',)

    def summary(self, entity):
        self.w(h2(_('summary')))
        self.wview('summary', entity.as_rset())

    def _prepare_side_boxes(self, entity):
        return []

    def render_entity_attributes(self, entity):
        w = self.w; _ = self._cw._
        w(h2(self._cw._('characteristics')))
        with table(w):
            for attr in self.characteristics_attrs:
                self.field(display_name(self._cw, attr), entity.view('reledit', rtype=attr),
                           tr=True, table=True)
            self.field(self._cw._('calendar'), entity.use_calendar, tr=True, table=True)

class TimeSeriesSummaryView(baseviews.EntityView):
    __regid__ = 'summary'
    __select__ = implements('TimeSeries')
    summary_attrs = (_('start_date'), _('end_date'),
                     _('min'), _('max'),
                     _('average'), _('count'))

    def cell_call(self, row, col, **kwargs):
        entity = self.cw_rset.get_entity(row, col)
        w = self.w; _ = self._cw._
        with table(w):
            if entity.is_constant:
                self.field('constant', self._cw.format_float(entity.first),
                           show_label=True, tr=True, table=True)
            else:
                for attr in self.summary_attrs:
                    # XXX getattr because some are actually properties
                    try:
                        self.field(attr, self._cw.format_float(getattr(entity, attr)),
                                   show_label=True, tr=True, table=True)
                    except:
                        self.field(attr, getattr(entity, attr),
                                   show_label=True, tr=True, table=True)

class TimeSeriesPlotView(baseviews.EntityView):
    __regid__ = 'ts_plot'
    __select__ = implements('TimeSeries')
    title = None
    def build_plot_data(self, entity):
        plots = []
        for ts in self.cw_rset.entities():
            plots.append(ts.timestamped_array())
        return plots

    def call(self, width=None, height=None):
        form = self._cw.form
        width = width or form.get('width', 900)
        height = height or form.get('height', 250)
        names = []
        plot_list = []
        for ts in self.cw_rset.entities():
            names.append(ts.dc_title())
            plot_list.append(ts.compressed_timestamped_array())
        plotwidget = TSFlotPlotWidget(names, plot_list)
        plotwidget.render(self._cw, width, height, w=self.w)


from cubicweb.web.views.basecontrollers import jsonize, JSonController
@jsonize
def get_data(self):
    form = self._cw.form
    print form
    page = int(form.get('page'))
    rows = int(form.get('rows'))
    entity = self._cw.execute(form.get('rql')).get_entity(0,0)
    if entity.granularity in (u'15min', 'hourly'):
        fmt = '%Y/%m/%d %H:%M'
    else:
        fmt = '%Y/%m/%d'
    if entity.data_type in ('Integer', 'Boolean'):
        formatter = lambda x:x
        format = '%d'
    else:
        formatter = lambda x:self._cw.format_float(x)
        format = '%s'
    values = [{'id': idx, 'cell': (date.strftime(fmt), format % formatter(value))}
               for idx, (date, value) in enumerate(entity.timestamped_array())]
    start = (page - 1)  * rows
    end = page * rows
    out = {'total': len(values) / rows, 'page': int(page), 'records': len(values),
           'rows': values[start:end]}
    print dumps(out)
    return out
JSonController.js_get_data = get_data

class TimeSeriesValuesView(baseviews.EntityView):
    __regid__ = 'ts_values'
    __select__ = implements('TimeSeries')
    title = None

    onload = u"""
jQuery("#tsvalue").jqGrid({
    url: '%(url)s',
    datatype: 'json',
    height: 300,
    colNames:['date', 'value'],
    colModel :[
      {name:'date', index:'date', width:95},
      {name:'value', index:'value', width:99, align:'right'},
    ],
    sortname: 'date',
    sortorder: 'desc',
    viewrecords: true,
    caption: 'Values for %(ts_name)s'
  });
"""

    def cell_call(self, row, col):
        req = self._cw
        entity = self.cw_rset.get_entity(row, col)
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js('jquery.jqGrid.js')
        req.add_css(('jquery-ui-1.7.2.custom.css', 'ui.jqgrid.css'))
        url = entity.absolute_url('json') + '&fname=get_data'
        req.html_headers.add_onload(self.onload %
                                   {'ts_name': entity.dc_title(),
                                    'url': url},
                                   jsoncall=req.json_request)
        self.w(table(id='tsvalue'))
        #self.w(div(id='pager'))




## NOTE: this seems generic enough to be backported in CW
class RelationSwitchField(formfields.Field):
    """field used to choose among a list of relation.
    """
    needs_multipart = True # csv-based timeseries require a file upload

    def __init__(self, name, **kwargs):
        # XXX hack field name to avoid automatic HiddenRelationField creation
        #     when field name matches an existing subject / object relation
        #     (no longer needed in 3.6)
        internal_name = '_%s_' % name
        super(RelationSwitchField, self).__init__(name=internal_name, **kwargs)
        self.rtype = name

    def find_targettypes(self, entity):
        eschema = entity.e_schema
        if self.role == 'subject':
            return eschema.subjrels[self.rtype].objects(eschema)
        else:
            return eschema.objrels[self.rtype].subjects(eschema)

    def selected(self, entity):
        """return which couple (rtype, target_type) should be selected
        in the combobox
        """
        targettypes = self.find_targettypes(entity)
        if not entity.has_eid():
            return targettypes[0]
        related = getattr(entity, self.rtype)
        if related:
            return related[0].e_schema
        elif self._cwuired:
            # if relation is required, we should never arrive here
            raise ValueError('%s.%s is required but not set on eid %s'
                             % (entity.e_schema, self.rtype, entity.eid))
        # if not required, just pick the first one
        return targettypes[0]

    def initial_form(self, form, entity, ttype):
        """return the initial inline form:
        - either the inline-edition form of the existing relation
        - or the inline-creation form of the first relation in the combobox
        """
        rtype = self.rtype
        i18nctx = 'inlined:%s.%s.%s' % (entity.e_schema, rtype, 'subject')
        if entity.has_eid():
            return form.view('inline-edition', entity.related(rtype),
                             rtype=rtype, role=self.role,
                             ptype=entity.e_schema, peid=entity.eid,
                             i18nctx=i18nctx)
        else:
            return form.view('inline-creation', None, etype=ttype,
                             peid=entity.eid, ptype=entity.e_schema,
                             rtype=rtype, role=self.role,
                             i18nctx=i18nctx)

    def render(self, form, renderer):
        entity = form.edited_entity
        eschema = entity.e_schema
        data = []
        w = data.append
        selected = self.selected(entity)
        # XXX hack to bypass a CW / jquery ajax/onload bug: we don't
        #     want the onload methods to be called each time an ajax
        #     query is done
        form._cw.html_headers.define_var('docloaded', False)
        form._cw.html_headers.add_post_inline_script(u"""
function switchInlinedForm() {
    var value = jQuery(this).val().split(';'); // holderId;eid;ttype;rtype;role
    var holder = jQuery('#' + value[0]);
    holder.prev().remove();
    var i18nctx = ''; // XXX
    addInlineCreationForm(value[1], value[2], value[3], value[4],
                          i18nctx, $holder);
}
        """)
        form._cw.add_onload(u'''if (!docloaded) {
  jQuery("input:radio").change(switchInlinedForm);''
  docloaded = true;
}
''')
        formid = u'f%s' % hex(id(self))
        with div(w):
            for targettype in self.find_targettypes(entity):
                inputargs = {
                    'value': u'%s;%s;%s;%s;%s' % (formid, entity.eid, targettype,
                                                  self.rtype, self.role),
                    }
                if targettype == selected:
                    inputargs['checked'] = u'checked'
                w(input(type=u'radio', name=self.rtype, **inputargs))
                w(u'%s <br />' % display_name(form._cw, targettype,
                                              context='inlined:%s.%s.%s' % (eschema, self.rtype, self.role)))
        w(div(self.initial_form(form, entity, selected)))
        w(div(u'', id=formid)) # needed by addInlineCreationForm()
        return u'\n'.join(unicode(x) for x in data)

## forms ######################################################################
uicfg.autoform_field.tag_subject_of(('TimeSeriesHandle', 'defined_by', '*'),
                                    RelationSwitchField(role='subject',
                                                        name='defined_by',
                                                        label=('TimeSeriesHandle', 'defined_by'),
                                                        required=True))

uicfg.autoform_section.tag_subject_of(('BlockConstantTSValue', 'blocks', '*'),
                                         'main', 'inlined')
uicfg.autoform_section.tag_subject_of(('ConstantAndExceptionTSValue', 'has_exceptions', '*'),
                                         'main', 'inlined')

## primary views ##############################################################
uicfg.primaryview_section.tag_subject_of(('*', 'defined_by', '*'),
                                         'relations')
uicfg.primaryview_section.tag_object_of(('*', 'defined_by', '*'),
                                         'attributes')
uicfg.primaryview_section.tag_subject_of(('ConstantAndExceptionTSValue', 'has_exceptions', '*'),
                                         'relations')
uicfg.primaryview_display_ctrl.tag_subject_of(('ConstantAndExceptionTSValue', 'has_exceptions', '*'),
                                              {'vid': 'list', 'order': 10})

uicfg.primaryview_section.tag_subject_of(('BlockConstantTSValue', 'blocks', '*'),
                                         'relations')
uicfg.primaryview_display_ctrl.tag_subject_of(('BlockConstantTSValue', 'blocks', '*'),
                                              {'vid': 'list', 'order': 10})

