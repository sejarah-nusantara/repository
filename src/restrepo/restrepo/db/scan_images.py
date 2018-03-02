from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey
from restrepo.db import metadata
from restrepo.db.mixins import DictAble


scan_image = Table('scan_image', metadata,
    Column('id', Integer, primary_key=True),
    Column('scan_number', Integer, ForeignKey('scan.number'), index=True),
    Column('filename', String(255), index=True),
    Column('is_default', Boolean),
)


class ScanImage(DictAble):
    "An image linked to a scan. Can be the default one."
    def __init__(self, **kwdata):
        for k, v in kwdata.items():
            setattr(self, k, v)
