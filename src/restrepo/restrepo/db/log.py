from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import mapper, relationship
from restrepo.db import metadata
from restrepo.db.mixins import DictAble
from datetime import datetime


log_action = Table('log_action', metadata,
    Column('id', Integer, primary_key=True),
    Column('user', String(30), index=True),
    Column('date', DateTime, index=True)
)


class LogAction(DictAble):
    "Represents a single HTTP request log"
    def __init__(self, user=None):
        self.user = user
        self.date = datetime.now()


log_object = Table('log_object', metadata,
    Column('id', Integer, primary_key=True),
    Column('log_action_id', Integer, ForeignKey('log_action.id')),
    Column('object_id', String, index=True),
    Column('object_type', String(30), index=True),
    Column('message', String(255), index=True),
)


class LogObject(DictAble):
    """
    Represents an action performed on an object.
    Possibly many objects are affected by a single query.
    """
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)


mapper(LogAction, log_action, properties={
    'entries': relationship(
        LogObject, backref='action', order_by=log_object.c.object_type
    )
})
mapper(LogObject, log_object)
