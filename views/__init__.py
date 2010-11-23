# the timeseries views ...

from cubicweb.web import uicfg

uicfg.autoform_section.tag_subject_of(('CWUser', 'format_preferences', '*'), 'main', 'hidden')
