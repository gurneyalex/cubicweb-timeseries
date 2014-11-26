"""this contains the cube-specific entities' adapters

:organization: Logilab
:copyright: 2009-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
import tempfile
import os
import csv
import zlib
import datetime
import pickle
import os.path as osp
from cStringIO import StringIO

import numpy

from cubicweb import Binary, ValidationError
from cubicweb.predicates import is_instance, ExpectedValuePredicate
from cubicweb.view import EntityAdapter

from cubes.timeseries.utils import get_formatter
from cubes.timeseries.entities import utils

_ = unicode

class mimetype(ExpectedValuePredicate):
    """ a selector for exporters  """

    def _get_value(self, cls, req, **kwargs):
        return kwargs.get('mimetype')

class filename_ext(ExpectedValuePredicate):
    """ a selector for converters  """

    def _get_value(self, cls, req, **kwargs):
        fname = kwargs.get('filename')
        if fname:
            return osp.splitext(fname)[1]
        return fname


# importers ####################################################################

class TSImportAdapter(EntityAdapter):
    """ import from various sources, delegates actual job to various other adapters
    entry point typically triggered from creation/udpate hook """

    __regid__ = 'TimeSeriesImporter'
    __select__ = is_instance('TimeSeries')

    def grok_data(self):
        """ self.data is something such as an excel file or CSV data or a pickled
        numpy array or an already processed binary.

        Ensure it's a pickle numpy array before storing object in db.

        If data seems to be already processed, return True, else return False.
        """
        entity = self.entity
        try:
            filename = entity.data.filename.lower()
        except AttributeError:
            data = entity.data
            if isinstance(data, Binary):
                return True
            # if not isinstance(data, numpy.ndarray):
            #     raise TypeError('data is neither a Binary nor a numpy array (%s)' % type(data))
            numpy_array = data
        else:
            adapter = self._cw.vreg['adapters'].select_or_none('source_to_numpy_array',
                                                               self._cw, entity=entity, filename=filename)
            if adapter is None:
                msg = self._cw._('Unsupported file type %s') % entity.data.filename
                raise ValidationError(entity.eid, {'data': msg})
            numpy_array = adapter.to_numpy_array(entity.data, filename)

        if numpy_array.ndim != 1:
            raise ValidationError(entity.eid,
                                  {'data': _('data must be a 1-dimensional array')})
        if numpy_array.size == 0:
            raise ValidationError(entity.eid,
                                  {'data': _('data must have at least one value')})
        data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        data.write(compressed_data)
        entity.cw_edited['data'] = data
        entity.array = numpy_array
        return False

class NPTSImportAdapter(TSImportAdapter):
    __select__ = is_instance('NonPeriodicTimeSeries')

    def grok_data(self):
        # XXX when data is a csv/txt/xl file, we want to read timestamps in
        # there too
        # XXX hooks won't catch change to timestamps
        if super(NPTSImportAdapter, self).grok_data():
            return # already processed
        numpy_array = self.grok_timestamps()
        tstamp_data = Binary()
        compressed_data = zlib.compress(pickle.dumps(numpy_array, protocol=2))
        tstamp_data.write(compressed_data)
        self.entity.cw_edited['timestamps'] = tstamp_data
        self.entity.timestamps_array = numpy_array

    def grok_timestamps(self):
        timestamps = self.entity.timestamps
        if len(timestamps) != self.entity.count:
            raise ValueError('data/timestamps vectors size mismatch')
        if isinstance(timestamps[0], (datetime.datetime, datetime.date)):
            timestamps = [self.entity.calendar.datetime_to_timestamp(v)
                          for v in timestamps]
        else:
            assert isinstance(timestamps[0], (int, float))
        tstamp_array = numpy.array(timestamps, dtype=numpy.float64)
        if not (tstamp_array[:-1] < tstamp_array[1:]).all():
            raise ValueError('time stamps must be a strictly ascendant vector')
        return tstamp_array


# source to numpy array converters #############################################

class TSTXTToNumpyArray(EntityAdapter):
    __regid__ = 'source_to_numpy_array'
    __select__ = is_instance('TimeSeries') & filename_ext('.txt')


    def to_numpy_array(self, file, filename):
        try:
            return numpy.array([float(x.strip().split()[-1]) for x in file],
                               dtype=self.entity.dtype)
        except ValueError:
            raise ValueError('invalid data in %s (expecting one number per line '
                             '(with optionally a date in the first column), '
                             'with . as the decimal separator)' % filename)


class CSVImportMixin(object):

    def snif_csv_dialect(self, file):
        sniffer = csv.Sniffer()
        raw_data = file.read()
        try:
            dialect = sniffer.sniff(raw_data, sniffer.preferred)
            has_header = sniffer.has_header(raw_data)
        except csv.Error:
            self.exception('Problem sniffing file %s', file.filename)
            dialect = csv.excel
            has_header = False
        file.seek(0)
        return dialect, has_header


class TSCSVToNumpyArray(CSVImportMixin, EntityAdapter):
    __regid__ = 'source_to_numpy_array'
    __select__ = is_instance('TimeSeries') & filename_ext('.csv')


    def to_numpy_array(self, file, filename, dialect=None, has_header=False):
        if dialect is None:
            dialect, has_header = self.snif_csv_dialect(file)
        else:
            assert dialect in csv.list_dialects()
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        # TODO: check granularity if we have a date column
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        th_sep = prefs.thousands_separator or ''
        for line, values in enumerate(reader):
            if len(values) not in (1, 2):
                raise ValueError('Too many columns in %s' % filename)
            try:
                strval = values[-1].replace(th_sep, '').replace(dec_sep, '.')
                val = float(strval)
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', filename)
                    continue # assume there was a header
                else:
                    raise ValueError('Invalid data type for value %s on line %s of %s' %
                                     (values[-1], reader.line_num, filename))
            series.append(val)
        return numpy.array(series, dtype=self.entity.dtype)


class TSXLSToNumpyArray(EntityAdapter):
    __regid__ = 'source_to_numpy_array'
    __select__ = is_instance('TimeSeries') & filename_ext('.xls')

    def to_numpy_array(self, file, filename):
        xl_data = file.read()
        wb = utils.xlrd.open_workbook(filename=file.filename,
                                      file_contents=xl_data)
        sheet = wb.sheet_by_index(0)
        values = []
        col = sheet.ncols - 1
        for row in xrange(sheet.nrows):
            cell_value = sheet.cell_value(row, col)
            try:
                cell_value = float(cell_value)
            except ValueError:
                raise ValueError('Invalid data type in cell (%s, %s) of %s (data: %s)'
                                 % (row, col, filename, cell_value))
            values.append(cell_value)
        if not values:
            raise ValueError('Unable to read a Timeseries in %s' % filename)
        return numpy.array(values, dtype=self.entity.dtype)


class TSXLSXToNumpyArray(EntityAdapter):
    __regid__ = 'source_to_numpy_array'
    __select__ = is_instance('TimeSeries') & filename_ext('.xlsx')

    def to_numpy_array(self, fileobj, filename):
        wb = utils.openpyxl.reader.excel.load_workbook(filename=fileobj, use_iterators=True)
        sheet = wb.worksheets[0]
        values = []
        for rownum, row in enumerate(sheet.iter_rows()):
            cell_value = row[0].internal_value
            try:
                cell_value = float(cell_value)
            except ValueError:
                raise ValueError('Invalid data type in cell (row %d) of %s (data: %s)'
                                 % (rownum, filename, cell_value))
            values.append(cell_value)
        if not values:
            raise ValueError('Unable to read a Timeseries in %s' % filename)
        return numpy.array(values, dtype=self.entity.dtype)


class NDTSCSVToNumpyArray(CSVImportMixin, EntityAdapter):
    __regid__ = 'source_to_numpy_array'
    __select__ = is_instance('NonPeriodicTimeSeries') & (filename_ext('.csv') | filename_ext('.txt'))

    def to_numpy_array(self, file, filename, dialect=None, has_header=False):
        if dialect is None:
            dialect, has_header = self.snif_csv_dialect(file)
        else:
            assert dialect in csv.list_dialects()
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        tstamps = []
        # TODO: check granularity if we have a date column
        prefs = self._cw.user.format_preferences[0]
        dec_sep = prefs.decimal_separator
        th_sep = prefs.thousands_separator or ''
        cal = self.entity.calendar
        for line, values in enumerate(reader):
            if len(values) != 2:
                raise ValueError('Expecting exactly 2 columns (timestamp, value), found %s in %s' % (len(values), filename))
            try:
                strval = values[1].replace(th_sep, '').replace(dec_sep, '.')
                val = float(strval)
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', filename)
                    continue # assume there was a header
                else:
                    raise ValueError('Invalid data type for value %s on line %s of %s' %
                                     (values[-1], reader.line_num, filename))
            try:
                tstamp_datetime = self._cw.parse_datetime(values[0])
                tstamp = cal.datetime_to_timestamp(tstamp_datetime)
            except ValueError:
                raise
            series.append(val)
            tstamps.append(tstamp)
        self.entity.cw_attr_cache['timestamps'] = numpy.array(tstamps)
        return numpy.array(series, dtype=self.entity.dtype)


# exporters ####################################################################

class TimeSeriesExportAdapter(EntityAdapter):
    __regid__ = 'ITimeSeriesExporter'
    __abstract__ = True
    __select__ = is_instance('TimeSeries', 'NonPeriodicTimeSeries')

    def export(self):
        raise NotImplementedError

    @property
    def filename(self):
        raise NotImplementedError


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

    @property
    def filename(self):
        return 'ts.csv'


class TimeSeriesXLSExport(TimeSeriesExportAdapter):
    __select__ = TimeSeriesExportAdapter.__select__ & mimetype('application/vnd.ms-excel')

    def export(self):
        # XXX timestamps ?
        entity = self.entity
        workbook = utils.xlwt.Workbook()
        sheet = workbook.add_sheet(('TS_%s' % entity.dc_title())[:31])
        outrows = []
        class Writer(object):
            def write(self, data):
                """ callback to comply to workbook.save api """
                outrows.append(data)
        for rownum, val in enumerate(entity.array):
            sheet.write(rownum, 0, entity.output_value(val))
        workbook.save(Writer())
        return ''.join(outrows)

    @property
    def filename(self):
        return 'ts.xls'


class TimeSeriesXLSXExport(TimeSeriesExportAdapter):
    __select__ = (TimeSeriesExportAdapter.__select__ &
                  mimetype('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))

    def export(self):
        entity = self.entity
        workbook = utils.openpyxl.workbook.Workbook(optimized_write=True)
        sheet = workbook.create_sheet()
        sheet.title = ('TS_%s' % entity.dc_title())[:31]
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

    @property
    def filename(self):
        return 'ts.xlsx'


def registration_callback(vreg):
    always = [TSImportAdapter, NPTSImportAdapter, TSTXTToNumpyArray,
              TSCSVToNumpyArray, NDTSCSVToNumpyArray, TimeSeriesCSVexport]
    for adapter in always:
        vreg.register(adapter)
    if utils.HANDLE_XLS:
        vreg.register(TimeSeriesXLSExport)
        vreg.register(TSXLSToNumpyArray)
    if utils.HANDLE_XLSX:
        vreg.register(TSXLSXToNumpyArray)
        vreg.register(TimeSeriesXLSXExport)
