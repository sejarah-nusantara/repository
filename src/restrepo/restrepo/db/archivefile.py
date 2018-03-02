# - coding: utf-8 -
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


import json
from sqlalchemy import Table, Column, Unicode, Integer, String
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import NoResultFound
from restrepo.config import status as status_values
from restrepo.db import metadata
from restrepo.db.archive import get_archive
from restrepo.db.archive import get_archives
from restrepo.db.mixins import JsonSaver, DictAble
from restrepo.db.solr import build_equality_query
from restrepo.db.solr import solr_escape
from restrepo import config

archivefile = Table(
    'archivefile',
    metadata,
    Column('number', Integer, primary_key=True),
    Column('archive_id', Integer, index=True),
    Column('archiveFile', Unicode(255), index=True),
    Column('status', Integer, default=status_values.PUBLISHED),
    # HACK alert - this was NOT a good idea - and if we have a way to remove this, lets
    Column('json_data', String),
)


class ArchiveFile(JsonSaver, DictAble):

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def to_dict(self, request=None, dbdata_only=False):
        """
        Return a JSON-serializable dict representing this object.
        A request object is needed unless dbdata_only is True.
        """
        me = dict(self)
        del me['json_data']
        if not dbdata_only:
            me['URL'] = request.route_url('service_archive_item', **me)
        if self.json_data:
            me.update(json.loads(self.json_data))
        return me

    def get_solr_data(self, context):
        """the data that will be indexed by solr"""
        d = dict(
            archivefile_id=self.create_archivefile_id(),
            archive_id=self.archive_id,
            archiveFile=self.archiveFile,
            status=self.get_status(),
            number_of_scans=self.get_number_of_scans(context),
            ead_ids=self.get_ead_ids(context),
            title=self.get_title(context),
            titles=unicode(self.get_titles(context)),
            sort_field=self.get_sort_field(),
        )
        return d

    def create_archivefile_id(self):
        """create an id for an archive file in teh solr index"""
        d = dict(self)
        return '%s/%s' % (d['archive_id'], d['archiveFile'])

    def get_status(self):
        if self.status is not None:
            return self.status
        else:
            return config.DEFAULT_ARCHIVEFILE_STATUS

    def get_solr_text(self):
        "Put together some text for solr fulltext search (TODO)"
        # TODO: implement get_solr_text for searching in text of scans
        # use the SOLR index 'search_source' for this (just as ead_components do)
        return ''

    def get_title(self, context):
        if getattr(self, 'title', None):
            return self.title
        else:
            # return the first title we happen to find
            titles = self.get_titles(context)
            return titles and titles.values()[0] or None

    def get_titles(self, context):
        q = 'archiveFile:%s AND archive_id:%s' % (solr_escape(self.archiveFile), solr_escape(self.archive_id))
        components = context.solr_eadcomponent.search(q=q).documents
        if components:
            return {c.get('language', ''): c.get('title', '') for c in components}
        else:
            return {}

    def get_institution(self):
        "get institution from the archive linked to this scan"
        archive = self.get_archive_data()
        return archive['institution']

    def get_archive(self):
        "get archive from the archive linked to this scan"
        return self.get_archive_data()['archive']

    def get_archive_data(self):
        "get archive info linked to this scan"
        db = object_session(self)
        archive = get_archive(Context(db), archive_id=self.archive_id)
        if archive:
            return archive.to_dict()

    def get_number_of_scans(self, context):
        """return number of scans for this archive file that are currently present in the index"""
        solr_query = build_equality_query(
            archiveFile=self.archiveFile,
            archive_id=self.archive_id,
        )
        result = context.solr_scan.search(q=solr_query, rows=1)
        return result.total_results

    def get_ead_ids(self, context):
        """return ead_ids in which this archivefile occurs"""
        if self.archive_id:
            solr_query = build_equality_query(
                archive_id=self.archive_id,
            )
            result = context.solr_ead.search(q=solr_query)
            return [x['ead_id'] for x in result.documents]
        else:
            return []

    def get_sort_field(self):
        archive_id = self.archive_id
        archiveFile = self.archiveFile
        return sort_field(archive_id, archiveFile)


def sort_field(archive_id, archiveFile):
    if archiveFile.isdigit():
        archiveFile = archiveFile.zfill(10)
    return '{archive_id}/{archiveFile}'.format(archive_id=archive_id, archiveFile=archiveFile)


class Context:
    def __init__(self, db):
        self.db = db


def get_archivefiles(context, **kwargs):
    return get_archivefiles_query(context, **kwargs).all()


def get_archivefile(context, **kwargs):
    try:
        return get_archivefiles_query(context, **kwargs).one()
    except NoResultFound:
        return None


def get_archivefiles_query(
    context,
    archive_id=None,
    archiveFile=None,
    order_by=None,
    order_dir=None,
    archive=None,
    institution=None,
    status=None,
):
    """returns a database query

    order by is a list of column names.
    If prefixed with a '-', we sort descending
    using order_dir is deprecated

    """
    db = context.db

    condition = (ArchiveFile.status != status_values.DELETED)

    if archive_id:
        condition = (ArchiveFile.archive_id == archive_id) & condition
    if archiveFile:
        condition = (ArchiveFile.archiveFile == archiveFile) & condition

    if archive and institution:
        archives = get_archives(archive=archive, institution=institution)
    elif archive:
        archives = get_archives(archive=archive)
    elif institution:
        archives = get_archives(institution=institution)
    else:
        archives = None

    if archives is not None:
        archive_ids = [archive.id for archive in archives]
        condition &= (ArchiveFile.archive_id.in_(archive_ids))

    if status:
        condition &= (ArchiveFile.status == status)

    query = db.query(ArchiveFile).filter(condition)
    if order_by:
        for col_name in order_by:
            desc = False
            if col_name.startswith('-'):
                col_name = col_name[1:]
                desc = True
            order_by_clause = getattr(ArchiveFile, col_name)
            if order_dir == 'DESC' or desc:
                order_by_clause = order_by_clause.desc()
            query = query.order_by(order_by_clause)

    return query
