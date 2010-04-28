# pylint: disable-msg=W0622
"""cubicweb-timeseries application packaging information"""

modname = 'timeseries'
distname = 'cubicweb-timeseries'

numversion = (0, 8, 4)
version = '.'.join(str(num) for num in numversion)

license = 'LCL'
copyright = '''Copyright (c) 2009-2010 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr -- mailto:contact@logilab.fr'''

author = 'LOGILAB S.A. (Paris, FRANCE)'
author_email = 'contact@logilab.fr'

short_desc = 'timeseries component for the CubicWeb framework'
long_desc = '''\
This cube provides a new datatype for time dependent values, handle the storage
in a RDBMS, various ways of specifying the values, and several default views.
'''

web = 'http://www.cubicweb.org/project/%s' % distname

pyversions = ['2.4', '2.5']


from os import listdir as _listdir
from os.path import join, isdir, exists, dirname
from glob import glob

THIS_CUBE_DIR = join('share', 'cubicweb', 'cubes', modname)

def listdir(dirpath):
    return [join(dirpath, fname) for fname in _listdir(dirpath)
            if fname[0] != '.' and not fname.endswith('.pyc')
            and not fname.endswith('~')
            and not isdir(join(dirpath, fname))]

data_files = [
    # common files
    [THIS_CUBE_DIR, [fname for fname in glob('*.py') if fname != 'setup.py']],
    ]
# check for possible extended cube layout
for dirname in ('entities', 'views', 'sobjects', 'hooks', 'schema', 'data', 'i18n', 'migration'):
    if isdir(dirname):
        data_files.append([join(THIS_CUBE_DIR, dirname), listdir(dirname)])
# Note: here, you'll need to add subdirectories if you want
# them to be included in the debian package


cube_eid = None # <=== FIXME if you need direct bug-subscription
__depends_cubes__ = {}
__depends__ = {'cubicweb': '>= 3.7.4'}
__recommends_cubes__ = {}
# obsolete (will be gone in cw 3.8.0)
__use__ = tuple(__depends_cubes__)
__recommend__ = tuple(__recommends_cubes__)
