# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


""" Web services for EAD files.
"""
import ntpath
import posixpath
import transaction

from dateutil.tz import tzutc

from sqlalchemy.orm.exc import NoResultFound
from StringIO import StringIO

from lxml import etree
from lxml.etree import XMLSyntaxError

from pyramid.response import FileResponse

from cornice import Service

from .validation import validate_schema, no_status0_factory

from restrepo import get_datafile
from restrepo.utils import file_null_renderer
from restrepo.models.ead import EadSchema, EadSearchSchema
from restrepo.storage import store_file, real_path
from restrepo.db import EadFile
from restrepo.browser import lists
from restrepo.db.archive import get_archives
from restrepo.db.eadcomponent import get_archive_file_ids
from restrepo import config
from restrepo.config import ERRORS
from restrepo.browser.log import get_user, log_events
from restrepo import db
from restrepo import indexes
import restrepo.indexes.ead
from restrepo.storage import delete_file
from restrepo.config import SERVICE_EAD_COLLECTION, SERVICE_EAD_ITEM
from restrepo.config import SERVICE_EAD_ITEM_RAW
from restrepo.utils import set_cors
from restrepo.utils import now
from restrepo.indexes.archivefile import cast_component_as_archivefile
from restrepo.indexes import reindex_archivefiles
from restrepo.db.archivefile import get_archivefiles
from restrepo.db.archivefile import ArchiveFile
from restrepo.db.archivefile import sort_field
from restrepo import pagebrowser
from restrepo.config import STATUS_PUBLISHED

ead_service = Service(name=SERVICE_EAD_COLLECTION[1:], path=SERVICE_EAD_COLLECTION,
                      description=__doc__)

DTD = etree.DTD(StringIO(get_datafile('ead2002.dtd')))


def valid_xml_file(request):
    """check if the uploaded file is valid.

    we check:
        - XML validates
        - XML contains the necessary elements
    """

    # we add a 'warnings' attribute, which we might use for user feedback (not implemented)
    if not hasattr(request, 'warnings'):
        request.warnings = []

    if 'file' not in request.POST:
        return
    fileobj = request.POST['file']

    if not hasattr(fileobj, 'file'):
        raise Exception('{fileobj} has no attribute "file"'.format(fileobj=fileobj))

    filecontents = fileobj.file.read()

    fileobj.file.seek(0)  # Be polite and leave things as we found 'em
    try:
        root = etree.XML(filecontents)
    except XMLSyntaxError, ex:
        request.errors.add('postdata', ERRORS.xml_syntax_error.name, str(ex))
        return

    request.validated['parsed_file'] = root
    request.validated['raw_file'] = filecontents

    if not DTD.validate(root):
        for error in DTD.error_log.filter_from_errors():
            errorstr = "Line %i, col %i: %s" % (
                error.line, error.column, str(error))
            request.errors.add('postdata', ERRORS.xml_dtd_validation_error.name, errorstr)

    try:
        institution = db.ead.get_institution(root)
    except db.ead.InvalidinstitutionException, ex:
        institution = None
        request.errors.add('postdata', ERRORS.ead_error.name, str(ex))

    try:
        archive = db.ead.get_archive_from_xml(root)
    except db.ead.InvalidArchiveException as ex:
        archive = None
        request.errors.add('postdata', ERRORS.ead_error.name, str(ex))

    # check if this archive is contained in our master list
    if institution and archive:
        archives=get_archives(request, institution=institution, archive=archive)
        if not archives:
            msg=('Unknown archive with institution="%s" and archive="%s"'
                  ' - check %s for the master list ') % (
                  institution, archive, config.SERVICE_ARCHIVE_COLLECTION)
            request.errors.add('postdata', ERRORS.archive_not_found.name, msg)
    else:
        msg='Institution and archive should be defined'
        request.errors.add('postdata', ERRORS.ead_error.name, msg)

    #
    # check uniqueness of archiveFiles
    #
    archive_files=get_archive_file_ids(root)

    # Test for empty file ids - only issue a warning
    if None in archive_files:
        msg='You have a archive file without an unitid in this EAD file'
        request.warnings.append(('postdata', ERRORS.ead_error.name, msg))

    #
    # test for duplicate ids - only issue a warning
    #
    if len(list(set(archive_files))) != len(archive_files):
        # there are duplicates, we find them to show to the user
        d ={}
        for x in archive_files:
            d[x]=d.get(x, 0) + 1
        duplicates = [x for x in d if d[x] > 1 if x]
        msg = 'There are duplicate ids of archive files in this file: %s' % ', '.join(duplicates)
        request.warnings.append(('postdata', ERRORS.duplicate_archive_ids.name, msg))


