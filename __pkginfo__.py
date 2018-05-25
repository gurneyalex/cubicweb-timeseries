# pylint: disable=W0622
"""cubicweb-timeseries application packaging information"""

from os import listdir as _listdir
from os.path import join, isdir
from glob import glob


modname = 'timeseries'
distname = 'cubicweb-timeseries'

numversion = (1, 5, 0)
version = '.'.join(str(num) for num in numversion)

license = 'LCL'
description = 'timeseries component for the CubicWeb framework'
author = 'LOGILAB S.A. (Paris, FRANCE)'
author_email = 'contact@logilab.fr'
web = 'http://www.cubicweb.org/project/%s' % distname

__depends__ = {
    'cubicweb': '>= 3.16.0',
    'cwtags': None,
    'numpy': None,
}

classifiers = [
    'Environment :: Web Environment',
    'Framework :: CubicWeb',
    'Programming Language :: Python',
    'Programming Language :: JavaScript',
]

THIS_CUBE_DIR = join('share', 'cubicweb', 'cubes', modname)


def listdir(dirpath):
    return [join(dirpath, fname) for fname in _listdir(dirpath)
            if fname[0] != '.' and not fname.endswith('.pyc') and
            not fname.endswith('~') and
            not isdir(join(dirpath, fname))]

data_files = [
    # common files
    [THIS_CUBE_DIR, [fname for fname in glob('*.py') if fname != 'setup.py']],
]
# check for possible extended cube layout
for dname in ('entities', 'views', 'sobjects', 'hooks', 'schema', 'data',
              'wdoc', 'i18n', 'migration'):
    if isdir(dname):
        data_files.append([join(THIS_CUBE_DIR, dname), listdir(dname)])
# Note: here, you'll need to add subdirectories if you want
# them to be included in the debian package
