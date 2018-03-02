# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


""" Web services for archive files.

"""
import sqlalchemy

from cornice import Service

from .log import log_events, get_user
from restrepo.db.archivefile import ArchiveFile
from restrepo.config import SERVICE_ARCHIVEFILE_COLLECTION, SERVICE_ARCHIVEFILE_ITEM
from restrepo.config import update_docstrings
from restrepo.db.solr import solr_escape
from restrepo import db
from restrepo.indexes.archivefile import get_archivefiles, get_archivefile
from restrepo.utils import set_cors
from restrepo.browser.validation import search_archivefile_valid_parameters
from restrepo.browser.validation import archivefile_put_valid_parameters
from restrepo.browser.validation import validate_archivefile_presence
from restrepo.config import ERRORS, STATUS_PUBLISHED
from restrepo import pagebrowser


service_archivefile_collection = Service(
    name='service_archivefile_collection',
    path=SERVICE_ARCHIVEFILE_COLLECTION,
    description=__doc__)

service_archivefile_item = Service(
    name='service_archivefile_item',
    path=SERVICE_ARCHIVEFILE_ITEM,
    description="Access, update or delete data of a single archivefile",
    validators=[validate_archivefile_presence]
    )


@service_archivefile_collection.get(validators=[search_archivefile_valid_parameters], filters=[set_cors])
def get_archivefiles_service(request):
    """
    Return a list of archive files.

    parameters:

        * **archive_id:**
            return archivefiles that are refenced by the archive identified by archive_id
        * **archiveFile:**
            return archive files that have the value of archiveFile equal to this parameter
            archiveFile can be passed multiple times.
            Also, a range, of the form "[1234 TO 1340]", or "[AA TO BB]", is  valid .
        * **ead_id:**
             return archivefiles that are references by this EAD file
        * **has_scans:**
            if the value of *has_scans* is True, then return only archivefiles
            that are referenced by one or more scans
        * **status:**
            a status: a value among :ref:`status_values` (except 0)
        * **start:**
            index of the first element returned (used in pagination)
        * **limit:**
            max # of objects to return

    Queries will return a structure similar to::

        {
          "total_results": 1,
          "start": 0,
          "end": 1,
          "results": [
            {
              "status": 2,
              "archive_id": 9,
              "archiveFile": "something_unique",
              "number_of_scans": 1,
              "ead_ids": [],
              "URL": "http://localhost/archivefiles/9/something_unique",
              "id": "9/something_unique",
              "titles": {"en": "English Title"},
              "ead_ids" : ["something.ead.xml"]
            }
          ],
          "query_used": {
            "archive_id": "9"
          }
        }

    cf.  :ref:`TestArchiveFile.test_get_archivefiles_search`, :ref:`TestArchiveFile.test_get_archivefiles_paging`
    """
    total_results, results = get_archivefiles(request, **request.validated)

    return {
        'results': results,
        'query_used': dict(request.validated),
        'total_results': len(results),
        'total_results': total_results,
        'start': request.validated['start'],
        'end': request.validated['start'] + len(results)

    }


#
#  the "add" function is not requested, but we might implement it anyway for consistency
#
# @service_archivefile_collection.post(validators=[], permission='write')
# def add_archivefile(request):
#    """
#    **not implemented**
#
#    Add a new archive file.
#
#
#    parameters:
#        * **archiveFile:
#            must be NMTOKEN ([-a-z0-9A-Z]*)
#        * **status:
#            a status: a value among :ref:`status_values` (except 0)
#    """
#    #implement NMTOKEN validation
#    pass


@service_archivefile_item.get(filters=set_cors)
def get_archivefile_service(request):
    """
    Return a single object representing the requested archivefile.

    will return something similar to::

        {
            "id": "1234567",
            "archiveFile": "identifierofarchivefile",
            "archive_id": 3,
            "public": true,
            "URL": "http://localhost/archivefile/1234567",
            "ead_ids" : ["sadflk.xml", "lkasjldsafkj.xml"],
            "number_of_scans": 3
        }

    see also :ref:`datamodel_archivefile` and :ref:`TestArchiveFile.test_get_archivefile`
    """
    return request._dbentity['archivefile']


@service_archivefile_item.delete(permission='write')
def service_archivefile_item_delete_archivefile(request):
    """
    Delete this archivefile.

    An archivefile can only be deleted if it not referenced by either an EAD file or a scan

    see :ref:`TestArchiveFile.test_archivefile_deleting`
    """

    archivefile = request._dbentity['archivefile']
    data = archivefile
    if data['ead_ids']:
        request.errors.add(ERRORS.archivefile_has_eads.name, 'This archive file is referenced by the ead files: %s' % ', '.join(data['ead_ids']))
    if data['number_of_scans']:
        request.errors.add('data', ERRORS.archivefile_has_scans.name, 'This archive file is referenced by %s scans' % data['number_of_scans'])

    delete_archivefile(request, archivefile)

    if not request.errors:
        user = get_user(request)
        log_events(request.db, user, [{
            'message': 'delete', 'object_id': archivefile['id'], 'object_type': 'archivefile'
        }])
        return {'success': True}


