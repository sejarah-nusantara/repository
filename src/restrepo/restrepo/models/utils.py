import colander
from pytz import UTC


class DatesSchema(colander.SequenceSchema):
    date = colander.SchemaNode(colander.Date())


MAKER = {
    'string': colander.String,
    'int': colander.Int,
    'date': colander.Date,
    'datetime': colander.DateTime,
    'boolean': colander.Boolean,
    'list': colander.Sequence,
    'list_of_dates': DatesSchema,
}


def el(type, **kwargs):
    """
    We place defaults here. Type is a string among
    'integer', 'string', 'date', 'datetime'
    """
    myargs = dict(missing=None)
    myargs.update(kwargs)
    if 'default' in kwargs:
        myargs['missing'] = kwargs['default']
    if myargs.get('required', False):
        del myargs['required']
        del myargs['missing']
    if type == 'datetime':
        myargs['default_tzinfo'] = UTC
    if type == 'list_of_dates':
        return DatesSchema(**myargs)
    else:
        return colander.SchemaNode(MAKER[type](), **myargs)


class MyDateTime(colander.DateTime):
    """
    A custom serializer/deserializer that converts datetimes
    to local timezone.
    """
    def deserialize(self, node, cstruct):
        value = super(MyDateTime, self).deserialize(node, cstruct)
        if not value:
            return value
        return value.astimezone(UTC)


MAKER['datetime'] = MyDateTime
