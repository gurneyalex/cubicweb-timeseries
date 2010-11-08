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

class TimeSeries(EntityType):
    data_type = String(required=True,
                       vocabulary = [_('Float'), _('Integer'), _('Boolean')],
                       default = _('Float'))
    unit = String(maxsize=64)
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

