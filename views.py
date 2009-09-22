"""cube-specific forms/views/actions/components

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from cubicweb.web.views import primary
from cubicweb.web.views import baseviews
from logilab.mtconverter import xml_escape
from cubicweb.common.uilib import cut, printable_value
from cubicweb.web.views.plots import FlotPlotWidget, datetime2ticks
from cubicweb.selectors import implements

class TimeSeriesPrimaryView(primary.PrimaryView):
    __select__ = implements('TimeSeries')

    def summary(self, entity):
        entity.view('ts_plot', w = self.w, width=640, height=480)
        entity.view('ts_summary', w=self.w)

class TimeSeriesPlotView(baseviews.EntityView):
    id = 'ts_plot'
    __select__ = implements('TimeSeries')
    def build_plot_data(self, entity):
        plots = []
        for ts in self.rset.entities():
            plots.append(ts.timestamped_array())
        return plots
    
    def call(self, width=None, height=None):
        form = self.req.form
        width = width or form.get('width', 500)
        height = height or form.get('height', 400)
        names = []
        plots = []
        for ts in self.rset.entities():
            names.append(ts.dc_title())
            plots.append(ts.timestamped_array())
        plotwidget = FlotPlotWidget(names, plots, timemode=True)
        plotwidget.render(self.req, width, height, w=self.w)

    def cell_call(self, row, col, width=None, height=None):
        ts = self.rset.get_entity(row, col)
        plotwidget = FlotPlotWidget([ts.dc_title()],
                                    [ts.timestamped_array()],
                                    timemode=True)
        plotwidget.render(self.req, width, height, w=self.w)


class TimeSeriesSummaryView(baseviews.EntityView):
    id = 'ts_summary'
    __select__ = implements('TimeSeries')
    def cell_call(self, row, col):
        entity = self.rset.get_entity(row, col)
        self.w(u'<p>Summary:\n<ul>')
        for attr in ('first', 'last', 'min', 'max', 'average', 'sum'):
            self.w(u'<li>%s: %.2f</li>' % (attr, getattr(entity, attr)))
        self.w(u'</ul></p>')
