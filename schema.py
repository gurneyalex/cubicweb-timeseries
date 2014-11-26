# cube's specific schema
"""
:organization: Logilab
:copyright: 2009-2011 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
_ = unicode

from yams.buildobjs import (EntityType, String, Bytes, Boolean, #pylint:disable-msg=E0611
                            Float, Datetime, SubjectRelation,
                            RelationDefinition)

class _AbstractTimeSeries(EntityType):
    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))
    unit = String(maxsize=64,
                  description=_('the unit in which the TimeSeries data are expressed'))

    data = Bytes(required=True,
                 description = _('Timeseries data'))

class TimeSeries(_AbstractTimeSeries):
    """Periodic Timeseries, defined with a start date and a fixed
    granularity"""
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



class NonPeriodicTimeSeries(_AbstractTimeSeries):
    """Non Periodic Time Series"""
    granularity = String(override=True, internationalizable=True,
                         vocabulary = [_('time_vector')], default='time_vector')

    timestamps = Bytes(required=False,
                       description = _('the array of timestamps. Mandatory but read from the same source as data'))


class ExcelPreferences(EntityType):
    # thousands: input only
    thousands_separator = String(maxsize=1, default=u'')
    decimal_separator = String(required=True, maxsize=1, default=u'.')
    csv_separator = String(required=True, maxsize=1, default=u';')

class format_preferences(RelationDefinition):
    subject = 'CWUser'
    object = 'ExcelPreferences'
    composite = 'subject'
    cardinality = '?1'
