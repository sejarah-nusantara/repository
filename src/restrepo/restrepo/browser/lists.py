# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


""" Lists


"""
from cornice import Service
from restrepo import config
from restrepo.models.lists import ComponentTreeSearchSchema
from restrepo import indexes
from restrepo.utils import set_cors
from restrepo.browser.validation import validate_schema, must_have_ead_id_or_archive_id
from restrepo.browser import validation
from restrepo.indexes.lists import search_components as _search_components
from restrepo.indexes.lists import get_tree as _get_tree
from restrepo.indexes.archivefile import get_archivefiles


service_list_archive_file_ids = Service(
    name='list_archive_file_ids',
    path=config.SERVICE_ARCHIVE_FILE_ID,
    description="List ids of archive files",
)


@service_list_archive_file_ids.get(validators=[must_have_ead_id_or_archive_id], filters=[set_cors])
def list_archive_file_ids_get(request):
    """
    **deprecated -- use the collection at /archivefiles/**

    get the list of ids archiveFiles present in a given EAD file
    or corresponding to a certain archive.

    cf. :ref:`TestLists.test_get_archive_file_ids`

    parameters:
        * **ead_id:**
            an identifier of an EAD file
        * **archive_id:**
            return archiveFiles from EADs that correspond to this archive
        * **has_scans:** if the value of has_scans is True, then return only archiveFile ids
            that have a scan available

    One of these parameters MUST be given.

    If both are given only ead_id is honoured.



    """

    ead_id = request.GET.get('ead_id', None)
    archive_id = request.GET.get('archive_id', None)
    total_results, results = get_archivefiles(request, ead_id=ead_id, archive_id=archive_id)

    def retrocompatibility(result):
        result['id'] = result['archiveFile']
        return result

    results = map(retrocompatibility, results)

    return {
        'results': results,
        'query_used': dict(request.GET),
        'total_results': total_results,
    }


get_component_for_viewer_service = Service(
    name='get_component_for_viewer',
    path=config.SERVICE_GET_COMPONENT_FOR_VIEWER,
    description="Get all information of the component that the viewer needs to visualize it",
    )


@get_component_for_viewer_service.get(
    validators=[validation.get_component_for_viewer_valid_parameters, ],
    filters=[set_cors],
    )
def get_component_for_viewer(request):
    """Get detailed information about this component from the ead file

    parameters:
        * **ead_id**:
        * **xpath**:
        * **archiveFile**:

    An ead_id and an xpath identify a unique component in the EAD file.

    For convenience, it is also possible to search for components by their "archiveFile" property.

    """
    qry = dict(request.validated)
    result = _search_components(context=request, **qry)

    if result['total_results'] == 0:
        return result
    if result['total_results'] != 1:
        # we should have exactly one result
        # TODO: Warn here
        pass
    component = result['results'][0]

    # now get all the children
    if component['is_component'] or component['show_in_tree']:
        children = _search_components(context=request, parent=component['eadcomponent_id'])['results']
        component['children'] = children
        for child in children:
            # we only return the first child, to mark the fact that the child has children
            child['children'] = _search_components(context=request, parent=child['eadcomponent_id'])['results'][:1]

    def cleanup_component(component):
        """remove some info from solr that the client will never need"""
        for k in [
            '_version_',
#             'breadcrumbs',
            # 'archive_id',
            'ead_component_id',
            'id', 'eadcomponent_id',
            'entity_type', 'ead_id', 'institution', 'is_archiveFile',
#             'is_component',
            'language',
            'search_source',
#             'show_in_tree',
            'sequenceNumber',
            ]:
            if k in component:
                del component[k]
        if 'text' in component:
            component['text'] = filter(None, component['text'])
        if 'children' in component:
            for child in component['children']:
                cleanup_component(child)
        return component
    cleanup_component(component)

    return result

service_search_components = Service(
    name='service_search_components',
    path=config.SERVICE_COMPONENTS_COLLECTION,
    description="Search for components in the EAD files",
    )


@service_search_components.get(validators=[
    validation.search_components_valid_parameters,
    validation.xpath_must_have_ead_id,
    ], filters=[set_cors])
