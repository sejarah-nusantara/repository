# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


""" Web services for scans.
Each scan represent a scanned page (an image).
"""
import re
import os
import json
import operator
import sqlalchemy
import logging
import types
from cgi import FieldStorage

from sqlalchemy.orm.attributes import InstrumentedAttribute

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import FileResponse
from cornice import Service

from webob.multidict import NoVars

from magic import get_filetype, whatis
from .validation import validate_schema, no_status0_factory
from .log import log_events, get_user
from restrepo.models.scan import ScanSchema, SearchSchema, ImageCollectionPost, CollectionImagesDeleteSchema
from restrepo.db import Scan
from restrepo.utils import file_null_renderer, now
from restrepo import config
from restrepo.config import SERVICE_SCAN_ITEM, ARCHIVE_IDS, SERVICE_SCAN_COLLECTION
from restrepo.config import SERVICE_SCAN_IMAGES_COLLECTION, SERVICE_SCAN_IMAGES_ITEM, SERVICE_SCAN_IMAGES_ITEM_RAW
from restrepo.config import SERVICE_SCAN_ITEM_DEFAULT_IMAGE
from restrepo.config import update_docstrings
from restrepo.db.scans import collapse_images_array
from restrepo.db.archive import get_archive
from restrepo.db.scan_images import ScanImage
from restrepo.db.archivefile import sort_field
from restrepo.config import ERRORS
from restrepo.db.solr import build_equality_query
from restrepo.db.solr import SolrException
from restrepo.indexes.lists import search_components
from restrepo.indexes.archivefile import search_archivefiles
from restrepo.indexes.archivefile import cast_scan_as_archivefile
from restrepo.browser.archivefile import delete_orphaned_archivefile
from restrepo.indexes.archivefile import get_archivefile
from restrepo.indexes.archivefile import cast_archivefile_as_component
from restrepo.utils import set_cors
from restrepo import pagebrowser
from restrepo.db.archivefile import ArchiveFile

log = logging.getLogger(__name__)


SUPPORTED_IMAGE_FORMATS = (
    'image/jpeg', 'image/tiff', 'image/x-png', 'image/gif'
)


def archive_condition(archive_id, archiveFile):
    "return sqlalchemy condition that selects scans belonging to this archive"
    result = (Scan.archive_id == archive_id) & (Scan.archiveFile == archiveFile)
    return result


def find_next_sequence_number(request, archive_id, archiveFile):
    """return the first unused sequence number with the archive"""
    condition = archive_condition(archive_id, archiveFile)
    column = sqlalchemy.func.max(Scan.sequenceNumber)
    query = sqlalchemy.select((column,)).where(condition)
    return (request.db.execute(query).fetchone()[0] or 0) + 1


def valid_scan_file(request):
    if 'file' in request.POST:
        if not isinstance(request.POST['file'], FieldStorage):
            request.errors.add(
                'body', ERRORS.missing_file.name,
                "The file parameter doesn't contain a file")
            return
        filetype = whatis(request.POST['file'].file.read())
        request.POST['file'].file.seek(0)
        if filetype not in SUPPORTED_IMAGE_FORMATS:
            request.errors.add(
                'body', ERRORS.invalid_file.name,
                "Unsupported file type")


def lock_table_scan(request):
    # request.db.execute('LOCK TABLE scan IN EXCLUSIVE  MODE')
    request.db.execute('Lock table scan in share row exclusive mode')


def valid_scan_data_new(request):
    # "Check incoming data: ensure desired schema"
    if 'file' not in request.POST:
        request.errors.add('body', ERRORS.invalid_file.name, "Missing file")
        return
    schema = ScanSchema()
    scan = dict(request.POST)
    del scan['file']
    validate_schema(schema, scan, request)
    check_unmutablefields(request)
    valid_archive_id(scan['archive_id'], request)


def valid_scan_data(request):
    """
    Updating the scan with the provided data should leave the scan
    in a consisistent state
    """
    schema = ScanSchema()
    scan = request._dbentity['scan'].to_dict(request)
    # This "Scan" represents the status the scan will have
    # after being updated. So we can use the same validation
    # for creation and update (and we can check invariants
    # spanning more than one attribute).
    # We need to remove the fields that would make it invalid
    # i.e. dateLastModified (that will come from the db)
    # and file (that might be present in the request.)
    scan.update(request.POST)
    del scan['dateLastModified']

    if 'file' in scan:
        del scan['file']  # 'file' is not in the schema

    validate_schema(schema, scan, request)
    check_unmutablefields(request)
    valid_archive_id(scan['archive_id'], request)


def check_unmutablefields(request):
    # number and sequenceNumber are not directly mutable
    for fieldname in ('number', 'sequenceNumber', 'URL'):
        if fieldname in request.POST:
            request.errors.add('postdata', ERRORS.invalid_parameter.name,
                "Direct update not allowed")


def valid_archive_id(archive_id, request):
    "Check referential integrity of archive_id: it must exist"
    try:
        archive_id = int(archive_id)
    except ValueError:
        request.errors.add(
            'postdata',
            ERRORS.archive_not_found.name,
            'Invalid value for archive_id:' +
            '"%s" (must be a integer)' % archive_id)

    if archive_id:
        try:
            #
            # TODO: get_archive gets its data from the database - from the index would be better
            #
            get_archive(request, archive_id=archive_id)
        except Exception:  # TODO: Use a more specific exception!
            # and/or return a "Unknown error" since that's what happened
            request.errors.add('postdata', ERRORS.archive_not_found.name,
                'Unknown archive_id: "%s"' % archive_id)


