#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#

import os
import logging
import copy
import simplejson as json

from pyramid.config import Configurator
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
from restrepo.security import Root
import cornice

from pyramid import httpexceptions as exc
from pyramid.response import Response
from cornice.util import json_error
# REPO location is the first found value among:
# * this file's dir
# * REPOSITORY_PATH environment (if specified)
# * restrepo.repository_path wsgi setting (if specified)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'files'))

if 'REPOSITORY_PATH' in os.environ:
    REPO = os.environ.get('REPOSITORY_PATH', REPO)

logger = logging.getLogger(__name__)


# we patch the error handling becaue we also want to log validation errors
# original_json_error = copy.deepcopy(cornice.util.json_error)
class _JSONError(exc.HTTPError):
    def __init__(self, errors, status=400):
        body = {'status': 'error', 'errors': errors}
        Response.__init__(self, json.dumps(body, use_decimal=True))
        self.status = status
        self.content_type = 'application/json'


def dasa_error_handler(errors):
    for error in errors:
        try:
            logger.error('{name} error in {location}: {description}'.format(**error))
        except:
            logger.error(unicode(error))
    return _JSONError(errors, errors.status)

cornice.util.json_error = dasa_error_handler
cornice.service.json_error = dasa_error_handler


def main(global_config, **settings):
    from restrepo.db import DbRequest  # Avoid circular dependencies
    from restrepo.db.settings import Settings
    engine = engine_from_config(settings, prefix='sqlalchemy.')
    settings['db.session'] = sessionmaker(extension=ZopeTransactionExtension(), bind=engine)
    settings['tm.commit_veto'] = 'restrepo.db.commit_veto'

    # get settings stored in db
    for record in settings['db.session']().query(Settings).all():
        settings[record.key] = record.value
    # need to commit the transaction otherwise the Settings table will remain locked
    import transaction
    transaction.commit()
    config = Configurator(settings=settings, request_factory=DbRequest, root_factory=Root)
    config.include("cornice")
    # config.include('pyramid_mako')
    config.include('pyramid_chameleon')
    config.include('pyramid_tm')
    config.include("restrepo.security")
    config.add_static_view(name='static', path='restrepo:static')
    config.add_static_view(name='deform_static', path='deform:static')
    config.add_route('admin_archives', '/admin_archives')
    config.add_route('configuration', '/configuration')
    config.add_route('root', '/')
    config.add_renderer(name='csv', factory='restrepo.browser.scans_csv.CSVRenderer')

    config.scan("restrepo.security")
    config.scan("restrepo.browser")
    config.scan("restrepo.pagebrowser")

    # Override env REPOSITORY_PATH if restrepo.repository_path
    # is found in config
    if 'restrepo.repository_path' in settings:
        path = settings['restrepo.repository_path']
        if not os.path.isdir(path):
            os.mkdir(path)
        import restrepo.storage
        restrepo.storage.REPO = path
    return config.make_wsgi_app()

_ROOT = os.path.abspath(os.path.dirname(__file__))


def get_datafile(filename):
    with open(os.path.join(_ROOT, 'data', filename)) as fh:
        return fh.read()
