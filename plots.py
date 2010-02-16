"""basic plot views

:organization: Logilab
:copyright: 2007-2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement
__docformat__ = "restructuredtext en"

from simplejson import dumps

from logilab.common.date import datetime2ticks

from cwtags.tag import div, button
from cubicweb.web.views.plots import PlotWidget

class TSFlotPlotWidget(PlotWidget):
    """PlotRenderer widget using Flot"""
    onload = u"""
var mainfig = jQuery("#main%(figid)s");
var overviewfig = jQuery("#overview%(figid)s");

if ((mainfig.attr('cubicweb:type') != 'prepared-plot') ||
  (overviewfig.attr('cubicweb:type') != 'prepared-plot')) {

    %(plotdefs)s

    var mainoptions = {points: {show: true, radius: 2},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: true, clickable: true},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
         };

    var overviewoptions = {points: {show: false},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: false},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
         };

    var main = jQuery.plot(mainfig, [%(plotdata)s], mainoptions);
    var overview = jQuery.plot(overviewfig, [%(plotdata)s], overviewoptions);

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

    jQuery("#reset").click(function () {
        jQuery.plot(jQuery("#main%(figid)s"), [%(plotdata)s], mainoptions);
        overview.clearSelection();
    });

    mainfig.attr('cubicweb:type','prepared-plot');
    overviewfig.attr('cubicweb:type','prepared-plot');
};
"""

    def __init__(self, labels, plots):
        self.labels = labels
        self.plots = plots # list of list of couples

    def dump_plot(self, plot):
        plot = [(datetime2ticks(x), y) for x,y in plot]
        return dumps(plot)

    def _render(self, req, width=900, height=250):
        w = self.w
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js(('jquery.flot.js',
                    'cubes.timeseries.flot.js',
                    'jquery.flot.selection.js',
                    'jquery.js'))
        figid = u'figure%s' % req.varmaker.next()
        plotdefs = []
        plotdata = []
        w(div(id='main%s' % figid, style='width: %spx; height: %spx;' % (width, height)))
        w(div(id='overview%s' % figid, style='width: %spx; height: %spx;' % (width, height/3)))
        w(button(req._('Reset'), id='reset'))
        for idx, (label, plot) in enumerate(zip(self.labels, self.plots)):
            plotid = '%s_%s' % (figid, idx)
            plotdefs.append('var %s = %s;' % (plotid, self.dump_plot(plot)))
            # XXX ugly but required in order to not crash my demo
            plotdata.append("{label: '%s', data: %s}" % (label.replace(u'&', u''), plotid))

        req.html_headers.add_onload(self.onload %
                                    {'plotdefs': '\n'.join(plotdefs),
                                     'figid': figid,
                                     'plotdata': ','.join(plotdata)},
                                    jsoncall=req.json_request)