no_status0 = no_status0_factory('create', 'scan')

service_scan_collection = Service(name='service_scan_collection', path=SERVICE_SCAN_COLLECTION, description=__doc__)


def prepare_data(request):
    """
    Colander fills in missing values, but we only want to update
    the columns we were explicitly required.
    """
    return dict(
        (k, request.validated[k]) for k in request.POST.keys()
        if k != 'file'
    )


@service_scan_collection.post(
    validators=[lock_table_scan, valid_scan_data_new, valid_scan_file, no_status0],
    permission='write',
)
def add_scan(request):
    """
    Add a new scan.

    parameters:
        %(PARAM_ARCHIVE_ID)s
        * **archiveFile:**
            identifier of an archive file within the archive
            (given by archive_id)
        * **file:**
            the image of the scan. Must be TIFF, GIF, PNG or JPEG.
        * **status:**
            a status: a value among :ref:`status_values` (except 0)
        * **user:**
            the name of a user - optional, will be used for logging info
        * **date:**
            a date for the scan. If this value is not given, the current date/time will be used.
        :other parameters:
            all parameters from the data model  :ref:`datamodel_scans`
        :returns:
            information about the scan

    See :ref:`TestScans.test_add`
    and :ref:`TestScanImages.test_scan_get_has_key_images`.

    """  # The last line in the docstring is needed to avoid a sphynx warning

    data = prepare_data(request)
    scan = Scan()
    for key in data:
        setattr(scan, key, data[key])

    scan.sequenceNumber = find_next_sequence_number(
        request, scan.archive_id, scan.archiveFile)

    if not scan.date:
        scan.date = now()

    scan.last_modified = now()

    request.db.add(scan)
    request.db.flush()

    add_files_from_request(request, scan, is_default=True)

    request.db.refresh(scan)
    request._dbentity = dict(scan=scan)
    user = get_user(request)
    log_events(request.db, user, [{
        'message': 'create', 'object_id': scan.number, 'object_type': 'scan'
    }])

    # TOOD: optimization: next line can be optimized (using partial_update_keys)
    scandata = scan.get_solr_data()
    request.solr_scan.update([scandata])

    # we need to update the corresponding archive file
    document = cast_scan_as_archivefile(request, scandata).get_solr_data(request)
    document['number_of_scans'] = document['number_of_scans'] + 1

    def partial_update_keys(document):
        del document['title']
        del document['titles']
        keep_these_original = ['_version', 'id', 'archive_id', 'archivefile_id']

        partial_document = dict(
            [(k, document[k]) for k in document if k in keep_these_original] +
            [(k, {'set': document[k]}) for k in document if k not in keep_these_original]
        )
        return partial_document

    request.solr_archivefile.update([partial_update_keys(document)])

    component = cast_archivefile_as_component(request, document)
    if component:
        try:
            request.solr_eadcomponent.update([component])
        except SolrException as error:
            if error.message['responseHeader']['status'] == 409:
                # this probably is a version conflict error [???]
                component['_version_'] = 0
                request.solr_eadcomponent.update([component])
            else:
                raise

    for ead_id in document['ead_ids']:
        pagebrowser.update.refresh_book(request, ead_id=ead_id, archivefile_id=document['archivefile_id'])

    # TODO: refactor: WHY IS THIS NEEDED HERE???
    try:
        # using request.db.commit on a running server throws an error
        # but in tests we seem to need it.
        request.db.commit()
    except:
        pass
    return desolarize(scandata, request)


def add_files_from_request(request, scan, is_default=False):
    """read files from request, associate them with scan object, and save them to disk.

    if is_default is True, the first provided image is the default image
    """
    added_images = []
    for fileobj in request.POST.getall('file'):
        image = ScanImage(filename=fileobj.filename, scan_number=scan.number, is_default=is_default)
        scan.images.append(image)
        added_images.append(image)
        request.db.flush()
        scan.store_file(fileobj.file.read(), image.id)
        is_default = False  # only the first image can be teh default image
    return added_images


def valid_search_data(request):
    get_as_dict = request.GET.copy().mixed()

    if 'timeFrames' in get_as_dict:
        if not isinstance(get_as_dict['timeFrames'], types.ListType):
            get_as_dict['timeFrames'] = [get_as_dict['timeFrames']]
    validate_schema(SearchSchema(), get_as_dict, request)
    if not request.validated:
        return

    request.validated['order_by'] = request.validated['order_by'].split(',')
    # check that every field we are requested to order_by
    # is actually a valid field of Scan
    for field_name in request.validated['order_by']:
        if field_name.startswith('-'):
            field_name = field_name[1:]
        field = getattr(Scan, field_name, None)
        if not isinstance(field, InstrumentedAttribute):
            request.errors.add('querystring', ERRORS.invalid_parameter.name,
                "The field %s is not a field of scan" % field_name)


