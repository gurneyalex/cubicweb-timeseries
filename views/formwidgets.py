"""cube-specific forms/views/actions/components

:organization: Logilab
:copyright: 2010-2014 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import division

import numpy

from cubicweb import Binary, ValidationError, tags
from cubicweb.web.views import uicfg
from cubicweb.web import formwidgets as fw, formfields as ff

_ = unicode

# XXX hack to work around https://www.cubicweb.org/ticket/1381203

class DataFileField(ff.FileField):
    """ FileField sucks, teach it good the manners """

    def _process_form_value(self, form):
        widget = self.get_widget(form)
        value = widget.process_field_data(form, self)
        return self._ensure_correctly_typed(form, value)

    def _ensure_correctly_typed(self, form, value):
        """ numpy.ndarray => that was a constant ts _with_ a value
        but we must work around bool(numpy.array([0])) == False
        fooling the default implementation
        """
        if isinstance(value, numpy.ndarray):
            return value
        return super(DataFileField, self)._ensure_correctly_typed(form, value)

    def _process_form_value_with_suffix(self, form, suffix=u''):
        """ add suffix parameter & use it """
        posted = form._cw.form
        if self.input_name(form, u'__detach') in posted:
            # drop current file value on explictily asked to detach
            return None
        try:
            value = posted[self.input_name(form, suffix)]
        except KeyError:
            # raise UnmodifiedField instead of returning None, since the later
            # will try to remove already attached file if any
            raise ff.UnmodifiedField()
        # value is a 2-uple (filename, stream)
        try:
            filename, stream = value
        except ValueError:
            raise ff.UnmodifiedField()
        # XXX avoid in memory loading of posted files. Requires Binary handling changes...
        value = Binary(stream.read())
        if not value.getvalue(): # usually an unexistant file
            value = None
        else:
            # set filename on the Binary instance, may be used later in hooks
            value.filename = ff.normalize_filename(filename)
        return value

def __new__(cls, *args, **kwargs):
    """depending on the attribute name we dispatch
    to DataFileField class
    """
    label = kwargs.get('label', ('', ''))
    if label[1] == 'data' and label[0].endswith('TimeSeries'):
        cls = DataFileField
    return ff.StringField.__new__(cls)
ff.FileField.__new__ = staticmethod(__new__)

# /hack

def interpret_constant(entity, str_value):
    _ = entity._cw._
    if not str_value:
        raise ValidationError(entity.eid, {'data': _('required field')})
    try:
        return entity.output_value(str_value)
    except (ValueError, TypeError):
        raise ValidationError(entity.eid, {'data': _('accepted type: %s') % _(entity.data_type)})
    except KeyError, k:
        # this can happen at creation time if data_type has not been provided
        # e.g.: data_type is automatically handled in a hook to be executed later
        # (yes, there are use case/applications that want to do this)
        # here we might also look into the form and extract the given
        # data_type value; for now, let's be dumb
        assert entity.data_type is None, 'failed with data_type %s' % entity.data_type
        return float(str_value)

class ConstantDataInput(fw.TextInput):

    def typed_value(self, form, field):
        entity = form.edited_entity
        granularity = entity.granularity
        if granularity != 'constant':
            return ''
        return entity.array[0]

class DataWidget(fw.Input):
    """ depending on granularity being constant,
    either show/process a simple input field or a file field
    """
    needs_js = fw.Input.needs_js + ('cubes.timeseries.js',)
    field_id_tmpl = '%s-subject%s:%s' # (field name, suffix, eid)

    # let's keep this open for easy subclassing
    VariableInputClass = fw.FileInput
    ConstantInputClass = ConstantDataInput

    def _render_export_url(self, form):
        out = []
        w = out.append
        if form.edited_entity and isinstance(form.edited_entity.eid, int):
            url = form.edited_entity.absolute_url(vid='tsxlexport')
            # button triggers form validation
            w(tags.span(tags.a(form._cw._('[export]'), href=url), klass='tsexport',
                        escapecontent=False))
        return ''.join(unicode(x) for x in out)

    def _render(self, form, field, renderer):
        """ provide two input widgets
        the switch will be made in js-land where the shadows^W
        the live value of the granularity will be used
        to present the appropriate widget
        """
        eid = form.edited_entity.eid
        form._cw.add_onload("init_data_widget('%s', '%s', '%s')" %
                            (self.field_id_tmpl % ('granularity', '', eid),
                             self.field_id_tmpl % ('data', '-non-constant', eid),
                             self.field_id_tmpl % ('data', '-constant', eid)))
        nonconstwidget = self.VariableInputClass(suffix='-non-constant')
        constwidget = self.ConstantInputClass(suffix='-constant')
        export_url = self._render_export_url(form)
        return '<div id="%s">%s\n%s</div>' % (field.dom_id(form),
                                              constwidget.render(form, field, renderer),
                                              nonconstwidget.render(form, field, renderer) + export_url)

    def process_field_data(self, form, field):
        value = super(DataWidget, self).process_field_data(form, field)
        req = form._cw
        granularity = req.form.get('granularity-subject:%s' % form.edited_entity.eid)
        constant_value = req.form.get(field.input_name(form, '-constant')).strip() or None
        if granularity == 'constant':
            value = numpy.array([interpret_constant(form.edited_entity, constant_value)])
            return value
        field = DataFileField(name='data', eidparam=True, required=True, role='subject')
        return field._process_form_value_with_suffix(form, suffix=u'-non-constant')

uicfg.autoform_field_kwargs.tag_subject_of(('TimeSeries', 'data', '*'),
                                           {'widget': DataWidget})
uicfg.autoform_field_kwargs.tag_subject_of(('NonPeriodicTimeSeries', 'data', '*'),
                                           {'widget': DataWidget})
