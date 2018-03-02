import colander
from utils import el


class ComponentSearchSchema(colander.MappingSchema):
    archive = el('string')
    archiveFile = el('string')
    archive_id = el('int')
    contains_text = el('string')
    country = el('string')
    date_from = el('date')
    date_to = el('date')
    ead_id = el('string')
    findingaid = el('string')
    institution = el('string')
    is_archiveFile = el('boolean')
    is_component = el('boolean')
    language = el('string')
    limit = el('int', default=1000)
    order_by = el('string')
    start = el('int', default=0)
    xpath = el('string')


class ComponentTreeSearchSchema(colander.MappingSchema):
    ead_id = el('string', required=True)
    # is_component has default True mostly for reasons of backwards compatility
    is_component = el('boolean', default=True)
    prune = el('boolean', default=True)


class GetComponentForViewerSchema(colander.MappingSchema):
    ead_id = el('string', required=True)
    xpath = el('string', required=False)
    archiveFile = el('string', required=False)
    show_in_tree = el('boolean')
