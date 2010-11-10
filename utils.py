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
    if isinstance(val, numpy.int32):
        return int(val)
    if isinstance(val, numpy.bool_):
        return bool(val)
    return val


def get_formatter(req, entity):
    if entity.granularity in (u'15min', 'hourly'):
        dateformat = '%Y/%m/%d %H:%M'
    else:
        dateformat = '%Y/%m/%d'
    if entity.data_type in ('Integer', 'Boolean'):
        numformatter = lambda x:x
        numformat = '%d'
    else:
        numformatter = lambda x:req.format_float(x)
        numformat = '%s'
    return dateformat, numformat, numformatter
