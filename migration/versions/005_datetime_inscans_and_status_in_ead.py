from sqlalchemy import *
from migrate import *


pre_meta = MetaData()
post_meta = MetaData()
ead_file = Table('ead_file', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=100), nullable=False),
    Column('status', Integer, default=ColumnDefault(1)),
)

scan = Table('scan', post_meta,
    Column('number', Integer, primary_key=True, nullable=False),
    Column('archive_id', Integer),
    Column('archiveFile', Unicode(length=255)),
    Column('sequenceNumber', Integer),
    Column('json_data', Unicode),
    Column('status', Integer, default=ColumnDefault(1)),
    Column('date', DateTime),
    Column('timeFrameFrom', Date),
    Column('timeFrameTo', Date),
    Column('transcriptionDate', Date),
    Column('translationENDate', Date),
    Column('translationIDDate', Date),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].columns['status'].create(table=ead_file)
    post_meta.tables['scan'].columns['date'].create()
    post_meta.tables['scan'].columns['status'].create(table=scan)
    post_meta.tables['scan'].columns['timeFrameFrom'].create()
    post_meta.tables['scan'].columns['timeFrameTo'].create()
    post_meta.tables['scan'].columns['transcriptionDate'].create()
    post_meta.tables['scan'].columns['translationENDate'].create()
    post_meta.tables['scan'].columns['translationIDDate'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].columns['status'].drop()
    post_meta.tables['scan'].columns['date'].drop()
    post_meta.tables['scan'].columns['status'].drop()
    post_meta.tables['scan'].columns['timeFrameFrom'].drop()
    post_meta.tables['scan'].columns['timeFrameTo'].drop()
    post_meta.tables['scan'].columns['transcriptionDate'].drop()
    post_meta.tables['scan'].columns['translationENDate'].drop()
    post_meta.tables['scan'].columns['translationIDDate'].drop()
