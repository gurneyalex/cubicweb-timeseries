for etype in ('TimeSeriesHandle', 'ExcelTSValue', 'TSConstantBlock', 'TSConstantExceptionBlock',
              'ConstantAndExceptionTSValue', 'BlockConstantTSValue'):
    drop_entity_type(etype)
sync_schema_props_perms()
add_attribute('TimeSeries', 'unit')
