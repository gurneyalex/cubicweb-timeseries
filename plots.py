"""basic plot views

:organization: Logilab
:copyright: 2007-2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
__docformat__ = "restructuredtext en"

import os
import time

from simplejson import dumps

from logilab.common import flatten
from logilab.mtconverter import xml_escape

from cubicweb.utils import make_uid, UStringIO, datetime2ticks
from cubicweb.appobject import objectify_selector
from cubicweb.web.views import baseviews
from cubicweb.web.views.plots import PlotWidget

class TSFlotPlotWidget(PlotWidget):
    """PlotRenderer widget using Flot"""
    onload = u"""
var fig = jQuery("#%(figid)s");

if (fig.attr('cubicweb:type') != 'prepared-plot') {

    %(plotdefs)s
    
    var mainoptions = {points: {show: true, radius: 3},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: true},
         xaxis: {mode: "time"},
         selection: {mode: "x"}
         }
         
    var overviewoptions = {points: {show: false},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: false},
         xaxis: {mode: "time"},
         selection: {mode: "x"}
         }

    var main = jQuery.plot(jQuery("#main%(figid)s"), [%(plotdata)s], mainoptions);
    
    var overview = jQuery.plot(jQuery("#overview%(figid)s"), [%(plotdata)s], overviewoptions);
         
    jQuery("#main%(figid)s").bind("plothover", onTSPlotHover);
    
    // now connect the two
    
    jQuery("#main%(figid)s").bind("plotselected", function (event, ranges) {
    
        // do the zooming
        main = jQuery.plot(jQuery("#main%(figid)s"), [%(plotdata)s],
                      jQuery.extend(true, {}, mainoptions, {
                          xaxis: { min: ranges.xaxis.from, max: ranges.xaxis.to }
                      }));
    
        // don't fire event on the overview to prevent eternal loop
        overview.setSelection(ranges, true);
    });
    
    jQuery("#overview%(figid)s").bind("plotselected", function (event, ranges) {
        main.setSelection(ranges);
    });

    
    fig.attr('cubicweb:type','prepared-plot');
}
"""

    def __init__(self, labels, plots):
        self.labels = labels
        self.plots = plots # list of list of couples

    def dump_plot(self, plot):
        plot = [(datetime2ticks(x), y) for x,y in plot]
        return dumps(plot)

    def _render(self, req, width=900, height=250):
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js(('jquery.flot.js', 
                    'timeseries.flot.js', 
                    'jquery.flot.selection.js',
                    'jquery.corner.js'))
        figid = u'figure%s' % req.varmaker.next()
        plotdefs = []
        plotdata = []
        self.w(u'<div id="main%s" style="width: %spx; height: %spx;"></div>' %
               (figid, width, height))
        self.w(u'<div id="overview%s" style="width: %spx; height: 80px;"></div>' %
               (figid, width))
        for idx, (label, plot) in enumerate(zip(self.labels, self.plots)):
            plotid = '%s_%s' % (figid, idx)
            plotdefs.append('var %s = %s;' % (plotid, self.dump_plot(plot)))
            # XXX ugly but required in order to not crash my demo
            plotdata.append("{label: '%s', data: %s}" % (label.replace(u'&', u''), plotid))

        req.html_headers.add_onload(self.onload %
                                    {'plotdefs': '\n'.join(plotdefs),
                                     'figid': figid,
                                     'plotdata': ','.join(plotdata),
                                     },
                                    jsoncall=req.form.get('jsoncall', False))

