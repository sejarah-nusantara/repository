import io
import ConfigParser
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from restrepo.db.solr import Solr
from restrepo.db import SolrWrapper
from restrepo.indexes import reindex_all, reindex_scans, reindex_archivefiles, reindex_ead_files, reindex_components


def extract_urls(text):
    """
    >>> from textwrap import dedent
    >>> extract_urls('''
    ... [app:someappname]
    ... sqlalchemy.url = postgresql+psycopg2:///some_dbname
    ... solr.url = http://somehost:5002/solr/
    ... ''')
    ('postgresql+psycopg2:///some_dbname', 'http://somehost:5002/solr/')
    """
    config = ConfigParser.RawConfigParser()
    config.readfp(io.BytesIO(text))
    sqlalchemy_url = ''
    solr_url = ''
    for section in config.sections():
        for option in config.options(section):
            if option == 'sqlalchemy.url':
                sqlalchemy_url = config.get(section, option)
            if option == 'solr.url':
                solr_url = config.get(section, option)
    if not sqlalchemy_url or not solr_url:
        raise ValueError("sqlalchemy.url or solr.url missing")
    return sqlalchemy_url, solr_url


def reindex_all_command(delete=True):
    context = get_context()
    reindex_all(context, delete=delete)


def get_context():
    inifile = sys.argv[1]
    inifile_contents = open(inifile).read()
    sqlalchemy_url, solr_url = extract_urls(inifile_contents)
    context = Context(sqlalchemy_url, solr_url)
    return context


class Context(object):
    """A context for reindex_all"""
    def __init__(self, sqlalchemy_url, solr_url):
        self.sqlalchemy_url = sqlalchemy_url
        engine = create_engine(sqlalchemy_url)
        self.db = sessionmaker(bind=engine)()
        self.solr = Solr(solr_url + 'entity')
        self.solr_ead = SolrWrapper(self.solr, 'ead', 'ead_id')
        self.solr_eadcomponent = SolrWrapper(self.solr, 'eadcomponent', 'eadcomponent_id')
        self.solr_scan = SolrWrapper(self.solr, 'scan', 'number')
        self.solr_archivefile = SolrWrapper(self.solr, 'archivefile', 'archivefile_id')


if __name__ == '__main__':
    delete = True
    if len(sys.argv) > 3:
        delete = sys.argv[3]
        if delete not in [True, 'True', 1, '1']:
            delete = False
    if len(sys.argv) > 2:
        context = get_context()
        if sys.argv[2] == 'scans':
            reindex_scans(context, delete=delete)
        elif sys.argv[2] == 'archivefiles':
            reindex_archivefiles(context, delete=delete)
        elif sys.argv[2] == 'eadfiles':
            reindex_ead_files(context, delete=delete)
        elif sys.argv[2] == 'components':
            reindex_components(context, delete=delete)
        else:
            raise "unknown second argument %s" % sys.argv[2]
    else:
        reindex_all_command(delete=delete)