def search_components(request):
    """Search for elements in the ead files.

    parameters:
        * **ead_id:**
        %(PARAM_ARCHIVE_ID)s
        * **country:**
            the country of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **institution:**
            the institution of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archive:**
            the archive of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archiveFile:**
             as above
        * **xpath:**
            if given, also ``ead_id`` must be provided
            an xpath within the file identified by ``ead_id``.
            at the moment, only the "canonical" xpath
            (returned by this service) is recognized
            *not currently working*
        * **findingaid:**
        * **language:**
        * **is_archiveFile:** Boolean, default is false. If true, return only 'leaf'
            components - those that correspond to archive files
        * **is_component:** Boolean, default is False.
            If True, return only 'components' (i.e. <c>, <c01>, <c02> ... elements).
            If false, return all elements with a non-empty text (whether components or not)
        * **start:**
            index of the first element returned (used in pagination)
        * **limit:**
            max # of objects to return. Defaults to 1000.
        * **contains_text:**
            a string. Return results containing this string
        * **collapse_leaves:** boolean, default=True
            if this is True, then leaves will not be returned as separate elements.
            *not implemented*
        * **tree_view:** boolean, default=True
            base search results on mapping (if this is true, search results will coi
        * **date_from:**
            a string in ISO-?? format, i.e. of the form YYYY, YYYY-MM or YYYY-MM-DD
            return all components that have a end date later than date_from
        * **date_to:**
            a string in ISO-?? format, i.e. of the form YYYY, YYYY-MM or YYYY-MM-DD
            return all components that have a start date before date_to
        * **order_by:**
            a comma-separated list of column names to sort results on
            *not yet implemented*

    cf. :ref:`TestComponents.test_search_components`

    The function returns component objects with the following fields:
    *(to be done: document the returned values - for now, see the example)*
    """
    # TODO: document the returned values
    # TODO: result should also include the number of scans (higher level = all scans of underlying level)
    # TODO: implement order_by

    qry = dict(request.validated)
    result = _search_components(context=request, **qry)
    for component in result['results']:
        # clean up
        for key in [
            '_version_',
#             'country',
#             'archive',
#             'ead_id',
            'id',
#             'institution',
            'search_source',
            'parent',
            ]:
            if key in component:
                del component[key]
    return result

search_components.__doc__ = search_components.__doc__ % config.__dict__


component_tree_service = Service(
    name='component_tree',
    path=config.SERVICE_COMPONENT_TREE,
    description="Return a tree of components of an EAD file",
    )


def component_tree_valid_parameters(request):
    schema = ComponentTreeSearchSchema()
    data = dict(request.GET)
    validate_schema(schema, data, request)


@component_tree_service.get(validators=[
    component_tree_valid_parameters,
    ],
    filters=[set_cors],
    )
def component_tree(request):
    """Return a tree of elements in an EAD file.

    parameters:
        * **ead_id:** required. The id of an ead file.
        * **prune:** boolean. If false, show all subelements of the tree. Default is true.

    cf. :ref:`TestComponents.test_component_tree`
    """
    ead_id = request.validated['ead_id']
    prune = request.validated['prune']
    results = _get_tree(context=request, ead_id=ead_id, prune_tree=prune)

    return {
        'results': results,
        'query_used': {'ead_id': ead_id},
    }


list_findingaid_service = Service(
    name='list_findingaid_service',
    path=config.SERVICE_FINDINGAID_COLLECTION,
    description="Return list of finding aids in uploaded ead files",
    )


@list_findingaid_service.get(validators=[], filters=set_cors)
def list_finding_aid(request):
    """get the list of ids findingaid values present in the database

    cf. :ref:`TestLists.test_list_findingaid`
    """
    # TODO: get these data from SOLR facet!
    result = []
    for ead_file in indexes.ead.get_ead_files(context=request):
        result.append(ead_file['findingaid'])
    result = list(set(result))
    result.sort()
    result = [{'id': findingaid_name} for findingaid_name in result]
    return {
        'results': result,
        'total_results': len(result),
    }