def valid_ead(request):
    schema = EadSchema()
    ead = dict(request.POST)
    if 'file' in ead:
        del ead['file']
    validate_schema(schema, ead, request)


def fullpath_to_filename(fullpath):
    "Return the file basename. Path can be win or posix style"
    if '\\' in fullpath:
        return ntpath.basename(fullpath)
    else:
        return posixpath.basename(fullpath)


def extract_ead_id(request):
    "Extract the id for the ead in the 'file' postdata variable"
    root = request.validated.get('parsed_file', None)
    possible_ids = root.xpath('/ead/eadheader/eadid/attribute::urn')
    if possible_ids:
        return possible_ids[0]
    else:
        return fullpath_to_filename(request.POST['file'].filename)


def unique_file_id(request):
    if not len(request.validated.get('parsed_file', '')):
        return  # The file is unparsable, an error was already set
    ead_id = extract_ead_id(request)
    cond = EadFile.name == ead_id
    nexisting=request.db.query(EadFile).filter(cond).count()
    if nexisting:
        request.errors.add('postdata', ERRORS.ead_exists.name,
                           "A file with id '%s' is already present" % ead_id)
    if '/' in ead_id:
        msg = 'Forward slashes are not allowed in the file parameter'
        request.errors.add('postdata', ERRORS.ead_invalid_id.name, msg)
    request.validated['ead_id'] = ead_id


no_status0 = no_status0_factory('create', 'ead')


@ead_service.post(
    validators=[valid_ead, valid_xml_file, unique_file_id, no_status0],
    permission='write',
    )
def service_add_ead_file(request):
    """
    Add a new EAD file

    parameters:

        * **file:**
        * **user:**
            the name of a user - optional, will be used for logging info
        * **status:**
            optional, a value among :ref:`status_values` (except 0)

        :returns: a JSON object with the id and url.

        See :ref:`TestEad.test_add`

    If successful, the file will be available on ``/ead/{ead_id}``,
    where ``{ead_id}`` is determined as follows:

        1. the value of ``/ead/eadheader/eadid/attribute::urn`` is defined,
           if this exists
        2. otherwise, the file name of the uploaded file

    If a file with this id exists, an error is raised.
    See :ref:`TestEad.test_error_if_upload_twice_id_from_filename`
    and :ref:`TestEad.test_error_if_upload_twice_id_from_content`

    If the file is not valid, an error is raised.
    See :ref:`TestEad.test_invalid_xml` and
    :ref:`TestEad.test_valid_xml_but_wrong_as_dtd`

    """
    eadfile = db.ead.add_ead_file(
        context=request,
        name=request.validated['ead_id'],
        status=request.validated['status'],
        filecontents=request.validated['raw_file'],
    )

    request._dbentity['ead'] = eadfile

    user = get_user(request)
    log_events(request.db, user, [{
        'object_id': request._dbentity['ead'].name,
        'object_type': 'ead',
        'message': 'create'
    }])

    context = request
    context.solr_ead.update([eadfile.get_solr_data()])

    components = eadfile.extract_component_dicts()
    context.solr_eadcomponent.update(components)
    context.solr.commit()

    archivefiles = [cast_component_as_archivefile(x).get_solr_data(context) for x in components if x['is_archiveFile']]
    for archivefile in archivefiles:
        db_records = get_archivefiles(request, archiveFile=archivefile['archiveFile'], archive_id=archivefile['archive_id'])
        if db_records:
            db_record = db_records[0]
            archivefile['status'] = db_record.status

    context.solr_archivefile.update(archivefiles)

    ead_id = eadfile.name
    for archivefile in archivefiles:
        if archivefile['status'] == config.STATUS_PUBLISHED:
            pagebrowser.update.refresh_book(context, ead_id=ead_id, archivefile_id=archivefile['archivefile_id'])

    return eadfile.to_dict(request)


