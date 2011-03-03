from logilab.mtconverter import xml_escape

from cwtags.tag import span, div, a

import numpy

from cubicweb.selectors import is_instance
from cubicweb.view import EntityView
from cubicweb.web.views.baseviews import InContextView

class TimeSeriesSparkLine(EntityView):
    """ display a timeseries with sparkline
    see: http://omnipotent.net/jquery.sparkline/
    """
    __regid__ = 'sparkline'
    __select__ = is_instance('TimeSeries')
    onload = """
var jqelt = jQuery('#sparklinefor%(target)s');
if (jqelt.attr('cubicweb:type') != 'prepared-sparkline') {
    jqelt.sparkline('html', {%(plot_type)s, height:20, width:120});
    jqelt.attr('cubicweb:type', 'prepared-sparkline');
}
"""

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
            if len(data) > 500:
                data = self._resample(data, 500)
                plot_type = "type : 'line'"
            elif len(data) > 25:
                data = self._resample(data, 25)
        req.html_headers.add_onload(self.onload % {'target': entity.eid,
                                                   'plot_type' : plot_type})
        with span(w, id='sparklinefor%s' % entity.eid):
            w(xml_escape(','.join(unicode(elt) for elt in data)))

    def _resample(self, data, sample_length):
        step = len(data) / sample_length
        newdata = []
        for idx in xrange(0, len(data), step):
            newdata.append(data[idx:idx+step].mean())
        return newdata



class TimeSeriesInContextView(InContextView):
    """ show the sparklines of the time series variants """
    __regid__ = 'incontext'
    __select__ = is_instance('TimeSeries')
    inner_vid = 'summary'

    def cell_call(self, row, col):
        w = self.w
        entity = self.cw_rset.get_entity(row, col)
        if entity.is_constant and isinstance(entity.first, (bool, numpy.bool_)):
            w(span(self._cw._(unicode(entity.first_unit))))
        else:
            with div(w, style='display: inline'):
                # XXX values should be rounded at the data level
                first = unicode(str(round(entity.first, 2)))
                last = unicode(str(round(entity.last, 2)))
                w(span(xml_escape(first+entity.safe_unit), style='font-size: 10px;'))
                with div(w, Class='info'):
                    with a(w, href=entity.absolute_url()):
                        w("&#xA0;&#xA0;")
                        w(entity.view('sparkline'))
                        w("&#xA0;&#xA0;")
                w(span(xml_escape(last+entity.safe_unit), style='font-size: 10px;'))
                w("&#xA0;")
                w(div(entity.view(self.inner_vid, label=_('[summary]')),
                      style='display: inline'))
                url = entity.absolute_url(vid='tsxlexport')
                with span(w, Class='tsexport'):
                    with a(w, href=url):
                        w(self._cw._(u'[export]'))

