#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


import json
from sqlalchemy.orm import class_mapper, ColumnProperty
from restrepo.utils import datetime_to_string


class DictAble(object):
    @classmethod
    def _field_names(cls):
        return (prop.key for prop in class_mapper(cls).iterate_properties
            if isinstance(prop, ColumnProperty))

    def __iter__(self):
        "dict(scan) will give a JSON-encodable object"
        for key in self._field_names():
            value = getattr(self, key)
            value = datetime_to_string(value)
            yield (key, value)


class JsonSaver(object):
    "Save non-column values in the 'json_data' column as JSON"
    # TOOD: refactor and remove this horrendous, implicitly making stuff untransparent, object
    # Not as efficient as it should. If we would have had a newer SQLAlchemy we
    # would have used the `reconstruct_instance` hook and the like
    def _is_json_field(self, name):
        columns = class_mapper(type(self)).columns
        if name.startswith('_') or name in columns:
            return False  # Do not hijack private attribute and defined columns
        return True

    def __setattr__(self, k, v):
        if self._is_json_field(k):
            json_data = json.loads(self.json_data or '{}')
            json_data[k] = v
            super(JsonSaver, self).__setattr__(
                'json_data', json.dumps(json_data))
        super(JsonSaver, self).__setattr__(k, v)

    def __getattr__(self, k):
        if k.startswith('_'):
            return object.__getattribute__(self, k)
        if self._is_json_field(k):
            place_to_look = json.loads(self.json_data or '{}')
        else:
            place_to_look = self.__dict__
        try:
            return place_to_look[k]
        except KeyError:
            raise AttributeError
