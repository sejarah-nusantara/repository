#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


import colander

from restrepo.config import ERRORS
from restrepo.models.lists import ComponentSearchSchema
from restrepo.models.lists import GetComponentForViewerSchema
from restrepo.models.archivefile import ArchiveFileSearchSchema, ArchiveFilePutSchema, ArchiveFileGetSchema
from restrepo.indexes.archivefile import get_archivefile


def validate_schema(schema, data, request):
    try:
        request.validated = schema.deserialize(data)
    except colander.Invalid, e:
        errors = e.asdict()
        for errorfield, errorvalue in errors.items():
            request.errors.add('request', ERRORS.invalid_parameter.name, '%s: %s' % (errorfield, errorvalue))
    for key in data:
        if key not in schema:
            request.errors.add('request', ERRORS.invalid_parameter.name, "Unknown field: %s" % key)


def no_status0_factory(action, object_type):
    def method(request):
        if 'status' in request.validated and request.validated['status'] == 0:
            message = {
                'update': 'To delete this %s use the DELETE HTTP verb.',
                'create': 'Creating a deleted %s is not allowed.',
            }[action] % object_type
            request.errors.add('postdata', ERRORS.invalid_parameter.name, message)
    return method


def must_have_ead_id_or_archive_id(request):
    ead_id = request.GET.get('ead_id', '')
    archive_id = request.GET.get('archive_id', '')
    if not ead_id and not archive_id:
        msg = 'Either "ead_id" or "archive_id" must be given'
        request.errors.add('querystring', ERRORS.missing_parameter.name, msg)
        return

    if archive_id:
        try:
            archive_id = int(archive_id)
        except ValueError:
            msg = '"archive_id" must be a number'
            request.errors.add('querystring', ERRORS.invalid_parameter.name, msg)
            return

    request.environ['ead_id'] = ead_id
    request.environ['archive_id'] = archive_id


def search_components_valid_parameters(request):
    schema = ComponentSearchSchema()
    data = dict(request.GET)
    validate_schema(schema, data, request)


def search_archivefile_valid_parameters(request):
    schema = ArchiveFileSearchSchema()
    data = dict(request.GET)
    validate_schema(schema, data, request)

    # we have a further undocumented feature that allows us to pass multiple archiveFile params
    # (this is a bit of a hack, but i am in a hurry and i could not get colander to validate properly)
    data = request.GET.mixed()
    if 'archiveFile' in data and isinstance(data['archiveFile'], type([])):
        request.validated['archiveFiles'] = data['archiveFile']
        del request.validated['archiveFile']


def archivefile_put_valid_parameters(request):
    schema = ArchiveFilePutSchema()
    data = dict(request.POST)
    validate_schema(schema, data, request)


def xpath_must_have_ead_id(request):
    if request.validated.get('xpath') and not request.validated.get('ead_id'):
        request.errors.add('querysting', ERRORS.invalid_parameter.name, 'The xpath parameter can only be used in combination with "ead_id"')


def get_component_for_viewer_valid_parameters(request):
    schema = GetComponentForViewerSchema()
    data = dict(request.GET)
    validate_schema(schema, data, request)


def get_archivefile_conditions(request):
    "Extracts from the requests a SqlAlchemy condition to find a scan"
    result = []
    return result


def validate_archivefile_presence(request):
    schema = ArchiveFileGetSchema()
    data = request.matchdict
    validate_schema(schema, data, request)
    if request.errors:
        return
    archivefile = get_archivefile(request, **data)

    if archivefile:
        request._dbentity['archivefile'] = archivefile
    else:
        request.errors.status = 404
        request.errors.add('url', ERRORS.archivefile_notfound.name, 'An archivefile was not found')
