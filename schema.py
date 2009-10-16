# cube's specific schema
"""

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""

_ = unicode

from yams.buildobjs import EntityType, String, Bytes, Date, Datetime, SubjectRelation
from yams.constraints import StaticVocabularyConstraint

class TimeSeries(EntityType):
    name = String(required=True,
                  fulltextindexed=True,
                  maxsize=255,
                  unique=True)

    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))

    granularity = String(description=_('Granularity'),
                         required=True,
                         internationalizable=True,
                         vocabulary = [_('15 min'), _('hourly'), _('daily'),
                                       _('weekly'), _('monthly'), _('yearly')],
                         default='daily')

    use_calendar = String(description=_('Calendar used'),
                      required=True,
                      internationalizable=True,
                      vocabulary = (_('gregorian'), _('normalized'), _('gas'),),
                      default='gregorian')

    start_date = Date(description=_('Start date'),
                          required=True,
                          default='TODAY')

    data = Bytes(required=True,
                 description = _('Timeseries data'))



class TimeSeriesHandle(EntityType):
    name = String(required=True,
                  fulltextindexed=True,
                  maxsize=255,
                  unique=True)

    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))

    granularity = String(description=_('Granularity'),
                         required=True,
                         internationalizable=True,
                         vocabulary = [_('15 min'), _('hourly'), _('daily'),
                                       _('weekly'), _('monthly'), _('yearly')],
                         default='daily')

    use_calendar = String(description=_('Calendar used'),
                      required=True,
                      internationalizable=True,
                      vocabulary = (_('gregorian'), _('normalized'), _('gas'),),
                      default='gregorian')

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

class BlockConstantTSValue(_TimeSeriesValue):
    """
    composite de start date, value
    """

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
