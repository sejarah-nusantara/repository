from sqlalchemy import *
from migrate import *


pre_meta = MetaData()
post_meta = MetaData()
ead_file = Table('ead_file', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String(length=100), nullable=False),
    Column('file', LargeBinary),
)

log_action = Table('log_action', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user', Unicode(length=30)),
    Column('date', DateTime),
)

log_object = Table('log_object', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('log_action_id', Integer),
    Column('object_id', Integer),
    Column('object_type', String(length=30)),
    Column('message', Unicode(length=255)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].create()
    post_meta.tables['log_action'].create()
    post_meta.tables['log_object'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['ead_file'].drop()
    post_meta.tables['log_action'].drop()
    post_meta.tables['log_object'].drop()
