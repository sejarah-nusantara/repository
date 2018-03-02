import colander
from utils import el


class SearchSchema(colander.MappingSchema):
    user = el('string')
    date_from = el('datetime')
    date_to = el('datetime')
    object_id = el('string')
    object_type = el('string', validator=colander.OneOf(['scan', 'ead']))
    message = el('string', validator=colander.OneOf(
        ["create", "update", "move", "delete"]))
    start = el('int', default=0)
    limit = el('int', default=1000)
    order_by = el('string', default='date', missing='date')
    order_dir = colander.SchemaNode(colander.String(),
        validator=colander.OneOf(['ASC', 'DESC']),
        missing='ASC', default='ASC')
