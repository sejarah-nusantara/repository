""" Setup file.
"""
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

requires = [
    'cornice',
]

packages = [
    'magic',
    'restrepo',
    'restrepo.indexes',
    'restrepo.browser',
    'restrepo.pagebrowser',
    'restrepo.db',
    'restrepo.models',
    'restrepo.tests',
    'restrepo.browser.admin',
]


setup(
    name='restrepo',
    version=0.9,
    description="",
    long_description=README,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"
    ],
    keywords="web services",
    author='Jelle Gerbrandy, Silvio Tomatis',
    author_email="jelle@gerbrandy.com, silviot@gmail.com",
    url="http://www.gerbrandy.com",
    packages=packages,
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'pyramid',
        'pyramid_mako',
        'pyramid_chameleon',
        'cornice',
        'PasteScript',
        'sqlalchemy',
        'psycopg2',
        'pyramid_tm',
        'zope.sqlalchemy',
        'colander',
        'lxml',
        'pytz',
        'python-dateutil',
        'sqlalchemy-migrate',
        'Pillow',
        'mysolr',
        'pyramid_ipauth',
    ],
    tests_require=requires,
    test_suite="restrepo",
    entry_points="""\
    [paste.app_factory]
    main = restrepo:main
    """,
)
