# postcreate script. You could setup site properties or a workflow here for example
"""

:organization: Logilab
:copyright: 2001-2009 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""

# Example of site property change
#set_property('ui.site-title', "<sitename>")

from cubicweb import __pkginfo__ as cwinfo

# cw 3.15 runs hooks on postcreate, don't do this twice
# http://www.cubicweb.org/ticket/1417110
if cwinfo.numversion < (3, 15, 0):
    for user in rql('CWUser U').entities():
        prefs = create_entity('ExcelPreferences')
        user.set_relations(format_preferences=prefs)
