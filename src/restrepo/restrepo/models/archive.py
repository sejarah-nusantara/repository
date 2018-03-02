import colander
from utils import el


class ArchiveSchema(colander.MappingSchema):
    archive = el('string')
    archive_description = el('string')
    country_code = el('string')
    institution = el('string')
    institution_description = el('string')
