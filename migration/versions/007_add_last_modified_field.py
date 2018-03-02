from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
ead_file = Table('ead_file', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=100), nullable=False),
    Column('status', Integer, default=ColumnDefault(1)),
    Column('last_modified', DateTime(timezone=True)),
)

scan = Table('scan', post_meta,
    Column('number', Integer, primary_key=True, nullable=False),
    Column('archive_id', Integer),
    Column('archiveFile', Unicode(length=255)),
    Column('sequenceNumber', Integer),
    Column('json_data', String),
    Column('status', Integer, default=ColumnDefault(1)),
    Column('date', DateTime(timezone=True)),
    Column('timeFrameFrom', Date),
    Column('timeFrameTo', Date),
    Column('transcriptionDate', Date),
    Column('translationENDate', Date),
    Column('translationIDDate', Date),
    Column('last_modified', DateTime(timezone=True)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].columns['last_modified'].create()
    post_meta.tables['scan'].columns['last_modified'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].columns['last_modified'].drop()
    post_meta.tables['scan'].columns['last_modified'].drop()

