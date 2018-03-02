import colander
from utils import el


class ScanSchema(colander.MappingSchema):
    number = el('int')
    archive_id = el('int', required=True)
    archiveFile = el('string', required=True)
    date = el('datetime')
    folioNumber = el('string')
    originalFolioNumber = el('string')
    language = el('string')
    sequenceNumber = el('int')
    subjectEN = el('string')
    title = el('string')
    timeFrameFrom = el('date')
    timeFrameTo = el('date')
    transcription = el('string')
    transcriptionAuthor = el('string')
    transcriptionDate = el('date')
    translationEN = el('string')
    translationENDate = el('date')
    translationENAuthor = el('string')
    translationID = el('string')
    translationIDAuthor = el('string')
    translationIDDate = el('date')
    type = el('string')
    URL = el('string')
    URI = el('string')
    relation = el('string')
    source = el('string')
    creator = el('string')
    format = el('string')
    contributor = el('string')
    publisher = el('string')
    rights = el('string')
    user = el('string')
    status = colander.SchemaNode(
        colander.Int(),
        validator=colander.OneOf([0, 1, 2]),
        missing=1, default=1)


DEFAULT_ORDER_BY = 'archive_id,archiveFile,sequenceNumber'


class SearchSchema(colander.MappingSchema):
    # schema for seearch parameters in GET scan collection
    country = el('string')
    institution = el('string')
    archive = el('string')
    archive_id = el('int')
    archiveFile = el('string')
    archiveFile_raw = el('string')
    date = el('date')
    timeFrame = el('date')
    timeFrames = el('list_of_dates')
    folioNumber = el('string')
    folioNumbers = el('string')
    originalFolioNumber = el('string')
    start = el('int', default=0)
    limit = el('int', default=1000)
    status = el('int')

    order_by = el('string', default=DEFAULT_ORDER_BY, missing=DEFAULT_ORDER_BY)
    order_dir = colander.SchemaNode(colander.String(),
        validator=colander.OneOf(['ASC', 'DESC']),
        missing='ASC', default='ASC')


class ImageCollectionPost(colander.MappingSchema):
    is_default = el('boolean', missing=False)
    user = el('string')


class CollectionImagesDeleteSchema(colander.MappingSchema):
    archiveFile = el('string', required=True)
    archive_id = el('int', required=True)
    user = el('string')
