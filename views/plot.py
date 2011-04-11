"""cube-specific plot-like views

:organization: Logilab
:copyright: 2001-2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement, division

from logilab.common.date import datetime2ticks
from logilab.mtconverter import xml_escape

from cwtags.tag import div, button

from cubicweb.utils import json_dumps as dumps
from cubicweb.selectors import is_instance
from cubicweb.web.views import baseviews

_ = unicode


class TimeSeriesPlotView(baseviews.EntityView):
    __regid__ = 'ts_plot'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
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
        w(div(id='main%s' % figid, style='width: %spx; height: %spx;' % (width, height)))
        w(div(id='overview%s' % figid, style='width: %spx; height: %spx;' % (width, height/3)))
        w(button(req._('Zoom reset'), id='reset', Class='validateButton'))
        plotdata = ("{label: '%s', data: %s}" % (xml_escape(ts.dc_title()), self.dump_plot(ts))
                    for ts in self.cw_rset.entities())
        req.html_headers.add_onload(self.onload %
                                    {'figid': figid,
                                     'plotdata': ','.join(plotdata)})
