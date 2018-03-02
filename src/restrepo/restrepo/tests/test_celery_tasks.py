import time
import datetime
from restrepo.tests.base import BaseRepoTest
from restrepo import celery_tasks

from mock import Mock


class ResponseMock(Mock):
    status_code = 200


class RequestsMock(Mock):
    get = Mock(return_value=ResponseMock())


class RequestsWithDelayMock(Mock):
    def get(self, url, *args, **kwargs):
        time.sleep(1)
        return ResponseMock()


class TestCeleryTasks(BaseRepoTest):
    def setUp(self):
        super(TestCeleryTasks, self).setUp()

        self.old_requests = celery_tasks.requests
        celery_tasks.requests = RequestsMock()
        # this setting makes celery execute tasks immediately
        celery_tasks.app.conf.update(CELERY_ALWAYS_EAGER=True)

    def tearDown(self):
        celery_tasks.requests = self.old_requests
        celery_tasks.app.conf.update(CELERY_ALWAYS_EAGER=False)
        ResponseMock.status_code = 200

    def test_celery(self):
        # this just tests basic sanity

        msg = celery_tasks.update_book('refresh', 'http://127.0.0.1/', '1', '2')
        self.assertTrue('refresh' in msg, msg)
        msg = celery_tasks.update_book('delete', 'http://127.0.0.1/', '1', '2')
        self.assertTrue('delete' in msg, msg)

        ResponseMock.status_code = 400
        self.assertRaises(Exception, celery_tasks.update_book, 'refresh', 'http://127.0.0.1/', '1', '2')
        self.assertRaises(Exception, celery_tasks.update_book, 'delete', 'http://127.0.0.1/', '1', '2')

    def test_celery_queue_refresh(self):
        celery_tasks.app.queued_tasks = {}
        celery_tasks.requests.get.call_count = 0
        self.assertEqual(celery_tasks.app.queued_tasks, {})
        celery_tasks.update_book.delay('refresh', 'http://127.0.0.1/', '1', '2')
        self.assertEqual(celery_tasks.app.queued_tasks, {})
        self.assertEqual(celery_tasks.requests.get.call_count, 1)

        # if we add the task to the queue, we expect requests.get to not be called
        celery_tasks.app.queued_tasks[('refresh', 'http://127.0.0.1/', '1', '2')] = datetime.datetime.now()
        celery_tasks.update_book.delay('refresh', 'http://127.0.0.1/', '1', '2')
        # call_count should reamin 1
        self.assertEqual(celery_tasks.requests.get.call_count, 1)

        # hower, if we have an expired task in the queue, we expect it to be be calle anyway
        celery_tasks.app.queued_tasks[('refresh', 'http://127.0.0.1/', '1', '2')] = datetime.datetime(1900, 1, 1)
        celery_tasks.update_book.delay('refresh', 'http://127.0.0.1/', '1', '2')
        # call_count should reamin 1
        self.assertEqual(celery_tasks.requests.get.call_count, 2)

        # if we disable the delete action, the task should added (and remain) in the queue
        celery_tasks.app.queued_tasks = {}
        old_delete_from_queue = celery_tasks.update_book.delete_from_queue
        celery_tasks.update_book.delete_from_queue = Mock()
        celery_tasks.update_book.delay('refresh', 'http://127.0.0.1/', '1', '2')
        self.assertTrue(('refresh', 'http://127.0.0.1/', '1', '2') in celery_tasks.app.queued_tasks, 'queus is {celery_tasks.app.queued_tasks}'.format(celery_tasks=celery_tasks))
        celery_tasks.update_book.delete_from_queue = old_delete_from_queue

    def test_celery_queue_delete(self):
        # deleting should have the same behavior
        celery_tasks.requests.get.call_count = 0
        celery_tasks.app.queued_tasks = {}
        self.assertEqual(celery_tasks.app.queued_tasks, {})
        celery_tasks.update_book.delay('delete', 'http://127.0.0.1/', '1', '2')
        self.assertEqual(celery_tasks.app.queued_tasks, {})
        self.assertEqual(celery_tasks.requests.get.call_count, 1)

        # if we have the task in the queue, we expect requests.get to not be called
        celery_tasks.app.queued_tasks[('delete', 'http://127.0.0.1/', '1', '2')] = datetime.datetime.now()
        celery_tasks.update_book.delay('delete', 'http://127.0.0.1/', '1', '2')
        # call_count should reamin 1
        self.assertEqual(celery_tasks.requests.get.call_count, 1)

        # hower, if we have an expired task in the queue, we expect it to be be calle anyway
        celery_tasks.app.queued_tasks[('delete', 'http://127.0.0.1/', '1', '2')] = datetime.datetime(1900, 1, 1)
        celery_tasks.update_book.delay('delete', 'http://127.0.0.1/', '1', '2')
        # call_count should reamin 1
        self.assertEqual(celery_tasks.requests.get.call_count, 2)

        # if we disable the delete action, the task should remain in the queue
        celery_tasks.app.queued_tasks = {}
        old_delete_from_queue = celery_tasks.update_book.delete_from_queue
        celery_tasks.update_book.delete_from_queue = Mock()
        celery_tasks.update_book.delay('delete', 'http://127.0.0.1/', '1', '2')
        self.assertTrue(('delete', 'http://127.0.0.1/', '1', '2') in celery_tasks.app.queued_tasks, 'queus is {celery_tasks.app.queued_tasks}'.format(celery_tasks=celery_tasks))
        celery_tasks.update_book.delete_from_queue = old_delete_from_queue
