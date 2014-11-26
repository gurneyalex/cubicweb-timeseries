"""cube-specific plot-like views

:organization: Logilab
:copyright: 2010-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

from logilab.common.date import datetime2ticks
from logilab.mtconverter import xml_escape

from cubicweb import tags
from cubicweb.utils import json_dumps as dumps
from cubicweb.predicates import is_instance, score_entity
from cubicweb.web.views import baseviews

_ = unicode


class TimeSeriesPlotView(baseviews.EntityView):
    __regid__ = 'ts_plot'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries') & score_entity(lambda x: not x.is_constant)
    title = None
    onload = u"init_ts_plot('%(figid)s', [%(plotdata)s]);"

    def dump_plot(self, ts):
        plot = [(datetime2ticks(x), y)
                for x,y in ts.compressed_timestamped_array()]
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
        w(tags.div(None, id='main%s' % figid, style='width: %spx; height: %spx;' % (width, height)))
        w(tags.div(None, id='overview%s' % figid, style='width: %spx; height: %spx;' % (width, height/3)))
        w(tags.button(req._('Zoom reset'), id='reset', klass='validateButton'))
        plotdata = ("{label: '%s', data: %s}" % (xml_escape(ts.dc_title()), self.dump_plot(ts))
                    for ts in self.cw_rset.entities())
        req.html_headers.add_onload(self.onload %
                                    {'figid': figid,
                                     'plotdata': ','.join(plotdata)})
