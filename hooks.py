from cubicweb.server import hooksmanager

class TimeSeriesDataReadHook(hooksmanager.Hook):

    accepts = ('TimeSeries',)
    events = ('before_update_entity', 'before_add_entity')

    def call(self, session, entity):
        if 'data' in entity.edited_attributes:
            entity.grok_data()


