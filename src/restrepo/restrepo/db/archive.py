from sqlalchemy import Table, Column, Integer, Text
from sqlalchemy.orm import mapper
from restrepo.db import metadata
from restrepo.db.mixins import DictAble
# from restrepo.config import SERVICE_ARCHIVE_ITEM

archive_table = Table('archive', metadata,
    Column('id', Integer, primary_key=True),
    Column('country_code', Text, index=True),
    Column('institution', Text, index=True),
    Column('institution_description', Text, index=True),
    Column('archive', Text, index=True),
    Column('archive_description', Text, index=True),
)


class Archive(DictAble):
    "An Archive from an EAD file"

    def to_dict(self, request=None):
        d = dict(self)
        if request:
            d['URL'] = request.route_url('archive', archive_id=self.id)
        return d


mapper(Archive, archive_table)


def get_archives(
    context,
    institution=None,
    archive=None,
    country=None,
    archive_id=None,
):
    query = context.db.query(Archive)
    if institution:
        query = query.filter(Archive.institution == institution)
    if archive:
        query = query.filter(Archive.archive == archive)
    if country:
        query = query.filter(Archive.country_code == country)
    if archive_id:
        query = query.filter(Archive.id == archive_id)
    return query.order_by(Archive.id).all()


def get_archive(
    context,
    institution=None,
    archive=None,
    archive_id=None,
):
    if archive_id:
        archives = get_archives(context, archive_id=archive_id)
    else:
        archives = get_archives(context, institution=institution, archive=archive)
    params = "with institution='%s' and archive='%s'" % (institution, archive)
    if not archives:
        raise Exception('No archive found: %s' % params)
    if len(archives) > 1:
        msg = 'More than one archive found' % params
        raise Exception(msg)
    return archives[0]