def ead_valid_searchdata(request):
    schema = EadSearchSchema()
    ead = dict(request.GET)
    validate_schema(schema, ead, request)


@ead_service.get(validators=ead_valid_searchdata, filters=set_cors)
def search_ead_files(request):
    """
    Search for EAD files

    parameters:
        * **archive_id:** integer.
            return all EAD files that have institution and archive
            corresponding with archive_id

        * **country:** string.
        * **institution:** string.
        * **archive:** string.
        * **findingaid:** string.
        * **language:** string, a language code such as "eng"


    :returns:
        a list object representing EAD files;

    see :ref:`TestEad.test_search`
    """
    # TODO: EAD file should also return "number_of_scans")

    results = indexes.ead.get_ead_files(request, **request.validated)
    # XXX this is not good: we are searching for data stored in solr.
    # When data comes out we instantiate the original object
    # and call expensive methods on it.
    # (but given that we expect max < 100 files, it is not too serious)
    # TODO: tune solr stored fields so that results is good to be fed
    # as a response
    results = [EadFile(context=request, **ead).to_dict(request)
        for ead in results]

    return {
        'results': results,
        'query_used': dict(request.GET),
        'total_results': len(results),
    }


def retrieve_ead(request):
    ead_id =request.matchdict.get('ead_id', '') or request.GET.get('ead_id', '')

    try:
        ead =db.ead.get_ead_file(request, ead_id)
        request._dbentity['ead'] = ead
    except NoResultFound:
        request.errors.status = 404
        request.errors.add('url', ERRORS.ead_not_found.name,
            'File %s was not found in the database' % ead_id)

ead_file_service = Service(
    name='ead_file',
    path=SERVICE_EAD_ITEM,
    description=""
)


@ead_file_service.get(validators=[retrieve_ead], filters=set_cors)
def get_ead_file(request):
    """
    Retrieve data about the EAD file

    :returns:
        a JSON structure. See :ref:`TestEad.test_get_ead`
    """
    eadfile = request._dbentity['ead']

    return eadfile.to_dict(dbdata_only = True)


ead_file_service_raw =Service(name='ead_file_raw',
    path=SERVICE_EAD_ITEM_RAW, description="")


@ead_file_service_raw.get(renderer=file_null_renderer,
    validators=[retrieve_ead], filters=set_cors)
def get_ead_file_raw(request):
    """
    Retrieve the EAD file with the given ``ead_id``

    :returns:
        the original XML file. See :ref:`TestEad.test_get_raw_ead`

    """
    path=real_path(request._dbentity['ead'].get_file_path())
    return FileResponse(path, request=request, content_type='text/xml')


def no_id_change(request):
    if not len(request.validated.get('parsed_file', '')):
        return  # The file is unparsable or not provided
    new_id=extract_ead_id(request)
    if not new_id:
        return  # no check necessary: nobody is trying to change the id
    current_id=request._dbentity['ead'].name
    if new_id != current_id:
        message=("You are trying to update the ead file with id "
                   "%(current_id)s; the file you are providing "
                   "has id %(new_id)s."
                   " Either change its id or create a new one") % locals()
        request.errors.add('url', ERRORS.ead_invalid_id.name, message)


no_status0_update=no_status0_factory('update', 'ead')


@ead_file_service.put(
    validators=[valid_ead, retrieve_ead, valid_xml_file, no_id_change, no_status0_update],
    permission='write',
    )
