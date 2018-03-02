import json
import re
from restrepo.utils import datetime_to_string_zulu
from restrepo.db.solr import solr_escape
from restrepo.config import status


def search_archivefiles(context, **kwargs):
    """
    possible arguments:
        start
        limit
        date_from
        date_to
        archive
        archive_id
        archiveFile
        country
        contains_text
        ead_id
        findingaid
        institution
        is_archiveFile
        is_component
        parent
        show_in_tree
        language
        xpath
        with_facets : return the argument with facets, default is True
    """
    start = kwargs.get('start', 0)
    limit = kwargs.get('limit', 1000)

    conditions = []
    query_used = {}
    with_facets = kwargs.get('with_facets', True)
    if with_facets:
        query = {
            'facet': 'true',
            'facet.field': ['country', 'language'],
            'start': start,
            'rows': limit,
        }
    else:
        query = {}

    date_from = kwargs.get('date_from')
    date_to = kwargs.get('date_to')
    if date_from:
        date_from = datetime_to_string_zulu(date_from)
    if date_to:
        date_to = datetime_to_string_zulu(date_to)
    if date_from or date_to:
        date_from = date_from or '*'
        date_to = date_to or '*'
        conditions.append('date_from:[* TO %(date_to)s]' % locals())
        conditions.append('date_to:[%(date_from)s TO *]' % locals())

    for k in [
        'archive',
        'archive_id',
        'archiveFile',
        'country',
        'contains_text',
        'ead_id',
        'findingaid',
        'institution',
        'is_component',
        'language',
        'parent',
        'show_in_tree',
        'xpath',
    ]:
        value = kwargs.get(k, None)
        if k == 'is_component' and not value:
            value = None
        if value is not None:
            query_used[k] = value
            value = solr_escape(value)
            value = '"%s"' % value.strip('"')
            if k == 'contains_text':
                value = value.lower()
                conditions.append('search_source:%s' % value)
                # cf. http://wiki.apache.org/solr/HighlightingParameters
                query['hl'] = True
                query['hl.fl'] = 'search_source'
                query['hl.q'] = 'search_source:%s' % value
            else:
                conditions.append('%s:%s' % (k, value))
    query['q'] = ' AND '.join(conditions) if conditions else '*:*'

    response = context.solr_archivefile.search(**query)
    results = response.documents
    for result in results:
        if 'breadcrumbs' in result:
            result['breadcrumbs'] = json.loads(result['breadcrumbs'])
        else:
            result['breadcrumbs'] = []

    total_results = response.total_results
    start = response.start
    end = start + len(results)

    if query.get('hl'):
        # incluce highlighted phrases in the results
        for component in results:
            component_id = 'archivefile=%s' % component['id']
            component['snippet'] = response.highlighting[component_id].get('search_source', '')

    return {
        'results': results,
        'query_used': query_used,
        'total_results': total_results,
        'start': start,
        'end': end,
        'facets': with_facets and response.facets['facet_fields'] or {},
    }


def cast_scan_as_archivefile(context, scandata):
    """'extracts' the archive file information from a scan, suitable for solr indexing

    scan is a dictionary represting a scan"""
    # todo: cleanup code so we don't need to import here
    q = 'archive_id:{archive_id} AND archiveFile:{archiveFile}'.format(
        archive_id=solr_escape(scandata['archive_id']),
        archiveFile=solr_escape(scandata['archiveFile']),
    )
    documents = context.solr_archivefile.search(q=q).documents
    from restrepo.db.archivefile import ArchiveFile
    archivefile = ArchiveFile()
    if documents:
        for k in documents[0]:
            setattr(archivefile, k, documents[0][k])
    else:
        archivefile.archive_id = scandata['archive_id']
        archivefile.archiveFile = scandata['archiveFile']
    return archivefile


def cast_archivefile_as_component(context, archivefile):
    """returns a json dict representing a component -- if one exists -- updated with the archivefile info"""
    # we look for the component in the index (THIS IS POTENTIALLY EXPENSIVE)
    from restrepo.indexes.lists import search_components
    component = search_components(context, archiveFile=archivefile['archiveFile'], archive_id=archivefile['archive_id'])['results']
    if component:
        component = component[0]
        component['breadcrumbs'] = json.dumps(component['breadcrumbs'])
        for k in component:
            if k in archivefile and k not in ['_version_']:
                component[k] = archivefile[k]
        return component


def cast_component_as_archivefile(component):
    """represent information from a component as an archivefile, suitable for solr indexing

    returns: an ArchiveFile instance
    """
    from restrepo.db.archivefile import ArchiveFile
    archivefile = ArchiveFile()
    archivefile.archive_id = component['archive_id']
    archivefile.archiveFile = component['archiveFile']
    archivefile.title = component['title']
    return archivefile


def get_archivefile(request, archive_id, archiveFile):
    """get archivefile from the index"""
    _total_results, archive_files = get_archivefiles(request, archive_id=archive_id, archiveFile=archiveFile)
    if archive_files:
        assert len(archive_files) == 1
        return archive_files[0]


def archivefile_solr_to_json(request, document):
    """these are the data of an archivefile as returned by the server"""
    keys = [
        ('archive_id', None),
        ('status', status.PUBLISHED),
        ('archiveFile', None),
        ('URL', None),
        ('number_of_scans', None),
        ('ead_ids', []),
        ('title', None),  # really it does not make much sense ask for a title - the title might be different dependiung on the EAD file
        ('titles', '{}'),
        ('URL', request.route_url(
            'service_archivefile_item',
            archive_id=document['archive_id'], archiveFile=document['archiveFile'])),
    ]
    result = {}
    for key, default in keys:
        result[key] = document.get(key, default)
    result['id'] = document['archivefile_id']
    if result['titles'].startswith('{'):
        # TODO: This seems a bit exaggerated...
        result['titles'] = eval(result['titles'])

    return result


def get_archivefiles(
    context,
    ead_id=None,
    archive_id=None,
    archivefile_id=None,
    archiveFile=None,
    archiveFiles=[],
    has_scans=None,
    status=None,
    start=0,
    limit=10000,
    sort='sort_field asc',
    ):

    q = ['*:*']

    if ead_id:
        q.append('ead_ids:%s' % solr_escape(ead_id))

    if archive_id:
        archive_id = int(archive_id)
        q.append('archive_id:%s' % solr_escape(archive_id))

    if archivefile_id:
        q.append('archivefile_id:%s' % solr_escape(archivefile_id))

    def archiveFile_escape(s):
        m = re.match('\[(.*?) TO (.*?)\]$', s)
        if m is None:
            return solr_escape(s)
        else:
            archiveFile_from = solr_escape(m.groups()[0])
            archiveFile_to = solr_escape(m.groups()[1])
            return '["{archiveFile_from}" TO "{archiveFile_to}"]'.format(archiveFile_from=archiveFile_from, archiveFile_to=archiveFile_to)

    if archiveFile:
        q.append('archiveFile:%s' % archiveFile_escape(archiveFile))

    if archiveFiles:
        q.append('archiveFile:(%s)' % ' OR '.join(archiveFile_escape(s) for s in archiveFiles))

    if status is not None:
        q.append('status:%s' % status)

    if has_scans is not None:
        if has_scans:
            q.append('number_of_scans:[1 TO *]')
        else:
            q.append('number_of_scans:0')

    q = ' AND '.join(q)

    response = context.solr_archivefile.search(q=q, rows=limit, start=start, sort=sort)

    results = response.documents
    results = [archivefile_solr_to_json(context, x) for x in results]
    total_results = response.total_results

    return total_results, results
