from sqlalchemy import *
from migrate import *


pre_meta = MetaData()
post_meta = MetaData()


def upgrade(migrate_engine):
    "Update archives sequence"
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
#     migrate_engine.execute('alter table scan add constraint "unique_sequenceNumber" UNIQUE (archive_id, "archiveFile", "sequenceNumber")')
    


def downgrade(migrate_engine):
    "No point degrading the db. Do nothing"
    migrate_engine.execute('alter table scan drop constraint "unique_sequenceNumber"')
