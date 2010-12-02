# the timeseries views ...

from cubicweb.web import uicfg

uicfg.autoform_section.tag_subject_of(('CWUser', 'format_preferences', '*'), 'main', 'hidden')


reledit_ctrl = uicfg.reledit_ctrl
reledit_ctrl.tag_attribute(('TimeSeries', 'start_date'), {'reload': True})
reledit_ctrl.tag_attribute(('TimeSeries', 'granularity'), {'reload': True})
