
from cubicweb.devtools.testlib import CubicWebTC
from cubicweb import ValidationError
from logilab.common.testlib import unittest_main

class ExcelPreferencesTC(CubicWebTC):
    def test_validation_hooks(self):
        req = self.request()
        try:
            prefs = req.create_entity('ExcelPreferences', csv_separator=u',', decimal_separator=u',')
            self.fail('should have ValidationError')
        except ValidationError, exc:
            self.assertListEqual(exc.errors.keys(), ['csv_separator'])

    def test_user_owned(self):
        req = self.request()
        user = self.create_user(req, 'toto', commit=False)
        self.commit()
        self.failUnless('toto' in [u.login for u in user.format_preferences[0].owned_by])


if __name__ == '__main__':
    unittest_main()
