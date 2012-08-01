from __future__ import division

from logilab.mtconverter import xml_escape

import numpy

from cubicweb import tags
from cubicweb.predicates import is_instance
from cubicweb.view import EntityView
from cubicweb.web.views.baseviews import InContextView

class TimeSeriesSparkLine(EntityView):
    """ display a timeseries with sparkline
    see: http://omnipotent.net/jquery.sparkline/
    """
    __regid__ = 'sparkline'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
    onload = """
var jqelt = jQuery('#sparklinefor%(target)s');
if (jqelt.attr('cubicweb:type') != 'prepared-sparkline') {
    jqelt.sparkline('html', {%(plot_type)s, height:20, width:120});
    jqelt.attr('cubicweb:type', 'prepared-sparkline');
}
"""
    _switch_to_line_threshold = 500
    _downsample_threshold = 18

    def cell_call(self, row, col):
        w = self.w; req = self._cw
        if req.ie_browser():
            req.add_js('excanvas.js')
        req.add_js('jquery.sparkline.js')
        entity = self.cw_rset.get_entity(row, col)
        plot_type = "type : 'bar', barWidth : 5"
        if entity.is_constant:
            data = [entity.first] * 10
        else:
            data = entity.array
            if len(data) > self._switch_to_line_threshold:
                data = self._resample(data, self._switch_to_line_threshold)
                plot_type = "type : 'line'"
            elif len(data) > self._downsample_threshold:
                data = self._resample(data, self._downsample_threshold)
        req.html_headers.add_onload(self.onload % {'target': entity.eid,
                                                   'plot_type' : plot_type})
        content = u'<!-- %s -->' % xml_escape(u', '.join(unicode(elt) for elt in data))
        w(tags.span(content, id='sparklinefor%s' % entity.eid,
                    escapecontent=False))

    def _resample(self, data, sample_length):
        newdata = []
        datalen = len(data)
        for x in xrange(sample_length):
            idx = int(((x + .5) / sample_length) * datalen)
            newdata.append(data[idx])
        return newdata



class TimeSeriesInContextView(InContextView):
    """ show the sparklines of the time series variants """
    __regid__ = 'incontext'
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')
    inner_vid = 'summary'

    def cell_call(self, row, col):
        w = self.w
        _ = self._cw._
        entity = self.cw_rset.get_entity(row, col)
        if entity.is_constant and isinstance(entity.first, (bool, numpy.bool_)):
            w(tags.span(_(unicode(entity.first_unit))))
        else:
            w(u'<div style="display: inline">')
            # XXX values should be rounded at the data level
            first = unicode(str(round(entity.first, 2)))
            last = unicode(str(round(entity.last, 2)))
            w(tags.span(first+entity.safe_unit, style='font-size: 10px;'))
            w(u'<div class="info">')
            content = u"&#xA0;&#xA0;%s&#xA0;&#xA0;" % entity.view('sparkline')
            w(tags.a(content, href=entity.absolute_url(),
                     escapecontent=False))
            w(u'</div>')
            w(tags.span(last+entity.safe_unit, style='font-size: 10px;'))
            w(u'&#xA0;')
            w(u'<div style="display: inline">')
            entity.view(self.inner_vid, label=_('[summary]'), w=w)
            w(u'</div>')
            url = entity.absolute_url(vid='tsxlexport')
            w(tags.span(tags.a(_(u'[export]'), href=url), klass='tsexport',
                        escapecontent=False))
            w(u'</div>')

