from __future__ import with_statement
import nose

import os
import os.path as osp
import sys
import shutil
import subprocess
import re

from distutils.core import setup
from distutils.core import Command

PYTHON_SCRIPT_DIR = osp.join(osp.dirname(sys.executable), 'Scripts')

REPORT_PYLINT = 'pylint_report.txt'
REPORT_COVERAGE = 'coverage_report.txt'
REPORT_DOC = 'epydoc_report.txt'

############ SETUP INPUT ############
packages_list = ['.',
                  ]

class build_doc(Command):
    description = 'Builds the documentation'
    user_options = [
        ('force', None,
         "force regeneration even if no reStructuredText files have changed"),
        ('without-apidocs', None,
         "whether to skip the generation of API documentation"),
    ]
    boolean_options = ['force', 'without-apidocs']

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        epydoc_conf = osp.join('epydoc.ini')
        epydoc_script = osp.join(PYTHON_SCRIPT_DIR, 'epydoc.py')

        args = ['python',
                 epydoc_script,
                '--config=%s' % epydoc_conf,
                '--no-private', # epydoc bug, not read from config
                '--simple-term',
                '--verbose', ]

        proc = subprocess.Popen(args = args,
                                stdout = subprocess.PIPE,
                                stdin = subprocess.PIPE,
                                stderr = subprocess.PIPE)

        output, errors = proc.communicate()

        with open(REPORT_DOC, 'w') as report:
            report.writelines([line.replace('\r', '') for line in output])

class test_command(Command):
    user_options = [ ]
    description = 'Runs Nose tests'

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):

       nose_script = osp.join(PYTHON_SCRIPT_DIR, 'pytest.bat')

       args = [nose_script,
               '-v']

       proc = subprocess.Popen(args = args,
                               cwd = self._dir,
                               stdout = subprocess.PIPE,
                               stdin = subprocess.PIPE,
                               stderr = subprocess.PIPE)

       output, errors = proc.communicate()

       with open(REPORT_COVERAGE, 'w') as report:
           report.writelines([line.replace('\r', '') for line in errors])

       pytest_xunit_report(REPORT_COVERAGE)
       
def pytest_xunit_report(test_output):

    test_pattern = re.compile('^(test_.*) \((.*)\) \.{3} (ok|fail|error)$')

    results = []

    counts = dict.fromkeys(['ok', 'fail', 'error', 'total', 'skipped'], 0)

    with open(test_output, 'r') as report:

        for row in report:

            match = test_pattern.match(row)

            if match:

                test_name, test_class, result = match.groups()

                result = result.lower()

                counts[result] += 1
                counts['total'] += 1

                stats = {'cls':test_class,
                         'name' : test_name,
                         'taken':0,
                         'errtype':test_class,
                         'tb':''}

                if result == 'ok':

                    results.append('<testcase classname="%(cls)s" name="%(name)s" '
                                   'time="%(taken)d" />' % stats)

                elif result == 'fail':

                    results.append('<testcase classname="%(cls)s" name="%(name)s" '
                                   'time="%(taken)d" />'
                                   '<failure type="%(errtype)s">%(tb)s</failure></testcase>' % stats)

                elif result == 'error':

                    results.append('<testcase classname="%(cls)s" name="%(name)s" '
                                   'time="%(taken)d" />'
                                   '<error type="%(errtype)s">%(tb)s</failure></testcase>' % stats)

    with open('nosetests.xml', 'w') as xml_report:

        xml_report.write('<?xml version="1.0" encoding="utf-8"?>'
                         '<testsuite name="nosetests" tests="%(total)d" '
                         'errors="%(error)d" failures="%(fail)d" '
                         'skip="%(skipped)d">' % counts)

        xml_report.write(''.join(results))

        xml_report.write('</testsuite>')

class clean_command(Command):
    user_options = []
    description = 'Cleans the output folders'

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        doc_path = osp.join(self._dir, 'html_doc')
        if osp.exists(doc_path):
            shutil.rmtree(path = doc_path)

        # remove reports
        for report in [REPORT_COVERAGE, REPORT_DOC, REPORT_PYLINT]:
            report_path = osp.join(self._dir, report)
            if osp.exists(report_path):
                os.remove(report_path)

class pylint_command(Command):
    user_options = []
    description = 'Performs static code analysis'

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):

        args = [osp.join(PYTHON_SCRIPT_DIR, 'pylint.bat'),
                 '-f',
                 'parseable',
                 '--output-format=parseable',
                 '--ignore-comments=y',
                 '--ignore=tests',
                 '--min-similarity-lines=4',
                 '--disable-msg=C0103',
                 '--disable-msg=C0301',
                 ','.join(packages_list)]

        proc = subprocess.Popen(args = args,
                        cwd = self._dir,
                        stdout = subprocess.PIPE,
                        stdin = subprocess.PIPE,
                        stderr = subprocess.PIPE)

        output, errors = proc.communicate()

        with open(REPORT_PYLINT, 'w') as report:
            report.writelines([line.replace('\r', '') for line in output])

setup(name = 'MAS_Foundations',
      version = '0.1',
      description = 'Common modules and packages shared by M&AS python projects',
      author = 'M&AS',
      author_email = 'Patrick.Watteyne@gdf-suez.com',
      packages = packages_list,
      cmdclass = {'doc' : build_doc,
                  'test': test_command,
                  'pylint' : pylint_command,
                  'clean' : clean_command}
     )
