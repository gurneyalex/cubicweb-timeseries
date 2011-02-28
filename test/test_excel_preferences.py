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


if __name__ == '__main__':
    unittest_main()
