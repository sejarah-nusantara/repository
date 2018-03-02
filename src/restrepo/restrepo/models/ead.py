import colander
from utils import el


class EadSchema(colander.MappingSchema):
    user = el('string')
    status = colander.SchemaNode(colander.Int(),
        validator=colander.OneOf([0, 1, 2]),
        missing=1, default=1)


class EadSearchSchema(colander.MappingSchema):
    archive = el('string')
    archive_id = el('string')
    country = el('string')
    findingaid = el('string')
    institution = el('string')
    language = el('string')
