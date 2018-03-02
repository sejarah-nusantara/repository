#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#
from restrepo.db import metadata
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from restrepo import pagebrowser
from restrepo.pagebrowser import update

from base import PSQL_URL


class Fixture(object):
    "Placeholder"

fixture = Fixture()


def setUp():
    fixture.engine = create_engine(PSQL_URL, strategy="threadlocal", pool_size=1)
    fixture.Session = sessionmaker(bind=fixture.engine)
    metadata.bind = fixture.engine
    try:
        metadata.bind.connect()
    except OperationalError as error:
        msg = 'Try creating the database with a command such as\n'
        msg += 'sudo su postgres -c "createdb dasa_repository --owner=dasa"'
        raise Exception(unicode(error) + msg)

    metadata.drop_all(fixture.engine)
    metadata.create_all(fixture.engine)

    # it would be more correct to define the constraint in the ddl of sqlalchemy, but i cannot find the right way to do that
    #
#     postgres 8.4 (which is on server) does not eat this
#     fixture.engine.execute('alter table scan add constraint "unique_sequenceNumber" UNIQUE (archive_id, "archiveFile", "sequenceNumber") DEFERRABLE INITIALLY DEFERRED')


def tearDown():
    metadata.drop_all()
    fixture.engine.dispose()
    fixture.engine.close()


def _ping_url(url, params):
    """don't really ping an url in the tests"""
    # this function is redefined in test_pagebrowser_updates
    pass

pagebrowser.update._ping_url = _ping_url