@service_scan_collection.get(validators=(valid_search_data), filters=set_cors,)
def search_scans(request):
    """
    Search scans.

    :parameters:
        %(PARAM_ARCHIVE_ID)s
        * **country:**
            the country of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **institution:**
            the institution of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archive:**
            the archive of the scan (cf. %(SERVICE_ARCHIVE_COLLECTION)s)
        * **archiveFile:**
            the archiveFile of the scan
        * **archiveFile_raw:**
            an advanced option to search for ranges of archiveFile, using the solr syntax.
            For example, valid arguments are [1000 TO 2000] or [a OR b]
        * **timeFrame**
            return scans that have timeFrame in the range timeFrameFrom to timeFrameTo
        * **timeFrames**
            a list of dates
            return scans that have one of the given dates in the range timeFrameFrom to timeFrameTo
        * **folioNumber** (a string)
            search for scans with this folioNumber
        * **folioNumbers** a list of strings, of the form ["1", "xxx", "345"]
        * **originalFolioNumber** (a string)
            search for scans with this originalFolioNumber
        * **start:**
            index of the first element returned (used in pagination)
        * **limit:**
            max # of objects to return
        * **order_by:**
            a comma-separated list of field names to sort results on.
            Default order is by ``archive_id,archiveFile,sequenceNumber``.
            To sort descending, append '-' to a field name.
        * **status:**
            a status: a value among :ref:`status_values` (defaults to non-0)

    :returns:
            information about the query, and a paged lists of results

    See :ref:`TestScanSearch.test_search_for_archiveFile`
    """
    solr_query = build_equality_query(
        archiveFile=request.validated['archiveFile'],
        archive=request.validated['archive'],
        archive_id=request.validated['archive_id'],
        status=request.validated['status'],
        institution=request.validated['institution'],
        date=request.validated['date'],
        folioNumber=request.validated['folioNumber'],
        originalFolioNumber=request.validated['originalFolioNumber'],
    )

    if request.validated['archiveFile_raw']:
        solr_query = ' AND '.join([solr_query, 'archiveFile:{}'.format(request.validated['archiveFile_raw'])])

    timeFrames = []
    if request.validated['timeFrame']:
        timeFrames.append(request.validated['timeFrame'])

    if request.validated['timeFrames']:
        timeFrames += request.validated['timeFrames']

    if timeFrames:
        timeFrame_query = []
        for timeFrame in timeFrames:
            # timeFrame should either either be
            # 1) >= timeFrameFrom and <= timeFrameTo
            # 2) equal to timeFrameFrom, with timeFrameTo empty
            timeFrame_query.append(
                '((timeFrameFrom:[* TO {timeFrame}] AND timeFrameTo:[{timeFrame} TO *])'.format(timeFrame=timeFrame) +
                ' OR ' +
                'timeFrameFrom:{timeFrame}'.format(timeFrame=timeFrame) +
                ')')
        solr_query += ' AND (' + ' OR '.join(timeFrame_query) + ')'

    if request.validated['folioNumbers']:
        folio_numbers = json.loads(request.validated['folioNumbers'])
        solr_query += ' AND (%s)' % ' OR '.join(['folioNumber:%s' % number for number in folio_numbers])

    # order_dir is implemented but deprecated:
    # we can pass -colname in order_by to sort desc.
    order_dir = request.validated['order_dir']
    start = request.validated['start']
    limit = request.validated['limit']
    order_by = []
    for fieldname in request.validated['order_by']:
        desc = fieldname.startswith('-')
        if desc:
            fieldname = fieldname[1:]
        # order_dir defaults to 'ASC'
        # order_dir = 'DESC' reverses the meaning of -
        # I know, awful, but if I need to support both APIs...
        if not desc and order_dir.lower() == 'asc':
            order_by.append('%s asc' % fieldname)
        else:
            order_by.append('%s desc' % fieldname)

    result = request.solr_scan.search(q=solr_query, sort=','.join(order_by), start=start, rows=limit)
    documents = [
        desolarize(dict(doc, URL=request.route_url('service_scan_item', number=doc['number'])), request)
        for doc in result.documents
    ]
    return {
        'results': documents,
        'query_used': dict(request.GET),
        'total_results': result.total_results,
        'start': start,
        'end': start + len(result.documents)
    }


service_utils_scan_delete = Service(name='service_utils_scan_delete', path=config.SERVICE_UTILS_SCAN_DELETE, description='Delete a batch of scans')


def valid_delete_data(request):
    validate_schema(CollectionImagesDeleteSchema(), request.POST, request)
    if not request.validated:
        return


@service_utils_scan_delete.post(validators=(valid_delete_data), filters=set_cors, permission='write')
def delete_scans(request):
    """
    Delete all scans associated with the given archive_id and archiveFile

    parameters:
        %(PARAM_ARCHIVE_ID)s
        * **archiveFile:**
             as above
    """
    archive_id = request.validated['archive_id']
    archiveFile = request.validated['archiveFile']
    archivefile = get_archivefile(request, archive_id=archive_id, archiveFile=archiveFile)
    if not archivefile:
        return {'success': True}

    scans = request.db.query(Scan)
    scans = scans.filter(Scan.archive_id == archive_id)
    scans = scans.filter(Scan.archiveFile == archiveFile)
    scans = scans.order_by(Scan.sequenceNumber.desc())  # order descendingly, so reordering scans takes little time
    scans = scans.all()

    if not scans:
        return {'success': True}

    # TODO: optimize: we also dont need to reorder, because we drop all scans of the archivefile
    context = request
    for scan in scans:
        user = get_user(request)
        delete_scan(context=context, scan=scan, user=user, ping_pagebrowser=False, update_archivefile=False)

    archivefile['number_of_scans'] = 0
    archivefile_deleted = delete_orphaned_archivefile(context=request, archivefile=archivefile)
    if not archivefile_deleted:
        #
        # if we did not delete the archive file, we need to update the index
        #
        archivefile = cast_scan_as_archivefile(context, scan.get_solr_data()).get_solr_data(context)
        archivefile['number_of_scans'] = 0
        context.solr_archivefile.update([archivefile])
        component = cast_archivefile_as_component(context, archivefile)
        if component:
            context.solr_eadcomponent.update([component])

    # ping the pagebrowser
    for ead_id in archivefile['ead_ids']:
        if archivefile_deleted:
            pagebrowser.update.delete_book(context=request, ead_id=ead_id, archivefile_id=archivefile['id'])
        else:
            pagebrowser.update.refresh_book(context=request, ead_id=ead_id, archivefile_id=archivefile['id'])

    return {'success': True}


