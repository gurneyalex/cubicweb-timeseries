
from cubicweb.devtools.testlib import CubicWebTC
from cubicweb import ValidationError
from logilab.common.testlib import unittest_main

class ExcelPreferencesTC(CubicWebTC):
    def test_validation_hooks(self):
        with self.admin_access.web_request() as req:
            try:
                prefs = req.create_entity('ExcelPreferences', csv_separator=u',', decimal_separator=u',')
                self.fail('should have ValidationError')
            except ValidationError, exc:
                self.assertListEqual(exc.errors.keys(), ['csv_separator'])

    def test_everyone(self):
        with self.admin_access.web_request() as req:
            user = self.create_user(req, 'toto', commit=False)
            req.cnx.commit()
            self.assertEqual(req.execute('CWUser U WHERE U format_preferences P').rowcount, 3)
            self.assertEqual(req.execute('CWUser U WHERE NOT U format_preferences P').rowcount, 0)

    def test_user_owned(self):
        with self.admin_access.web_request() as req:
            user = self.create_user(req, 'toto', commit=False)
            req.cnx.commit()
            self.failUnless('toto' in [u.login for u in user.format_preferences[0].owned_by])


if __name__ == '__main__':
    unittest_main()
