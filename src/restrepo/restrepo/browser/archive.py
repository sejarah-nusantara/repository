# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013-
#

""" Web services for Archives.
"""
# import ntpath
# import posixpath
# from dateutil.tz import tzutc

from sqlalchemy.orm.exc import NoResultFound
# from StringIO import StringIO

# from lxml import etree
# from lxml.etree import XMLSyntaxError

# from pyramid.response import FileResponse
from cornice import Service

from .validation import validate_schema, no_status0_factory

# from restrepo import get_datafile
# import restrepo.indexes.ead
# from restrepo.utils import file_null_renderer
from restrepo.models.archive import ArchiveSchema
from restrepo.storage import store_file, real_path
# from restrepo.db import EadFile
from restrepo.db.archive import Archive
# from restrepo.browser import lists
from restrepo import config
from restrepo.config import ERRORS
from restrepo.browser.log import get_user, log_events
from restrepo.config import SERVICE_ARCHIVE_ITEM, SERVICE_ARCHIVE_COLLECTION
# from restrepo.utils import now
from restrepo.db.archive import get_archive, get_archives
from restrepo.indexes.ead import get_ead_files
from restrepo.utils import set_cors

ARCHIVE_IDENTIFIERS = [
    'institution',
    'archive',
]

service_archive_collection = Service(
    name='list_archives',
    path=SERVICE_ARCHIVE_COLLECTION,
    description="List of available archives",
)

archive_service = Service(
    name='archive',
    path=SERVICE_ARCHIVE_ITEM,
    description="",
)


@service_archive_collection.get(filters=set_cors)
def get_list_of_archives(request):
    """returns a list of available archives

    parameters:
        * **institution:**
            optional
        * **archive:**
            optional
        * **country_code:**
            optional
        * **archive_id:**
            optional

    See  :ref:`TestLists.test_archives` for the structure returned.
    """
    #
    # TODO: use the validation pattern we used in other services to parse and check parameters
    #
    institution = request.GET.get('institution', None)
    archive = request.GET.get('archive', None)
    country = request.GET.get('country', None)
    archive_id = request.GET.get('archive_id', None)
    archives = get_archives(
        request,
        institution=institution,
        archive=archive,
        country=country,
        archive_id=archive_id,
        )
    archives = [archive.to_dict(request) for archive in archives]
    result = {
        "total_results": len(archives),
        "results": archives,
    }
    # check uniqueness of id's
    ids = [x['id'] for x in result['results']]
    assert len(set(ids)) == len(ids)
    return result

#
# institution: "ID-ANRI",
# institution_description: "Arsip Nasional Republik Indonesia",
# id: 1,
# archive_description: "Archief van de Gouverneur Generaal en Raden van Indie (Hoge Regering) van de VOC en Taakopvolgers",
# country_code: "ID",
# archive: "K.66a"


def retrieve_archive(request):
    """retrieve the archive corresponding tot he request"""
    archive_id = request.matchdict.get('archive_id')
    try:
        archive = get_archive(context=request, archive_id=archive_id)
        request._dbentity['archive'] = archive
    except NoResultFound:
        request.errors.status = 404
        request.errors.add('url', ERRORS.archive_not_found.name,
            'An archive with id %s was not found' % archive_id)


@archive_service.get(validators=[retrieve_archive])
def service_get_archive(request):
    """
    Retrieve data about the EAD file

    :returns:
        a JSON structure. See :ref:`TestArchive.test_get`
    """
    archive = request._dbentity['archive']
    return archive.to_dict()


def valid_archive(request):
    schema = ArchiveSchema()
    archive = dict(request.POST)
    validate_schema(schema, archive, request)


def archive_and_institution_are_present(request):
    if not request.validated.get('archive'):
        request.errors.add('request', ERRORS.archive_missing_value_archive.name, 'No value given for "archive"',)
    if not request.validated.get('institution'):
        request.errors.add('request', ERRORS.archive_missing_value_institution.name, 'No value given for "institution"')


def does_not_exist(request):
#    """make sure an archive with this archive and institution does not exist yet"""
    if request.errors:
        # we had earlier validation errors, and don't bother to check
        return
    if request.validated.get('archive') or request.validated.get('institution'):
        new_archive = request.validated['archive'] or request._dbentity['archive'].archive
        new_institution = request.validated['institution'] or request._dbentity['archive'].institution
        archives = get_archives(request, archive=new_archive, institution=new_institution)
        if request._dbentity.get('archive'):
            archives = [a for a in archives if a.id != request._dbentity['archive'].id]
        if archives:
            msg = 'An archive with institution %s and archive %s already exists' % (new_institution, new_archive)
            request.errors.add('request', ERRORS.archive_exists.name, msg)


