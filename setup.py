#!/usr/bin/env python
from setuptools import setup
#from distutils.extension import Extension
#from Cython.Distutils import build_ext

#ext_modules = [Extension("cmwlib", ["cmwlib.pyx"])]
#ext_modules = [Extension("cedgecache", ["cedgecache.pyx"])]

setup(
    name="wiki-network",
    description='Wikipedia Social Network Analysis',
    version="0.1",
    install_requires=('lxml', 'celery', 'django-celery', 'django_evolution',
                      'django', 'django_extensions', 'wirebin', 'nltk',
                      'sqlalchemy', 'nose==1.0.0', 'nose-exclude', 'pyyaml',
                      'simplejson', 'pygeoip', 'diff-match-patch',
                      'python-igraph==0.5.3', 'numpy', 'matplotlib',
                      'BeautifulSoup'),
    #cmdclass = {'build_ext': build_ext},
    #ext_modules = ext_modules
)
