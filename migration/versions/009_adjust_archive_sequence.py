from sqlalchemy import *
from migrate import *


pre_meta = MetaData()
post_meta = MetaData()


def upgrade(migrate_engine):
    "Update archives sequence"
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    current_max = migrate_engine.execute("SELECT max(id) from archive").fetchone()[0]
    new_max = current_max + 1
    migrate_engine.execute("ALTER SEQUENCE archive_id_seq RESTART WITH %i" % new_max)


def downgrade(migrate_engine):
    "No point degrading the db. Do nothing"