def desolarize(doc, request):
    for k in ['text', 'id', 'entity_type']:
        if k in doc:
            del doc[k]

    for key, val in doc.items():
        if val is None:
            del doc[key]

    newdoc = collapse_images_array(doc)

    for image in newdoc["images"]:
        url = request.route_url(
            'service_scan_images_item',
            number=doc['number'],
            number_of_image=image["id"])
        image['URL'] = url

        if image['is_default']:
            default_image_id = image['id']

    URL = request.route_url('service_scan_item', number=doc['number'])

    if doc.get('default_image_id'):
        # we add a hash value based on datelastmodified to make the default image cacheable
        image_url = os.path.join(URL, 'images', str(default_image_id), 'file_%s' % str(hash(doc['dateLastModified'])))
    else:
        image_url = None

    newdoc.update(dict(
        URL=URL,
        image_url=image_url,
    ))
    return newdoc


def validate_scanpresence(request):
    if not request.matchdict['number'].isdigit():
        request.errors.add('url', ERRORS.invalid_parameter.name, 'number must be integer')
        return
    cond = get_scan_condition(request)
    try:
        # TODO: OPTIMIZATION: why not take this from the index?
        request._dbentity['scan'] = request.db.query(Scan).filter(cond).one()
    except sqlalchemy.orm.exc.NoResultFound:
        response = {'errors': [{'location': 'url', 'name': 'no scan found with this number: {number}'.format(**request.matchdict)}]}
        headers = (['Content-Type', 'application/json; charset=UTF-8'],)
        raise HTTPNotFound(body=json.dumps(response), headers=headers)


service_scan_item = Service(
    name='service_scan_item',
    path=SERVICE_SCAN_ITEM,
    description="Access, update or delete data of a single scan",
)


@service_scan_item.get(
    validators=(validate_scanpresence),
    filters=set_cors,
)
def get_scan(request):
    """
    Return a single object representing the requested scan.

    See :ref:`TestScans.test_scan_get_data`
    """
    # For consistency (with what??) we pull the data out of solr
    #

    scan_number = request._dbentity['scan'].number
    scandict = request.solr.search(q='id:scan=%s' % scan_number).documents[0]
    scandict['URL'] = request.route_url('service_scan_item', number=scan_number)
    return desolarize(scandict, request)


@service_scan_item.delete(
    validators=[
        lock_table_scan,
        validate_scanpresence
    ],
    permission='write',
)
def delete_scan_handler(request):
    """
    Delete this scan.

    All following scans have their sequenceNumber decremented
    to avoid holes (that would make the index specified
    in the move operation ambiguous).

    parameters (in url, like http://host/scans/13?user=somebody)
        :user:
            the name of a user - optional, will be used for logging info

    See :ref:`TestScans.test_delete`
    """
    scan = request._dbentity['scan']
    user = get_user(request)
    delete_scan(context=request, scan=scan, user=user)
    return {'success': True}


def delete_scan(context, scan, user, ping_pagebrowser=True, update_archivefile=True):
    """Delete a scan and shift subsequent scans to avoid holes

    set 'ping_pagebrowser' to false if you have many scans to delete

    if update_archivefile is False, then the archivefile info is not updated (this is for optimizatoin when deleting many scans)

    scan is a Scan instance
    """
    # delete the files and the scan from the database
    scan.delete_files()
    db = context.db

    #
    # all scans that have higher seuqencenumbeers than the deleted scan
    # have to be moved one down the line
    #
    cond = Scan.sequenceNumber > scan.sequenceNumber
    cond &= get_archivefile_condition(scan)
    to_renumber = db.query(Scan).filter(cond)
    # run the query before we actully update
    to_renumber_all = to_renumber.all()
    to_renumber.update({Scan.sequenceNumber: Scan.sequenceNumber - 1})
    db.delete(scan)

    context.solr_scan.delete_by_key(scan.number)
    # TODO: optimization: next line is expensive..
    context.solr_scan.update([el.get_solr_data() for el in to_renumber_all])

    # delete the archivefile if it has no further references, and if it is not in the db
    if update_archivefile:
        archivefile = cast_scan_as_archivefile(context, scan.get_solr_data()).get_solr_data(context)
        archivefile['id'] = archivefile['archivefile_id']
        archivefile['number_of_scans'] = archivefile['number_of_scans'] - 1
        archivefile_deleted = delete_orphaned_archivefile(context, archivefile, check_for_db_record=False)
        if not archivefile_deleted:
            #
            # if we did not delete the archive file, we need to update the index
            #
            context.solr_archivefile.update([archivefile])
            component = cast_archivefile_as_component(context, archivefile)
            if component:
                context.solr_eadcomponent.update([component])

    log_events(db, user, [{
        'message': 'delete', 'object_id': scan.number, 'object_type': 'scan'
    }])

    if ping_pagebrowser and not archivefile_deleted:
        for ead_id in archivefile['ead_ids']:
            pagebrowser.update.refresh_book(context, ead_id=ead_id, archivefile_id=archivefile['archivefile_id'])

