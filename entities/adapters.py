import tempfile
import os
import csv
from cStringIO import StringIO

from cubicweb.selectors import is_instance, ExpectedValueSelector
from cubicweb.view import EntityAdapter

from cubes.timeseries.utils import get_formatter
from cubes.timeseries.entities import utils

class TimeSeriesExportAdapter(EntityAdapter):
    __regid__ = 'ITimeSeriesExporter'
    __abstract__ = True
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')

    def export(self):
        raise NotImplementedError

class mimetype(ExpectedValueSelector):

    def _get_value(self, cls, req, **kwargs):
        return kwargs.get('mimetype')

class TimeSeriesCSVexport(TimeSeriesExportAdapter):
    """ export timestamped array to paste-into-excel-friendly csv """
    __select__ = TimeSeriesExportAdapter.__select__ & mimetype('text/csv')

    def export(self):
        entity = self.entity
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        out = StringIO()
        dateformat, _numformat, _numformatter = get_formatter(self._cw, entity)
        writer = csv.writer(out, dialect='excel', delimiter='\t')
        for date, value in entity.timestamped_array():
            outvalue = str(entity.output_value(value)).replace('.', dec_sep)
            writer.writerow([date.strftime(dateformat), outvalue])
        return out.getvalue()

class TimeSeriesXLSExport(TimeSeriesExportAdapter):
    __select__ = TimeSeriesExportAdapter.__select__ & mimetype('application/vnd.ms-excel')

    def export(self):
        # XXX timestamps ?
        entity = self.entity
        tsbox = entity.reverse_ts_variant[0]
        workbook = utils.xlwt.Workbook()
        sheet = workbook.add_sheet(('TS_%s' % tsbox.name)[:31])
        outrows = []
        class Writer(object):
            def write(self, data):
                """ callback to comply to workbook.save api """
                outrows.append(data)
        for rownum, val in enumerate(entity.array):
            sheet.write(rownum, 0, entity.output_value(val))
        workbook.save(Writer())
        return ''.join(outrows)

class TimeSeriesXLSXExport(TimeSeriesExportAdapter):
    __select__ = (TimeSeriesExportAdapter.__select__ &
                  mimetype('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))

    def export(self):
        entity = self.entity
        tsbox = entity.reverse_ts_variant[0]
        workbook = utils.openpyxl.workbook.Workbook(optimized_write=True)
        sheet = workbook.create_sheet()
        sheet.title = ('TS_%s' % tsbox.name)[:31]
        outrows = []
        for val in entity.array:
            sheet.append([entity.output_value(val)])
        try:
            # XXX investigate why save_virtual_workbook
            #     does not work
            fd, fname = tempfile.mkstemp()
            # let's windows not complain about a locked file
            os.close(fd)
            workbook.save(fname)
            with open(fname, 'rb') as xlsx:
                return xlsx.read()
        finally:
            try:
                os.unlink(fname)
            except:
                pass


