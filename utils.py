"""this contains the cube-specific utilities

:organization: Logilab
:copyright: 2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
import numpy

def numpy_val_map(val):
    # XXX for some reason the workbook handles numpy.float64 fine
    #     but not numpy.int32
    # XXX (auc) shouldn't we track usage of this and replace
    #     with TimeSeries._dtypes_in/out ?
    if isinstance(val, numpy.int32):
        return int(val)
    if isinstance(val, numpy.bool_):
        return bool(val)
    return val


def get_formatter(req, entity):
    cw_datetime_format = req.property_value('ui.datetime-format')
    cw_date_format = req.property_value('ui.date-format')
    if entity.granularity in (u'15min', 'hourly', 'time_vector'):
        dateformat = cw_datetime_format #'%Y/%m/%d %H:%M'
    else:
        dateformat = cw_date_format #'%Y/%m/%d'
    if entity.data_type in ('Integer', 'Boolean'):
        numformatter = lambda x:x
        numformat = '%d'
    else:
        numformatter = lambda x:req.format_float(x)
        numformat = '%s'
    return dateformat, numformat, numformatter
