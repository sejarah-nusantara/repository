# encoding=utf8
""" Web services for reading logs.

Each change to the repository is logged.

Log entries are created automatically - there is no CRUD
for log entries, only reading.
"""
import re
import logging

from sqlalchemy.orm.attributes import InstrumentedAttribute
from cornice import Service
# from pyramid.events import NewResponse
# from pyramid.events import subscriber

from restrepo.config import LOG_SERVICE_PATH
from .validation import validate_schema
from restrepo.db import LogObject, LogAction
from restrepo.models.log import SearchSchema
from restrepo.config import ERRORS
from restrepo.utils import set_cors

log_service = Service(name=LOG_SERVICE_PATH[1:],
                      path=LOG_SERVICE_PATH, description=__doc__)


log_db_operations = logging.getLogger('restrepo.db_operations')


def valid_search_data(request):
    validate_schema(SearchSchema(), request.GET, request)
    if (request.validated and request.validated['date_from'] and request.validated['date_to']):
        if request.validated['date_from'] > request.validated['date_to']:
            request.errors.add('querystring', ERRORS.invalid_parameter.name,
                'date_to must be greater than date_from')
    if request.validated and 'order_by' in request.validated:
        order_by = request.validated['order_by']
        field = (getattr(LogAction, order_by, None) or
                 getattr(LogObject, order_by, None))
        if not isinstance(field, InstrumentedAttribute):
            request.errors.add('querystring', ERRORS.invalid_parameter.name,
                "The field %s is not a field of scan" % order_by)
        else:
            request.validated['order_by'] = field


@log_service.get(validators=(valid_search_data), filters=set_cors)
def search_log(request):
    """
    Search the log

    parameters:
        * **user:**
        * **date_from:**
        * **date_to:**
        * **object_id:** see the data model
        * **object_type:** one of "ead", "scan"
        * **message:** one of "create", "update", "move", "delete"
        * **start:** index of the first element returned (used in pagination)
        * **limit:** max # of objects to return
        * **order_by:** name of the field to sort on

    :returns:
        a list of log entries. See :ref:`TestLogs.test_log_search_by_date`
        each entry has the following attributes:
        date, id, log_action_id, message, object_id, object_type, user
    """
    query = request.db.query(LogObject).filter(
        LogAction.id == LogObject.log_action_id)
    params = request.validated
    if params['user']:
        query = query.filter(LogAction.user == params['user'])
    if params['date_from']:
        query = query.filter(LogAction.date >= params['date_from'])
    if params['date_to']:
        query = query.filter(LogAction.date <= params['date_to'])
    if params['object_id']:
        query = query.filter(LogObject.object_id == params['object_id'])
    if params['object_type']:
        query = query.filter(LogObject.object_type == params['object_type'])
    if params['message']:
        query = query.filter(LogObject.message == params['message'])
    order_by = request.validated.get('order_by')
    if request.validated['order_dir'] == 'DESC':
        order_by = order_by.desc()
    query = query.order_by(order_by, LogObject.id)
    start = request.validated['start']
    limit = request.validated['limit']
    results = []
    for el in query[start:start + limit]:
        dictel = dict(el)
        dictel.update(el.action)
        dictel['id'] = el.id
        results.append(dictel)
    n_res = query.count()
    return {
        'results': results,
        'query_used': dict(request.GET),
        'total_results': n_res,
        'start': start,
        'end': start + len(results)
    }


def get_user(request):
    user = request.POST.get('user') or request.GET.get('user')
    if not user:
        users_in_body = re.findall('user=\w*', request.body)
        if users_in_body:
            user = users_in_body[0][len('user='):]
    return user


def log_events(db, user, events):
    """log a db event, such as adding a scan"""
    for event in events:
        if not user:
            user = 'Anonymous'
        msg = "{event[message]} {event[object_type]} with id: {event[object_id]}".format(event=event)
        log_db_operations.info('{user} - {msg}'.format(**locals()))
