# postcreate script. You could setup site properties or a workflow here for example
"""
:organization: Logilab
:copyright: 2009-2012 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""

# some (e.g the admin/bootstrap user) may not have it
for user in rql('CWUser U WHERE NOT U format_preferences P').entities():
    prefs = create_entity('ExcelPreferences')
    user.cw_set(format_preferences=prefs)