no_status0_update = no_status0_factory('update', 'scan')


def good_POST_data(request):
    "Check that the request has good POST data"
    if type(request.POST) is NoVars:
        request.errors.add('postdata', ERRORS.invalid_parameter.name, request.POST.reason)


@service_scan_item.put(
    validators=[
        lock_table_scan,
        validate_scanpresence,
        valid_scan_data,
        valid_scan_file,
        no_status0_update,
        good_POST_data,
    ],
    permission='write',
)
def update_scan_endpoint(request):
    """
    Update data for this scan

        parameters:
            The parameters are the same as those of scan creation

    See :ref:`TestScans.test_update_image`,
    :ref:`TestScans.test_update_status`,
    :ref:`TestScans.test_update_archive_id_moves_scanNumber`
    :ref:`TestLogs.test_updating_scan_logs_all_modified_scans`
    """
    logging.debug('start PUT scan request')
    data = prepare_data(request)
    scan = request._dbentity['scan']
    fileobj = request.POST.get('file')
    filecontents = None
    filename = None
    if fileobj is not None:  # fileobj evaluates to False, so no Boolean test
        filecontents = fileobj.file.read()
    user = get_user(request)
    update_scan(request, scan, data, filecontents, filename, user)
    result = scan.to_dict(request, include_images=True)
    logging.debug('End PUT scan request')
    return result


@service_scan_item.post(
    validators=[
        lock_table_scan,
        validate_scanpresence,
        valid_scan_data,
        valid_scan_file,
        no_status0_update,
        good_POST_data,
    ],
    permission='write',
)
def update_scan_endpoint_post(request):
    """This does the samea as the PUT action :ref:`service_scan_item_put`

    (implemented for convenience)
    """
    return update_scan_endpoint(request)


def update_scan(context, scan, data, filecontents, filename, user=None):
    """
    - update solr data of scan
    - update solr data of archivefile
    - update solr data of eadcomponent
    - add log entry
    """
    db = context.db
    old_archivefile = dict([(field, getattr(scan, field)) for field in ARCHIVE_IDS])

    sa_old_condition = get_archivefile_condition(scan)

    for key in data:
        setattr(scan, key, data[key])

    scan.last_modified = now()

    #  we do a partial update for optimization
    scan_solr_data = scan.get_solr_data(partial_update_keys=data.keys())
    context.solr_scan.update([scan_solr_data])
    # context.solr.commit(soft_commit=OPTIMIZATION_SOFT_COMMIT)

    new_archivefile = dict([(field, getattr(scan, field)) for field in ARCHIVE_IDS])
    if old_archivefile != new_archivefile:
        # we changed the archiveFile to which the scan belongs
        # and so we need to move a lot of stuff around
        sa_new_condition = get_archivefile_condition(scan)

        old_sequenceNumber = scan.sequenceNumber
        # We must update sequenceNumbers. First null current scan and flush
        # scan.sequenceNumber = None
        # db.flush()
        query = sqlalchemy.func.max(Scan.sequenceNumber)
        highest_number = db.query(query).filter(sa_new_condition).one()[0] or 0
        scan.sequenceNumber = highest_number + 1

        # Now patch the hole in the old scan collection
        logging.debug('updating sequence numbers')
        to_decrease = sa_old_condition & (Scan.sequenceNumber > old_sequenceNumber)

        elements = db.query(Scan).filter(to_decrease)
        materialized_elements = elements.all()

        elements.update({Scan.sequenceNumber: Scan.sequenceNumber - 1})
        logging.debug('done')

        # now the database is updated, we update solr
        logging.debug('updating solr data')
        # materialized_elements = elements
        materialized_elements += [scan]
        solr_objects = [{'number': el.number, 'sequenceNumber': {'set': el.sequenceNumber}} for el in materialized_elements]
        context.solr_scan.update(solr_objects)
        logging.debug('done')

        # since we changed the archive file, we also need to update the scan counts in the
        # corresponding components
        old_components = search_components(context=context, with_facets=False, limit=1, **old_archivefile)['results']
        if old_components:
            old_component = old_components[0]
            context.solr_eadcomponent.update(
                [{
                    'eadcomponent_id': old_component['eadcomponent_id'],
                    'number_of_scans': {'set': old_component['number_of_scans'] - 1}
                }]
            )

        new_components = search_components(context=context, with_facets=False, limit=1, **new_archivefile)['results']
        if new_components:
            new_component = new_components[0]
            context.solr_eadcomponent.update(
                [{
                    'eadcomponent_id': new_component['eadcomponent_id'],
                    'number_of_scans': {'set': new_component['number_of_scans'] + 1}}]
            )

        # get the complete data of the old archive file
        old_archivefile = search_archivefiles(context=context, with_facets=False, limit=1, **old_archivefile)['results'][0]
        old_archivefile['number_of_scans'] = old_archivefile['number_of_scans'] - 1

        # we need to manually set the sort_field, as this field is not stored, and therefore not returned
        old_archivefile['sort_field'] = sort_field(archive_id=old_archivefile['archive_id'], archiveFile=old_archivefile['archiveFile'])
        context.solr_archivefile.update([old_archivefile])
        # now check for the new archivefile (and add it if necessary)
        new_archivefile = cast_scan_as_archivefile(context, {'archive_id': scan.archive_id, 'archiveFile': scan.archiveFile}).get_solr_data(context)
        context.solr_archivefile.update([new_archivefile])

    if filecontents:
        # erase other images
        for image in scan.images:
            scan.remove_file(image.id)
            context.db.delete(image)
        context.db.refresh(scan)
        image = ScanImage(filename=filename, scan_number=scan.number, is_default=True)
        scan.images.append(image)
        context.db.flush()
        scan.store_file(filecontents, image.id)

    #
    # we need to ping the pagebrowser that the archivefile has changed
    #
    archivefiles = [ArchiveFile(**old_archivefile)]
    if old_archivefile != new_archivefile:
        archivefiles.append(ArchiveFile(**new_archivefile))

    for archivefile in archivefiles:
        for ead_id in archivefile.get_ead_ids(context):
            pagebrowser.update.refresh_book(context, ead_id=ead_id, archivefile_id=archivefile.create_archivefile_id())


