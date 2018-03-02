
import json
from restrepo.utils import datetime_to_string_zulu
from restrepo.db.solr import solr_escape


def search_components(context, **kwargs):
    """
    search for components in the solr index

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
        order_by
        parent
        show_in_tree
        language
        xpath
        with_facets
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
        'is_archiveFile',
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

    order_by = kwargs.get('order_by', 'sequenceNumber asc')
    query['sort'] = order_by

    # get the documents from the index
    response = context.solr_eadcomponent.search(**query)
    results = response.documents

    for result in results:
        result['breadcrumbs'] = json.loads(result['breadcrumbs'])
    if query.get('hl'):
        # incluce highlighted phrases in the results
        for component in results:
            component_id = 'eadcomponent=%s' % component['eadcomponent_id']
            component['snippet'] = response.highlighting[component_id].get('search_source', '')

    # compute totals ans such
    total_results = response.total_results
    start = response.start
    end = start + len(results)

    return {
        'results': results,
        'query_used': query_used,
        'total_results': total_results,
        'start': start,
        'end': end,
        'facets': with_facets and response.facets['facet_fields'] or {},
    }


def get_tree(context, ead_id, prune_tree=True):
    """
    search for components in the given ead file, and construct a tree representation

    if prune_tree is true, then we will return a pruned tree
        (i.e. pruning lots of leaf nodes)
    """
    if prune_tree:
        show_in_tree = True
    else:
        show_in_tree = None
    results = search_components(
        context=context,
        ead_id=ead_id,
        limit=100000,
        show_in_tree=show_in_tree,
        )['results']

    # create a lookup dictionary to quickly find children of a component
    lookup_dict = {}
    for c in results:
        parent = c.get('parent', None)
        lookup_dict[parent] = lookup_dict.get(parent, []) + [c]

    def get_children(component):
        try:
            return lookup_dict[component['eadcomponent_id']]
        except KeyError:
            return []

    def to_json(component):
        return {
            'title': component['title'],
            'xpath': component['xpath'],
            'children': [to_json(c) for c in get_children(component)],
        }

    results = [to_json(c) for c in results if c.get('parent') is None]
    return results
