add_entity_type('ExcelPreferences')

for user in rql('CWUser U').entities():
    prefs = create_entity('ExcelPreferences')
    user.set_relations(format_preferences=prefs)