def archive_and_institution_not_empty(request):
    if request.params.get('archive') == '':
        request.errors.add('request', ERRORS.archive_missing_value_archive.name, 'No value given for "archive"')
    if request.params.get('institution') == '':
        request.errors.add('request', ERRORS.archive_missing_value_institution.name, 'No value given for "institution"')


@service_archive_collection.post(
    validators=[valid_archive, archive_and_institution_are_present, does_not_exist],
    permission='write',
    )
def service_add_archive(request):
    """
    Add a new Archive

    :parameters:

        * **archive:** string, a code of the archive, required
        * **institution:** string - code of the institution, required
        * **archive_description:** string,
        * **country_code:** string
        * **institution_description:** string
        * **user:** optional, a string.

    :returns: a JSON object with the id and url.

    archive and institution taken together should be unique.

    see :ref:`TestArchive.test_add`
    """
    archive = Archive()
    for k, v in request.validated.items():
        setattr(archive, k, v)

    request.db.add(archive)
    request.db.flush()
    request._dbentity['archive'] = archive
    user = get_user(request)
    log_events(request.db, user, [{
        'object_id': request._dbentity['archive'].id,
        'object_type': 'archive',
        'message': 'create'
    }])

    return archive.to_dict(request)


def has_no_scans(request):
    """
    Check if the archive from the request has not references anywhere
    """
    scans = request.solr_scan.search(q='archive_id:%s' % request._dbentity['archive'].id)
    if scans.total_results > 0:
        msg = "The archive has %s scans, and can therefore not be changed or deleted" % scans.total_results
        request.errors.add('data', ERRORS.archive_has_scans.name, msg)
        return False
    return True


def has_no_eads(request):
    """
    Check if the archive has EADs attached.
    """
    archive = request._dbentity['archive']
    eads = get_ead_files(request, archive=archive.archive, institution=archive.institution)
    if len(eads) > 0:
        msg = "The archive has %s EAD files, and can therefore not be changed or deleted" % len(eads)
        request.errors.add('data', ERRORS.archive_has_eads.name, msg)
        return False
    return True


@archive_service.put(validators=[valid_archive, retrieve_archive, archive_and_institution_not_empty, does_not_exist], permission='write')
def update_archive(request):
    """
    Update an Archive

    parameters:
        see add_archive.

    :returns:
        a JSON object representing the updated archive

    see :ref:`TestArchive.test_update`
    """
    archive = request._dbentity['archive']

    # if identifying properties get changed, we raise an error
    is_dirty = filter(None, [getattr(archive, attr) != request.validated[attr] for attr in ARCHIVE_IDENTIFIERS
                    if request.validated[attr]])
    if is_dirty:
        if not has_no_eads(request):
            msg = 'You cannot change the attributes %s of this archive, because it has EAD files connected' % ', '.join(['"%s"' % x for x in ARCHIVE_IDENTIFIERS])
            request.errors.add('data', ERRORS.archive_has_eads.name, msg)
            return archive.to_dict(request)
        elif not has_no_scans(request):
            msg = 'You cannot change the attributes %s of this archive, because it has scans connected' % ', '.join(['"%s"' % x for x in ARCHIVE_IDENTIFIERS])
            request.errors.add('data', ERRORS.archive_has_scans.name, msg)
            return archive.to_dict(request)

    for k, v in request.validated.items():
        setattr(archive, k, v)
    user = get_user(request)
    log_events(request.db, user, [{
        'object_id': archive.id,
        'object_type': 'archive',
        'message': 'update'
    }])
    return archive.to_dict(request)


@archive_service.delete(validators=[retrieve_archive, has_no_scans, has_no_eads], permission='write')
def delete_archive(request):
    """
    Delete this archive

    An archive can only be deleted if it is not references by any scans, and it is not referenced in any EAD file.

    see :ref:`TestArchive.test_delete`
    """
    user = get_user(request)
    log_events(request.db, user, [{
        'object_id': request._dbentity['archive'].id,
        'object_type': 'archive',
        'message': 'delete'
    }])
    archive = request._dbentity['archive']
    request.db.delete(archive)
    return {'success': True}

config.update_docstrings(locals())
