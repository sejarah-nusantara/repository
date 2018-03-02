import re
import types
from mysolr import Solr as Solr_original


class Solr(Solr_original):
    def __init__(
        self,
        base_url='http://localhost:8080/solr/',
        auth=None,
        version=None,
    ):
        "Explicitly set version to 4 to save an http call"
        super(Solr, self).__init__(base_url, auth, version=4)

    def search(self, *args, **kwargs):
        result = super(Solr, self).search(*args, **kwargs)
        if result.status != 200:
            raise SolrException(result.raw_content)
        return result

    def update(self, *args, **kwargs):
        kwargs['commit'] = kwargs.setdefault('commit', False)
        result = super(Solr, self).update(*args, **kwargs)
        if result.status != 200:
            raise SolrException(result.raw_content)
        return result

    def delete_by_key(self, *args, **kwargs):
        kwargs['commit'] = kwargs.setdefault('commit', False)
        result = super(Solr, self).delete_by_key(*args, **kwargs)
        if result.status != 200:
            raise SolrException(result.raw_content)
        return result

    def delete_by_query(self, *args, **kwargs):
        kwargs['commit'] = kwargs.setdefault('commit', False)
        result = super(Solr, self).delete_by_query(*args, **kwargs)
        if result.status != 200:
            raise SolrException(result.raw_content)
        return result


class SolrWrapper(object):
    "Wrap a Solr object. Intercepting all queries and add a fixed stanza."
    def __init__(self, solr, entity_type, idfield):
        self._entity_type = entity_type
        self._real_solr = solr
        self._idfield = idfield

    def search(self, resource='select', **kwa):
        condition = "entity_type:%s" % self._entity_type
        if 'fq' not in kwa:
            kwa['fq'] = condition
        else:
            kwa['fq'].append(condition)
        return self._real_solr.search(resource=resource, **kwa)

    def update(self, documents, **kwargs):
        "Insert the proper type and id inside each document"
        for document in documents:
            document['entity_type'] = self._entity_type
            document['id'] = '%s=%s' % (
                document['entity_type'], str(document[self._idfield]))
        return self._real_solr.update(documents=documents, **kwargs)

    def delete_by_query(self, query, **kwargs):
        new_query = "entity_type:%s AND ( %s )" % (self._entity_type, query)
        return self._real_solr.delete_by_query(query=new_query, **kwargs)

    def delete_by_key(self, identifier, **kwargs):
        real_identifier = "%s=%s" % (self._entity_type, identifier)
        return self._real_solr.delete_by_key(real_identifier, **kwargs)

    def commit(self, *args, **kwargs):
        return self._real_solr.commit(*args, **kwargs)


class SolrException(Exception):
    "Error in communication with solr"


# Code taken from
# http://fragmentsofcode.wordpress.com/2010/03/10/escape-special-characters-for-solrlucene-query/
# Solr/Lucene special characters: + - ! ( ) { } [ ] ^ " ~ * ? : \
# There are also operators && and ||, but we're just going to escape
# the individual ampersand and pipe chars.
# Also, we're not going to escape backslashes!
# http://lucene.apache.org/java/2_9_1/queryparsersyntax.html#Escaping+Special+Characters
ESCAPE_CHARS_RE = re.compile(r'(?<!\\)(?P<char>[ /&|+\-!(){}[\]^"~*?:])')


def solr_escape(value):
    r"""
    Escape un-escaped special characters and return escaped value.

    >>> solr_escape(r'foo+') == r'foo\+'
    True
    >>> solr_escape(r'foo\+') == r'foo\+'
    True
    >>> solr_escape(r'foo\\+') == r'foo\\+'
    True

    Solr 4.0 added regular expression support, which means that '/' is now
    a special character and must be escaped if searching
    for literal forward slash.

    >>> solr_escape(u'a[1]/b') == r'a\[1\]\/b'
    True
    >>> solr_escape(u'a[1]/b') == u'a\\[1\\]\/b'
    True

    We also escape whitespace

    >>> solr_escape(u'a b') == u'a\ b'
    True

    """

    if type(value) not in types.StringTypes:
        value = unicode(value)

    return ESCAPE_CHARS_RE.sub(r'\\\g<char>', value)


def build_equality_query(**kwargs):
    """
    Build a query from keyword parameters
    >>> build_equality_query(foo='bar')
    'foo:bar'
    >>> build_equality_query()
    '*:*'
    """
    pieces = []
    for fieldname, value in kwargs.items():
        if value:
            pieces.append("%s:%s" % (fieldname, solr_escape(value)))
    if pieces:
        return ' AND '.join(pieces)
    else:
        return '*:*'
