"""this contains the cube-specific entities' classes

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from cubicweb import Binary
from cubicweb.entities import AnyEntity

import pickle
import csv

# TODO: remove datetime and use our own calendars
import datetime

import numpy

TIME_DELTAS = {'15 min': datetime.timedelta(minutes=15),
               'hourly': datetime.timedelta(hours=1),
               'daily': datetime.timedelta(days=1),
               'weekly': datetime.timedelta(weeks=1),
               'monthly': datetime.timedelta(days=30), # XXX
               'yearly': datetime.timedelta(days=365),
               }

class TimeSeries(AnyEntity):
    id = 'TimeSeries'

    @property
    def array(self):
        if not hasattr(self, '_array'):
            self._array = pickle.load(self.data)
        return self._array

    def dc_title(self):
        return _(u'Time series starting on %s with %d values' % (self.start_date, self.length))

    def grok_data(self):
        """
        called in a before_update_entity_hook
        
        self.data is something such as an excel file or CSV data or a
        pickled numpy array. Ensure it a pickle numpy array before
        storing object in db.
        """
        filename = self.data.filename.lower()
        if filename.endswith('.csv'):
            numpy_array = self._numpy_from_csv(self.data)
        elif filename.endswith('.xls'):
            numpy_array = self._numpy_from_excel(self.data)
        elif filename.endswith('.txt'):
            pass
        else:
            raise ValueError('Unsupported file type %s' % self.data.filename)

        self.data = Binary()
        pickle.dump(numpy_array, self.data)

    def timestamped_array(self):
        step = TIME_DELTAS[self.granularity]
        date = self.start_date
        data = []
        for v in self.array:
            data.append((date, v))
            date += step
        return data

    @property
    def first(self):
        return self.array[0]
    
    @property
    def last(self):
        return self.array[-1]
    
    @property
    def length(self):
        return self.array.size
    
    @property
    def min(self):
        return self.array.min()

    @property
    def max(self):
        return self.array.max()

    @property
    def sum(self):
        return self.array.sum()

    @property
    def average(self):
        return self.array.mean()
    


    def _numpy_from_csv(self, file):
        sniffer = csv.Sniffer()
        raw_data = file.read()
        try:
            dialect = sniffer.sniff(raw_data, sniffer.preferred)
            has_header = sniffer.has_header(raw_data)
        except csv.Error, exc:
            self.exception('Problem sniffing file %s', file.filename)
            dialect = csv.excel
            has_header = False
        file.seek(0)
        reader = csv.reader(file, dialect)
        if has_header:
            reader.next()
        series = []
        # TODO: check granularity if we have a date column
        for line, values in enumerate(reader):
            if len(values) not in (1, 2):
                raise ValueError('Too many columns in %s' % file.filename)
            try:
                val = float(values[-1])
            except ValueError:
                if line == 0 and not has_header:
                    self.debug('error while parsing first line of %s', file.filename)
                    continue # assume there was a header
                else:
                    raise ValueError('unable to read value on line %d of %s' % (reader.line_num, file.filename))
            series.append(val)

        return numpy.array(series)


    def _numpy_from_excel(self, file):
        raise ValueError('Cannot process excel files yet')
