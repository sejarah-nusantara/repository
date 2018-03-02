#!./bin/python
"This is a command utility to migrate (upgrade) restrepo database"
import ConfigParser
import io
from migrate.versioning.shell import main


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


if __name__ == '__main__':
    inifile = 'restrepo.ini'
    inifile_contents = open(inifile).read()
    sqlalchemy_url, solr_url = extract_urls(inifile_contents)
#     sqlalchemy_url = 'postgresql+psycopg2:///dasa_repository'
    main(url=sqlalchemy_url, debug='False', repository='migration')