def get_scan_condition(request):
    "Extracts from the requests a SqlAlchemy condition to find a scan"
    cond = Scan.number == request.matchdict['number']
    return cond


def get_archivefile_condition(scan):
    "Extracts condition to find all scans in an archivefile"
    conds = [getattr(Scan, field) == getattr(scan, field) for field in ARCHIVE_IDS]
    return reduce(operator.and_, conds)


def valid_size(request):
    size = request.GET.get('size')
    if size:
        if size in ['0', '0x', 'x0', '0x0']:
            request.errors.add(
                'querystring', ERRORS.invalid_parameter.name,
                'Invalid size. Valid values can be 100x100, 100x or x200')
        elif re.match('([0-9]*)x([0-9]*)$', size) and size != 'x':
            pass
        elif re.match('[0-9]+$', size):
            pass
        else:
            request.errors.add(
                'querystring', ERRORS.invalid_parameter.name,
                'Invalid size. Valid values can be 100x100, 100x or x200')


service_move_scan = Service(
    name='move_scan',
    path=SERVICE_SCAN_ITEM + '/move',
    description="Move the scan",
)


def after_is_required(request):
    if 'after' not in request.POST:
        request.errors.add('postdata', ERRORS.missing_parameter.name,
                           'Parameter after is required')
        return


def after_is_integer(request):
    if 'after' not in request.POST:
        return
    if not request.POST['after'].isdigit():
        request.errors.add('postdata', ERRORS.invalid_parameter.name,
                           'Parameter after must be integer')
        return
    request.validated['after'] = int(request.POST['after'])


def after_is_in_range(request):
    if 'after' not in request.validated:
        return
    query = sqlalchemy.func.max(Scan.sequenceNumber)
    cond = get_archivefile_condition(request._dbentity['scan'])
    end = int(request.POST['after'])
    highest_number = request.db.query(query).filter(cond).one()[0]
    if end > highest_number or end < 0:
        request.errors.add(
            'querystring', ERRORS.missing_parameter.name,
            'after must point to an existing scan or 0')


@service_move_scan.post(
    validators=[
        lock_table_scan,
        validate_scanpresence,
        after_is_required,
        after_is_integer,
        after_is_in_range,
    ],
    permission='write'
)
def move_scan_post(request):
    """
    Change scan position.

    parameters:
        :after: put this scan after the scan with sequenceNumber :after:

    to move this scan to the first place :after: must be 0
    (the first scan has sequenceNumber 1).

    See :ref:`TestScans.test_move_scan_forward` and :ref:`TestScans.test_move_scan_backward`.
    """
    scan = request._dbentity['scan']
    move_from_number = scan.sequenceNumber
    move_from = move_from_number - 1  # move_from is the INDEX
    move_to = request.validated['after']

    # low and high are (included) indices  (not sequence numbers)
    # of scans to update
    if move_to == move_from:
        # we don't need to do anything
        return
    elif move_from < move_to:
        # we move a scan forwards
        # so we move all elements that bweteen our scan (with index move_from)
        # up to and including the skin with index at move_to -1
        # 1 step backwards
        low_number = move_from + 1
        high_number = move_to
        inc = -1
    else:  # move_from > move_to
        # we need to move all scans with numbers that
        # come after the position we move to
        # and before the number of the scan we are moving from
        low_number = move_to + 1
        high_number = move_from_number
        inc = 1

    # get the elements we need to change
    cond = Scan.sequenceNumber <= high_number
    cond &= Scan.sequenceNumber >= low_number
    cond &= get_archivefile_condition(scan)
    elements = request.db.query(Scan).filter(cond)
    materialized_elements = elements.all()

    # log events
    base_event_to_log = {'object_type': 'scan', 'message': 'move'}
    user = get_user(request)
    events_to_log = []
    for el in materialized_elements:
        events_to_log.append(dict(base_event_to_log, object_id=el.number))
    log_events(request.db, user, events_to_log)

    # update the elements in the range between move_to and move_from
    elements.update({Scan.sequenceNumber: Scan.sequenceNumber + inc})

    # finally, we update our own scan number as well
    if move_from < move_to:
        # we move the scan forwards, so the new sequence
        scan.sequenceNumber = move_to
    else:
        scan.sequenceNumber = move_to + 1

    # Update solr documents as well
    elements_to_update = elements.all() + [scan]
    documents = [
        {
            'number': el.number,
            'sequenceNumber': {"set": el.sequenceNumber},
        } for el in elements_to_update]

    request.solr_scan.update(documents)

    archivefile = get_archivefile(request, archiveFile=scan.archiveFile, archive_id=scan.archive_id)

    for ead_id in archivefile['ead_ids']:
        pagebrowser.update.refresh_book(request, ead_id=ead_id, archivefile_id=archivefile['id'])