def update_ead_file(request):
    """
    Update an EAD file

    parameters:

        * **file:**
            the XML file to
        * **user:**
             the name of a user - optional, will be used for logging info
        %(PARAM_STATUS)s

    returns: JSON object representing the EAD file

    see :ref:`TestEad.test_ead_update`
    """
    eadfile=request._dbentity['ead']
    ead_id=eadfile.name

    path=eadfile.get_file_path()
    if 'raw_file' in request.validated:
        store_file(path, request.validated['raw_file'])
    if 'status' in request.POST:
        eadfile.status=request.validated['status']
    user=get_user(request)
    if 'raw_file' in request.validated or eadfile in request.db.dirty:
        eadfile.last_modified=now()
        log_events(request.db, user, [{
            'object_id': ead_id,
            'object_type': 'ead',
            'message': 'update'
        }])
    request.solr_ead.update([eadfile.get_solr_data()])
    request.solr.commit()  # we need to commit before we index the archivefile

    request.solr_eadcomponent.delete_by_query('ead_id:' + ead_id)
    components = eadfile.extract_component_dicts()
    request.solr_eadcomponent.update(components)
    request.solr.commit()

    # archivefiles that are already indexed
    indexed_archivefiles = request.solr_archivefile.search(q='ead_ids:' + eadfile.name).documents
    # components of this ead file that are to be indexed as archivefiles
    to_index_archivefiles = [cast_component_as_archivefile(x).get_solr_data(request) for x in components if x['is_archiveFile']]
    to_index_archivefile_ids = [x['archivefile_id'] for x in to_index_archivefiles]
    to_delete_archivefiles = []

    for x in indexed_archivefiles:
        # delete all archivefiles that have no scans available, and are not in this ead file (anymore)
        if x['number_of_scans'] == 0 and x['archivefile_id'] not in to_index_archivefile_ids:
            request.solr_archivefile.delete_by_key(x['id'])
            to_delete_archivefiles.append(x)

    db_records = get_archivefiles(request, archive_id=x['archive_id'])
    db_records = {db_record.id: db_record for db_record in db_records}
    for document in to_index_archivefiles:
        if document['archivefile_id'] in db_records:
            db_record = db_records[document['archivefile_id']]
            if document['status'] != db_record.status:
                document['status'] = db_record.status

    request.solr_archivefile.update(to_index_archivefiles)

    # commit, and ping the pagebrowser
    for x in to_delete_archivefiles:
        pagebrowser.update.delete_book(request, ead_id=ead_id, archivefile_id=x['archivefile_id'])
    for document in to_index_archivefiles:
        if document['archivefile_id'] in db_records:
            if document['status'] == STATUS_PUBLISHED:
                pagebrowser.update.refresh_book(request, ead_id=ead_id, archivefile_id=document['archivefile_id'])
            else:
                pagebrowser.update.delete_book(request, ead_id=ead_id, archivefile_id=document['archivefile_id'])

    return eadfile.to_dict(request)


@ead_file_service.delete(validators=[retrieve_ead], permission='write')
def delete_ead_file(request):
    """Delete this file

    see :ref:`TestEad.test_delete`
    """
    user = get_user(request)
    log_events(request.db, user, [{
        'object_id': request._dbentity['ead'].name,
        'object_type': 'ead',
        'message': 'delete'
    }])
    ead = request._dbentity['ead']
    delete_file(ead.get_file_path())
    request.db.delete(ead)
    request.solr_ead.delete_by_key(ead.name)
    request.solr_eadcomponent.delete_by_query('ead_id:' + ead.name)
    #
    # get the archivefiles belonging to this ead
    documents = request.solr_archivefile.search(q='ead_ids:' + ead.name).documents

    # some archivefiles will need to be udpated, others deleted
    documents_to_update = []
    documents_to_delete = []
    for document in documents:
        if len(document['ead_ids']) > 1 or document['number_of_scans'] > 0:
            document['ead_ids'].remove(ead.name)

            # we need to manually set the sort_field, as this is not a stored field
            document['sort_field'] = sort_field(archive_id=document['archive_id'], archiveFile=document['archiveFile'])
            documents_to_update.append(document)
        else:
            documents_to_delete.append(document)

    request.solr_archivefile.update(documents_to_update)
    ead_id = ead.name
    for document in documents:
        pagebrowser.update.delete_book(request, ead_id=ead_id, archivefile_id=document['archivefile_id'])
    return {'success': True}

config.update_docstrings(locals())
