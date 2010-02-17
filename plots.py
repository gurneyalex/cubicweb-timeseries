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
from logilab.common.date import datetime2ticks
from logilab.mtconverter import xml_escape

from cubicweb.utils import make_uid, UStringIO
from cubicweb.appobject import objectify_selector
from cubicweb.web.views import baseviews
from cubicweb.web.views.plots import PlotWidget

class TSFlotPlotWidget(PlotWidget):
    """PlotRenderer widget using Flot"""
    onload = u"""

var mainfig = jQuery("#main%(figid)s");
var overviewfig = jQuery("#overview%(figid)s");

if ((mainfig.attr('cubicweb:type') != 'prepared-plot') || (overviewfig.attr('cubicweb:type') != 'prepared-plot')){

    %(plotdefs)s

    var mainoptions = {points: {show: true, radius: 2},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: true, clickable: true},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
         }

    var overviewoptions = {points: {show: false},
         lines: {show: true, lineWidth: 1},
         grid: {hoverable: false},
         xaxis: {mode: "time"},
         selection: {mode: "x", color: 'blue'}
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

    jQuery("#reset").click(function () {
        jQuery.plot(jQuery("#main%(figid)s"), [%(plotdata)s], mainoptions);
        overview.clearSelection();
    });

    mainfig.attr('cubicweb:type','prepared-plot');
    overviewfig.attr('cubicweb:type','prepared-plot');
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
                    'jquery.js'))
        figid = u'figure%s' % req.varmaker.next()
        plotdefs = []
        plotdata = []
        self.w(u'<div id="main%s" style="width: %spx; height: %spx;"></div>' %
               (figid, width, height))
        self.w(u'<div id="overview%s" style="width: %spx; height: %spx;"></div>' %
               (figid, width, height/3))
        self.w(u'<button id="reset">Reset</button>')
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

class TSHighChartsPlotWidget(PlotWidget):
    """PlotRenderer widget using HighCharts"""
    onload = u"""
var mainfig = jQuery("#main%(figid)s");
var overviewfig = jQuery("#overview%(figid)s");

if ((mainfig.attr('cubicweb:type') != 'prepared-plot') || (overviewfig.attr('cubicweb:type') != 'prepared-plot')){

    var chart_options = {
        renderTo: 'main%(figid)s',
        zoomType: 'x'
    } 
    
    var color_values = [
        '#007a69',
        '#4572A7', 
        '#AA4643', 
        '#89A54E', 
        '#80699B', 
        '#3D96AE', 
        '#DB843D', 
        '#92A8CD', 
        '#A47D7C', 
        '#B5CA92'
    ] 
    
    var title_options = {
        text: ''
    } 
            
    var subtitle_options = {
        text: ''
    } 
            
    var xAxis_options = {
        type: 'datetime',
        title: {
            text: null
        }
    }
            
    var yAxis_options = {
        title: {
            text: '.'
        }
    }
            
    var legend_options = {
        enabled: false
    }
            
    var plotOptions_options = {
        line: {
            animation: false,
            linewidth: 1,
            marker: {
                enabled: false
            },
            shadow: false
        }
    }
            
    var series_data = %(plotdefs)s
            
    var series_options = [{
        type: 'line',
        data: series_data
    }]
             
    var tooltip_options = {
        formatter: function() {
            return Highcharts.dateFormat('%%Y-%%m-%%d %%H:%%M', this.x) + ':<br/>'+
                + Highcharts.numberFormat(this.y, 2);
        }
    }
            
    var chart = new Highcharts.Chart({
        chart: chart_options,
        colors: color_values,
        title: title_options,
        subtitle: subtitle_options,
        xAxis: xAxis_options,
        yAxis: yAxis_options,
        legend: legend_options,
        plotOptions: plotOptions_options,
        tooltip: tooltip_options,
        series: series_options
    });
            
    mainfig.attr('cubicweb:type','prepared-plot');
    overviewfig.attr('cubicweb:type','prepared-plot');
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
            req.add_js('excanvas.compiled.js')
        req.add_js(('highcharts.js', 
                    'jquery.js'))
        figid = u'figure%s' % req.varmaker.next()
        plotdefs = []
        self.w(u'<div id="main%s" style="width: %spx; height: %spx;"></div>' %
               (figid, width, height))
        self.w(u'%nbsp;')
        for idx, (label, plot) in enumerate(zip(self.labels, self.plots)):
            plotid = '%s_%s' % (figid, idx)
            plotdefs.append('%s;' % self.dump_plot(plot))

        req.html_headers.add_onload(self.onload %
                                    {'plotdefs': '\n'.join(plotdefs),
                                     'figid': figid,
                                     },
                                    jsoncall=req.form.get('jsoncall', False))