@service_archivefile_item.put(permission='write', validators=[archivefile_put_valid_parameters])
def update_archivefile(request):
    """

    update information about this archivefile

    parameters:
        * **status:** a boolean
            a status: a value among :ref:`status_values` (except 0)
        * **user**:  a string that identifies the user responsible for the udpate
    """
    ""
    _data_changed = False

    archivefile = request._dbentity['archivefile']

    # find a database record
    qry = request.db.query(ArchiveFile)
    qry = qry.filter(ArchiveFile.archive_id == archivefile['archive_id'])
    qry = qry.filter(ArchiveFile.archiveFile == archivefile['archiveFile'])
    try:
        archivefile_db = qry.one()
    except sqlalchemy.orm.exc.NoResultFound:
        # if we do not find this archivefile in the database
        # we create a new db record
        archivefile_db = ArchiveFile()
        for key in archivefile:
            setattr(archivefile_db, key, archivefile[key])

        request.db.add(archivefile_db)
        _data_changed = True

    data = request.validated
    for k in data:
        if k in request.POST and k not in ['user']:  # only update with data that is explicitly given
            if data[k] != getattr(archivefile_db, k):
                setattr(archivefile_db, k, data[k])
                # also update the object that we are about to return
                archivefile[k] = data[k]
                _data_changed = True

    if _data_changed:
        request.db.flush()
        # update the index
        request.solr_archivefile.update([archivefile_db.get_solr_data(request)])
#         request.solr_archivefile.update([archivefile])

        if data:
            q = 'archive_id:{archive_id} AND archiveFile:{archiveFile}'.format(
                archive_id=solr_escape(archivefile['archive_id']),
                archiveFile=solr_escape(archivefile['archiveFile']),
                )

            documents = request.solr_eadcomponent.search(q=q).documents
            if documents:
                for document in documents:
                    document['status'] = data['status']
                request.solr_eadcomponent.update(documents)

        user = get_user(request)
        log_events(request.db, user, [{
            'message': 'update', 'object_id': archivefile['id'], 'object_type': 'archivefile'
        }])

        for ead_id in archivefile_db.ead_ids:
            if archivefile_db.status == STATUS_PUBLISHED:
                pagebrowser.update.refresh_book(request, ead_id=ead_id, archivefile_id=archivefile_db.id)
            else:
                pagebrowser.update.delete_book(request, ead_id=ead_id, archivefile_id=archivefile_db.id)

    return archivefile


@service_archivefile_item.post(permission='write', validators=[archivefile_put_valid_parameters])
def update_archivefile_post(request):
    """This does the same as the PUT action :ref:`service_archivefile_put`

    (implemented for convenience)
    """
    return update_archivefile(request)


def delete_archivefile(context, archivefile, check_for_db_record=False):
    """renamed to more explicit function name:"""
    return delete_orphaned_archivefile(context, archivefile, check_for_db_record)


def delete_orphaned_archivefile(context, archivefile, check_for_db_record=False):
    """Delete this archive file from the index and database, but only if it is not referenced by any ead or scan

    archivefile is a dictionary

    if check_for_db_record is True, then we don't delete anything if the archive file as a database record

    return True if succesful
    """
    data = archivefile
    if data['ead_ids']:
        # don't delete if it has eads
        return
    if data['number_of_scans']:
        # dont delete if it has scans
        return

    # we have no scans, no ead_ids. We check if we have a db record to delete

    archivefile_db = db.archivefile.get_archivefile(context, archive_id=archivefile['archive_id'], archiveFile=archivefile['archiveFile'])
    if check_for_db_record and archivefile_db:
        # we have been flagged not to delete an archivefile that is in the db, so we don't do anything
        return
    # we are ready to delete the archivefile and the index
    if archivefile_db:
        context.db.delete(archivefile_db)
        context.db.flush()
        # in theory, if the file is deleted, it does not reference any ead_ids, and therefore should already have been de-published
        # for ead_id in archivefile_db.ead_ids:
        #     pagebrowser.update.delete_book(ead_id, archivefile['archivefile_id'])

    context.solr_archivefile.delete_by_key(data['id'])

    return True


# Auto-update docstring
update_docstrings(locals())
