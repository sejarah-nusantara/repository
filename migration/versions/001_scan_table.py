from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
scan = Table('scan', post_meta,
    Column('number', Integer, primary_key=True, nullable=False),
    Column('institution', String),
    Column('fonds', String),
    Column('archiveFile', String),
    Column('sequenceNumber', Integer),
    Column('json_data', String),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['scan'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['scan'].drop()

