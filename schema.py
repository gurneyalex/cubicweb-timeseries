# cube's specific schema
"""
:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
_ = unicode

from yams.buildobjs import (EntityType, String, Bytes, Boolean, #pylint:disable-msg=E0611
                            Float, Datetime, SubjectRelation,)  #pylint:disable-msg=E0611
from yams.constraints import StaticVocabularyConstraint

class TimeSeries(EntityType):
    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))

    granularity = String(description=_('Granularity'),
                         required=True,
                         internationalizable=True,
                         vocabulary = [_('15min'), _('hourly'), _('daily'),
                                       _('weekly'), _('monthly'), _('yearly'),
                                       _('constant')],
                         default='daily')

    start_date = Datetime(description=_('Start date'),
                          required=True,
                          default='TODAY')

    data = Bytes(required=True,
                 description = _('Timeseries data'))


#
# Below is some work in progress, not yet used in Pylos
#

class TimeSeriesHandle(EntityType):
    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))

    granularity = String(description=_('Granularity'),
                         required=True,
                         internationalizable=True,
                         vocabulary = [_('15 min'), _('hourly'), _('daily'),
                                       _('weekly'), _('monthly'), _('yearly')],
                         default='daily')

    start_date = Datetime(description=_('Start date'),
                          required=True,
                          default='TODAY')

    end_date = Datetime(description=_('End date'),
                        required=True)


    defined_by = SubjectRelation(('ExcelTSValue',
                                  'BlockConstantTSValue',
                                  'ConstantAndExceptionTSValue'),
                                 cardinality='1?',
                                 inlined=True, composite='subject')


class _TimeSeriesValue(EntityType):
    pass

class ExcelTSValue(_TimeSeriesValue):
    """
    the current version adapted a little bit
    """
class TSConstantBlock(EntityType):
    start_date = Datetime(required=True)
    value = Float(required=True) # XXX add a value_unit metadata attribute

class BlockConstantTSValue(_TimeSeriesValue):
    """
    composite of start_date, value
    """
    blocks = SubjectRelation('TSConstantBlock', cardinality='+1', composite='subject')

class TSConstantExceptionBlock(EntityType):
    start_date = Datetime(required=True)
    stop_date = Datetime(required=True)
    value = Float(required=True) # XXX add a value_unit metadata attribute

class ConstantAndExceptionTSValue(_TimeSeriesValue):
    """
    default value + composite start-end, value
    """
    value = Float(required=True) # XXX add a value_unit metadata attribute
    has_exceptions = SubjectRelation('TSConstantExceptionBlock', cardinality='*1',
                                     composite='subject')
