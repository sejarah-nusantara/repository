import colander
from utils import el


class ArchiveFileGetSchema(colander.MappingSchema):
    # parameters to pass to GET archiveFile
    archive_id = el('int')
    archiveFile = el('string')


class ArchiveFilePutSchema(colander.MappingSchema):
    # parameters for "PUT" archiveFile
    status = el('int')
    user = el('string')


class ArchiveFileSearchSchema(colander.MappingSchema):
    ead_id = el('string')
    archiveFile = el('string')
    archive_id = el('int')
    archivefile_id = el('string')
    has_scans = el('boolean')
    status = el('int')

    start = el('int', default=0)
    limit = el('int', default=1000)
