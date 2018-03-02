"""functions for updating the pagebrowser"""

"""test this locally like thus:

curl http://localhost:5000/archivefiles/1/2495 -d status=1
curl -X PUT -d status=2 http://localhost:5000/archivefiles/1/2495


"""
import logging

from restrepo import celery_tasks

# dont spoil our log with lots of info about requests handler
x = logging.getLogger("requests")
x.setLevel(logging.WARN)

update_logger = logging.getLogger('restrepo.pagebrowser_update')
update_logger.setLevel(logging.INFO)


def refresh_book(context, *args, **kwargs):
    url = context.registry.settings.get('publish_in_pagebrowser.url')
    logging.debug('Refreshing book at {url}'.format(**locals())) 
    return celery_tasks.update_book.delay('refresh', url, *args, **kwargs)


def delete_book(context, *args, **kwargs):
    url = context.registry.settings.get('unpublish_in_pagebrowser.url')
    logging.debug('Deleting book at {url}'.format(**locals())) 
    return celery_tasks.update_book.delay('delete', url, *args, **kwargs)
