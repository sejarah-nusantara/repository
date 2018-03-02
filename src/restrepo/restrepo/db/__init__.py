#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


from pyramid.request import Request
from pyramid.decorator import reify
from pyramid_tm import default_commit_veto
from restrepo.db.solr import Solr, SolrWrapper
from sqlalchemy.orm import scoped_session
from sqlalchemy import MetaData, types
from pytz import UTC
import logging
from ..config import OPTIMIZATION_SOFT_COMMIT


class UTCDateTime(types.TypeDecorator):
    impl = types.DateTime

    def process_bind_param(self, value, engine):
        return value

    def process_result_value(self, value, engine):
        "Ensure no naive datetime comes out of the db"
        if not value or value.tzinfo:
            return value
        return UTC.localize(value)


class DbRequest(Request):
    def __init__(self, *args, **kwargs):
        super(DbRequest, self).__init__(*args, **kwargs)
        self._dbentity = {}

    def route_url(self, *args, **kwargs):
        return Request.route_url(self, *args, **kwargs)

    @reify
    def db(self):
        return scoped_session(self.registry.settings['db.session'])

    @reify
    def solr(self):
        return Solr(self.registry.settings['solr.url'] + 'entity')

    @reify
    def solr_scan(self):
        return SolrWrapper(self.solr, 'scan', 'number')

    @reify
    def solr_ead(self):
        return SolrWrapper(self.solr, 'ead', 'ead_id')

    @reify
    def solr_eadcomponent(self):
        return SolrWrapper(self.solr, 'eadcomponent', 'eadcomponent_id')

    @reify
    def solr_archivefile(self):
        return SolrWrapper(self.solr, 'archivefile', 'archivefile_id')


def commit_veto(request, response):
    # The default vetoes on response status != 2xx
    vetoed = default_commit_veto(request, response)
    if not vetoed and request.method in ('GET', 'POST', 'PUT', 'DELETE'):
        # we abuse the commit_veto call (called at the end of each request by
        # the pyramid transaction manager)
        # to also commit to solr
        request.solr.commit(soft_commit=OPTIMIZATION_SOFT_COMMIT)
    return vetoed


metadata = MetaData()

# metadata should be already instantiated when we import
# Those imports make it possible to import like this:
# from restrepo.db import EadFile
from ead import EadFile
from scans import Scan
from log import LogAction, LogObject
from settings import Settings  # need this here otherwise tests wont create the table
from archive import Archive
from scan_images import ScanImage
from archivefile import ArchiveFile

# We do the mapping part here to avoid circular imports
from scans import scan as scan_table
from scan_images import scan_image as scan_image_table
from archivefile import archivefile as archivefile_table
from sqlalchemy.orm import relationship, mapper

mapper(ScanImage, scan_image_table)
mapper(Scan, scan_table, properties={
    'images': relationship(
        ScanImage,
        backref='scan',
        order_by=(ScanImage.is_default.desc(), ScanImage.id)
    )
})

mapper(ArchiveFile, archivefile_table)