service_scan_images_collection = Service(
    name='service_scan_images_collection',
    path=SERVICE_SCAN_IMAGES_COLLECTION,
    description="Images connected with a scan",
    validators=[validate_scanpresence],
)


@service_scan_images_collection.get()
def get_scan_images(request):
    """Returns a list of all images pertaining to this scan"""
    scan = request._dbentity['scan']
    scan_number = request._dbentity['scan'].number
    scandict = request.solr.search(q='id:scan=%s' % scan_number).documents[0]
    images = [dict(image) for image in scan.images]
    for image in images:
        url = request.route_url('service_scan_images_item',
                                number=scan.number,
                                number_of_image=image['id'])
        image_url = os.path.join(url, 'file_%s' % str(hash(scandict['dateLastModified'])))
        image['URL'] = url
        image['image_url'] = image_url

    return {
        'results': sorted(images, key=lambda im: (not im['is_default'], im['id'])),
        'total_results': len(images)
    }


def valid_scan_images_collection_data(request):
    to_validate = dict(request.POST)
    if 'file' in to_validate:
        del to_validate['file']
    validate_schema(ImageCollectionPost(), to_validate, request)


@service_scan_images_collection.post(validators=[valid_scan_file, valid_scan_images_collection_data])
def add_scan_image(request):
    """Add one or more images to the collection

        * **file:**
            the file binary data; if repeated many images will be created

        * **is_default:**
            if set to non-empty, non-zero string
            this will become the default image.
            If many images are passed in the file parameters,
            the first will be the default one.
    """
    is_default = request.validated['is_default']
    scan = request._dbentity['scan']
    scan.last_modified = now()

    if is_default:
        for image in scan.images:
            image.is_default = False
    added_images = add_files_from_request(request, scan, is_default=is_default)

    # TOOD: next line can be optimized (using partial_update_keys)
    request.solr_scan.update([scan.get_solr_data()])

    user = get_user(request)
    for image in added_images:
        log_events(request.db, user, [{'message': 'create', 'object_id': image.id, 'object_type': 'image'}])

    return {'success': True, 'results': [dict(image) for image in added_images]}


service_default_scan_image = Service(
    name='service_default_scan_image',
    path=SERVICE_SCAN_ITEM_DEFAULT_IMAGE,
    description="Get the image for this scan that that has 'is_default' set to True",
    validators=(validate_scanpresence,)
)


@service_default_scan_image.get(renderer=file_null_renderer, validators=[valid_size], filters=[set_cors])
def get_default_scan_image(request):
    """return the default scan image.

    For parameters, see [TODO]
    """
    scan = request._dbentity['scan']
    size = request.GET.get('size')
    default_id = scan.images[0].id
    path = get_scan_image(scan=scan, id=default_id, size=size)
    response = FileResponse(path, request=request, content_type=get_filetype(path))
    response.headers.update(image_headers(scan, request))
    return response


def image_headers(scan, request):
    headers = {
        "Cache-Control": "max-age=604800, public",
    }
    headers.update({'Content-Type': 'image/jpeg'})
    archive_data = scan.get_archive_data()
    scan_data = scan.to_dict(request)
    if not scan_data.get('folioNumber', None):
        scan_data['folioNumber'] = scan_data.get('sequenceNumber')

    filename = '{archive_data[institution]}_{archive_data[archive]}_{scan_data[archiveFile]}_{scan_data[folioNumber]}'.format(archive_data=archive_data, scan_data=scan_data)
    headers.update({'Content-Disposition': 'attachment; filename="{filename}.jpg"'.format(filename=filename)})

    return headers


def validate_imagepresence(request):
    ".\n\n\nnumber_of_image must be an integer\n\n\n."
    if not request.matchdict['number_of_image'].isdigit():
        request.errors.add('url', ERRORS.invalid_parameter.name, 'number_of_image must be integer')
        return
    try:
        image_id = int(request.matchdict['number_of_image'])
        number = int(request.matchdict['number'])
        request._dbentity['scanimage'] = request.db.query(ScanImage).filter(
            (ScanImage.id == image_id) & (ScanImage.scan_number == number)
        ).one()
    except sqlalchemy.orm.exc.NoResultFound:
        response = {'errors': [{'location': 'url', 'name': 'number_of_image'}]}
        headers = (['Content-Type', 'application/json; charset=UTF-8'],)
        raise HTTPNotFound(body=json.dumps(response), headers=headers)


