from sqlalchemy import sql, Column, Table, Integer, String, Unicode, MetaData
from sqlalchemy.types import INT

pre_meta = MetaData()
post_meta = MetaData()

log_object = Table('log_object', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('log_action_id', Integer),
    Column('object_id', String),
    Column('object_type', String(length=30)),
    Column('message', Unicode(length=255)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    object_id_tmp = log_object.c.object_id
    log_object.c.object_id.alter(name='object_id_tmp')
    Column('object_id', String).create(log_object)
    query = log_object.update(None, {'object_id': object_id_tmp})
    migrate_engine.connect().execute(query)
    object_id_tmp.drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    object_id_tmp = log_object.c.object_id
    log_object.c.object_id.alter(name='object_id_tmp')
    Column('object_id', Integer).create(log_object)
    newvalue = sql.expression.cast(object_id_tmp, INT)
    query = log_object.update(None, {'object_id': newvalue})
    migrate_engine.connect().execute(query)
    object_id_tmp.drop()
