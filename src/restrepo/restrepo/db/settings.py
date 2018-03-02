# - coding: utf-8 -
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


"""
The layout of scan images on the filesystem is specified in this file.
It looks like this:
restrepo/files
└── original_scans
    └── 0-1000
        └── 1
"""

from sqlalchemy import Table, Column, String
from restrepo.db import metadata
from sqlalchemy.orm import mapper

settings = Table('settings', metadata,
    Column('key', String, primary_key=True),
    Column('value', String, index=True),
)


class Settings(object):
    pass


mapper(Settings, settings)
