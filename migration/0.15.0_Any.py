add_attribute('ExcelPreferences', 'csv_separator')

for user in rql('CWUser U').entities():
    if not user.format_preferences:
        prefs = create_entity('ExcelPreferences')
        user.set_relations(format_preferences=prefs)


