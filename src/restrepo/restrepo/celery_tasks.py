import os
import requests
import logging
from datetime import datetime

from celery import Celery
from celery import Task

from restrepo import config

# dont spoil our log with lots of info about requests handler
requests_logger = logging.getLogger("requests")
requests_logger.setLevel(logging.WARN)
update_logger = logging.getLogger('restrepo.pagebrowser_update')


app = Celery('tasks', broker='amqp://guest@localhost:5672//')
app.config_from_object('restrepo.celeryconfig')

# we keep a list of queued tasks, to avoid sending the same action over and over again
# the queued tasks is a dictionary that that stores, for each 'task type'
# the time it was added
app.queued_tasks = {}
# timeout of items in queue  (in seconds)
# (an item will added the the queue not more often the once every QUEUE_TIMEOUT seconds)
QUEUE_TIMEOUT = 20


class PingPagebrowserTask(Task):
    def delay(self, action, url, ead_id, archivefile_id):
        new_task = self.add_to_queue(action, url, ead_id, archivefile_id)
        if new_task:
            try:
                return super(PingPagebrowserTask, self).delay(action, url, ead_id, archivefile_id)
            except Exception as error:
                if error.message.errno == 111:
                    # [Errno 111] Connection refused
                    msg = unicode(error)
                    msg += ' - Is rabbitmq-server installed and running?'
                    logging.error(msg)
                    # raise Exception(msg)
                else:
                    raise error

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        action, url, ead_id, archivefile_id = args
        self.delete_from_queue(action, url, ead_id, archivefile_id)

    def delete_from_queue(self, action, url, ead_id, archivefile_id):
        if self._state_description(action, url, ead_id, archivefile_id) in app.queued_tasks:
            del app.queued_tasks[self._state_description(action, url, ead_id, archivefile_id)]

    def add_to_queue(self, action, url, ead_id, archivefile_id):
        logging.debug('Adding {action}, {url}, {ead_id}, {archivefile_id} to queue'.format(**locals()))
        # logging.debug(unicode(app.queued_tasks))
        if self._state_description(action, url, ead_id, archivefile_id) in app.queued_tasks:
            time_added = app.queued_tasks[self._state_description(action, url, ead_id, archivefile_id)]
            now = datetime.now()
            if (now - time_added).total_seconds() > QUEUE_TIMEOUT:
                app.queued_tasks[self._state_description(action, url, ead_id, archivefile_id)] = datetime.now()
                logging.debug('added (in queue, but timed out - {} secs)'.format(QUEUE_TIMEOUT))
                return True
            else:
                # not added, already in queue
                logging.debug('not added (already in queue)')
                return False
        else:
            app.queued_tasks[self._state_description(action, url, ead_id, archivefile_id)] = datetime.now()
            logging.debug('added (not in queue)')
            return True

    def _state_description(self, action, url, ead_id, archivefile_id):
        assert action in ['delete', 'refresh']
        return (action, url, ead_id, archivefile_id)

    def ping_url(self, url, params):
        # http://docs.python-requests.org/en/latest/
        auth_fn = os.path.join(config.THIS_DIR, 'pagebrowser_auth.txt')
        if not os.path.exists(auth_fn):
            raise Exception('No file found at {auth_fn}'.format(auth_fn=auth_fn))
        user, password = open(auth_fn).readlines()
        user = user.strip()
        password = password.strip()

        try:
            response = requests.get(url, params=params, auth=(user, password))
        except Exception, error:
            msg = 'Error trying to open %s with params %s' % (url, unicode(params))
            msg += '\n'
            msg += unicode(error)
            update_logger.warn(msg)
            raise Exception(msg)
        if response.status_code != 200:
            update_logger.warn('Response: %s; %s' % (response.status_code, response.text))
        update_logger.info('url %s; %s returned response: %s' % (url, params, response.content))
        return response


@app.task(base=PingPagebrowserTask, bind=True, name='Update Book')
def update_book(self, action, url, ead_id, archivefile_id):
    # add a task to update the pagebrowser book to the rabbitmq pool via celery
    assert action in ['refresh', 'delete']
    params = dict(
        archivefile=archivefile_id,
        ead_id=ead_id,
    )
    if action == 'refresh':
        params['publish'] = '1'
    elif action == 'delete':
        params['delete'] = '1'

    response = self.ping_url(url, params)
    now = datetime.now().isoformat()
    if response.status_code == 200:
        msg = '[{now}]: OK: {action} book at {archivefile_id} {ead_id} [visited {url} with params {params}]'.format(**locals())
        return msg
    else:
        msg = '[{now}] Failure: {action} book at {archivefile_id} {ead_id} using {url} and {params}.\n{response.content}'.format(**locals())
        raise Exception(msg)
