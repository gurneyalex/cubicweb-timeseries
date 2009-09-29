# cube's specific schema
"""

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""

_ = unicode

from yams.buildobjs import EntityType, String, Bytes, Datetime
from yams.constraints import StaticVocabularyConstraint

class TimeSeries(EntityType):
    name = String(required=True,
                  fulltextindexed=True,
                  maxsize=255,
                  unique=True)
    
                  
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
    
    data = Bytes(required=True,
                 description = _('Timeseries data'))
