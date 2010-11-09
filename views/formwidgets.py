"""cube-specific forms/views/actions/components

:organization: Logilab
:copyright: 2001-2010 LOGILAB S.A. (Paris, FRANCE), license is LGPL v2.
:contact: http://www.logilab.fr/ -- mailto:contact@logilab.fr
:license: GNU Lesser General Public License, v2.1 - http://www.gnu.org/licenses
"""
from __future__ import with_statement, division
import numpy

from cubicweb import Binary, ValidationError

from cubicweb.web import uicfg
from cubicweb.web import formwidgets as fw, formfields as ff

_ = unicode

# XXX hack to work around https://www.cubicweb.org/ticket/1381203

class DataFileField(ff.FileField):
    """ FileField sucks, teach it good the manners """

    def _process_form_value(self, form):
        widget = self.get_widget(form)
        value = widget.process_field_data(form, self)
        return self._ensure_correctly_typed(form, value)

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
    if kwargs.get('name') == 'data':
        cls = DataFileField
    return ff.StringField.__new__(cls, **kwargs)
ff.FileField.__new__ = staticmethod(__new__)

# /hack

def interpret_constant(entity, str_value):
    try:
        return entity.python_value(str_value)
    except (ValueError, TypeError):
        _ = entity._cw._
        raise ValidationError(entity.eid, {'data': _('accepted type: %s') % _(entity.data_type)})

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

    def _render(self, form, field, renderer):
        """ provide two input widgets
        the switch will be made in js-land where the shadows^W
        the live value of the granularity will be used
        to present the appropriate widget
        """
        formid = form.domid
        eid = form.edited_entity.eid
        data_fileinput_domid = self.field_id_tmpl % ('granularity', '', eid)
        form._cw.add_onload("init_data_widget('%s', '%s', '%s')" %
                            (self.field_id_tmpl % ('granularity', '', eid),
                             self.field_id_tmpl % ('data', '-non-constant', eid),
                             self.field_id_tmpl % ('data', '-constant', eid)))
        nonconstwidget = self.VariableInputClass(suffix='-non-constant')
        constwidget = self.ConstantInputClass(suffix='-constant')
        return '<div id="%s">%s\n%s</div>' % (field.dom_id(form),
                                              constwidget.render(form, field, renderer),
                                              nonconstwidget.render(form, field, renderer))

    def process_field_data(self, form, field):
        value = super(DataWidget, self).process_field_data(form, field)
        req = form._cw
        granularity = req.form.get('granularity-subject:%s' % form.edited_entity.eid)
        constant_value = req.form.get(field.input_name(form, '-constant')).strip() or None
        if granularity == 'constant':
            value = numpy.array([interpret_constant(form.edited_entity, constant_value)])
            return value
        field = ff.FileField(name='data', eidparam=True, required=True, role='subject')
        return field._process_form_value_with_suffix(form, suffix=u'-non-constant')

uicfg.autoform_field_kwargs.tag_subject_of(('TimeSeries', 'data', '*'),
                                           {'widget': DataWidget})