service_scan_images_item = Service(
    name='service_scan_images_item',
    path=SERVICE_SCAN_IMAGES_ITEM,
    description="Image connected with a scan",
    validators=[validate_scanpresence, validate_imagepresence],)


@service_scan_images_item.get()
def get_scan_image_item(request):
    """
    return information about this image


    See :ref:`TestScanImages.test_get_image`
    """
    db_entity = request._dbentity['scanimage']
    res = dict(db_entity)
    del res['scan_number']
    scan = db_entity.scan
    scan_number = scan.number
    scandict = request.solr.search(q='id:scan=%s' % scan_number).documents[0]
    url = request.route_url('service_scan_images_item', number=scandict['number'], number_of_image=res['id'])
    image_url = os.path.join(url, 'file_%s' % str(hash(scandict['dateLastModified'])))
    res['image_url'] = image_url
    res['URL'] = url
    return res


service_scan_images_item_raw = Service(
    name='service_scan_images_item_raw',
    path=SERVICE_SCAN_IMAGES_ITEM_RAW,
    description="Get raw image",
    validators=[validate_scanpresence, validate_imagepresence],
)


@service_scan_images_item_raw.get(renderer=file_null_renderer, validators=[valid_size], filters=[set_cors])
def get_scan_image_item_raw(request):

    """
    See :ref:`TestScans.test_scan_get_data`

        * **size:**
            a string determining either width and height of the image,
            or both. For example,  “200x300” or “120x” or “x400” are
            valid arguments.
            The returned image is resized to fall within the specified
            parameters (so “x400” returns an image 400px high).

    for example, ``%(SERVICE_SCAN_ITEM)s/image?size=120x120``
    retrieves a thumbnail-size image.
    """
    scan = request._dbentity['scan']
    size = request.GET.get('size')
    image_id = request._dbentity['scanimage'].id

    path = get_scan_image(scan=scan, id=image_id, size=size)
    response = FileResponse(path, request=request, content_type=get_filetype(path))
    response.headers.update(image_headers(scan, request))
    return response


def not_last_image(request):
    image = request._dbentity['scanimage']
    if len(image.scan.images) < 2:
        request.errors.add('url', ERRORS.cant_delete_last_scan_image.name,
            "Image %i is the last one of scan %i: it can't be deleted" % (image.id, image.scan.number))


@service_scan_images_item.delete(validators=[not_last_image], permission='write')
def delete_scan_image(request):
    """
    Delete this image.

    if successfull, returns {"success": "True"}
    """
    image = request._dbentity['scanimage']
    if image.is_default:
        for candidate in image.scan.images:
            if candidate.id != image.id:
                candidate.is_default = True
    scan = image.scan
    scan.last_modified = now()

    db = request.db
    image_id = image.id
    scan.delete_files_for_image(image_id)
    db.delete(image)
    db.flush()
    db.refresh(scan)
    # TOOD: next line can be optimized (using partial_update_keys)
    scan_solr_data = scan.get_solr_data()
    request.solr_scan.update([scan_solr_data])
    # TOOD: next line can be optimized (using partial_update_keys)
    archivefile = cast_scan_as_archivefile(request, scan_solr_data).get_solr_data(request)
    archivefile['id'] = archivefile['archivefile_id']
    request.solr_archivefile.update([archivefile])

    # delete the archive file if it remains orphaned
    delete_orphaned_archivefile(request, archivefile, check_for_db_record=False)

    user = get_user(request)
    log_events(request.db, user, [{'message': 'delete', 'object_id': image_id, 'object_type': 'image'}])

    return {"success": "True"}


@service_scan_images_item.put(validators=[valid_scan_file, valid_scan_images_collection_data])
def put_scan_image_item(request):
    """
    Change this image

    * **file: optional**

    * **is_default:**
        optional
        if this is True, then the current image will become the default image.

    """
    is_default = request.validated['is_default']
    scan = request._dbentity['scan']
    scanimage = request._dbentity['scanimage']
    if is_default:
        for image in scan.images:
            image.is_default = False
        scanimage.is_default = True

    if 'file' in request.POST:
        scan.delete_files_for_image(scanimage.id)
        scanimage.filename = request.POST['file'].filename
        scan.store_file(request.POST['file'].file.read(), scanimage.id)

    # updae the last_modified date of the scan
    scan.last_modified = now()

    # TOOD: next line can be optimized (using partial_update_keys)
    request.solr_scan.update([scan.get_solr_data()])

    user = get_user(request)
    log_events(request.db, user, [{'message': 'update', 'object_id': scan.number, 'object_type': 'scan'}])
    log_events(request.db, user, [{'message': 'update', 'object_id': scanimage.id, 'object_type': 'image'}])

    return {'success': True, 'image': dict(scanimage)}


@service_scan_images_item.post(validators=[valid_scan_file, valid_scan_images_collection_data])
def put_scan_image_item_post(request):
    """same as PUT action at :ref:`service_scan_images_item_put`

    (impemented for convenience)
    """
    return put_scan_image_item(request)


def get_scan_image(scan, id=None, size=None):  # @ReservedAssignment
    """
    Get the image determined by 'id' belonging to scan

    returns a path to the images

    if id=None or is not provided, return the default image
    if size=None, return the original size
    """
    try:
        path = scan.get_real_thumbnail_path(size=size, image_id=id)
    except IOError as error:
        raise HTTPNotFound(body=unicode(error))
    return path


# Auto-update docstring
update_docstrings(locals())
