from sqlalchemy import Table, Column, Integer, Unicode, Boolean, String, MetaData
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()

archivefile = Table('archivefile', post_meta,
    Column('number', Integer, primary_key=True),
    Column('archive_id', Integer, index=True),
    Column('archiveFile', Unicode(255), index=True),
    Column('status', Integer),
    Column('json_data', String),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['archivefile'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['archivefile'].drop()
