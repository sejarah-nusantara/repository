# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


from datetime import datetime
from dateutil import parser
from pytz import UTC
import unittest
import os
import tempfile
import shutil
import atexit
import urllib

from pyramid import testing as pyramid_testing

from restrepo import config
from restrepo.storage import REPO
from restrepo import main
from webtest import TestApp

from requests import ConnectionError

from restrepo.db import metadata, SolrWrapper
from restrepo.db.solr import Solr

TESTFILES_DIR = os.path.join(os.path.dirname(__file__), 'test_files')

PSQL_URL = os.environ['TEST_DB_URL']


def get_samplefile(filename):
    return open(os.path.join(TESTFILES_DIR, filename))


def get_samplefile_content(filename):
    with get_samplefile(filename) as fh:
        return fh.read()


def nuke_storage():
    "Completely erase stored files. Use in tests. Don't try this at home"
    return
    # ERASES $££*&*&87 PRODUCTION FILES
    if os.path.isdir(REPO):
        shutil.rmtree(REPO)


TEST_IMAGE_ZACKTHECAT = get_samplefile_content('zackthecat.tif')
TEST_IMAGE_300DPI = get_samplefile_content('img_300dpi.jpg')
TEST_IMAGE_GIF = get_samplefile_content('purple.gif')
TEST_IMAGE_JPG = get_samplefile_content('purple.jpg')
TEST_IMAGE_PNG = get_samplefile_content('purple.png')
TEST_IMAGE_TIF = get_samplefile_content('purple.tif')
TEST_IMAGE_TIFF = get_samplefile_content('purple.tiff')

TEST_IMAGE = TEST_IMAGE_GIF  # Use a small image for tests
DEFAULT_FILENAME = "test_image.jpg"


TEST_ARCHIVES = [
    (1, 'ID', 'ID-JaAN', 'Arsip Nasional Republik Indonesia',
        'HR', 'Archive of the Governor-General and councils of India'
              ' (High government) of the United East India Company'
              ' and its successors',),
    (2, 'ID', 'ID-JaAN', 'Arsip Nasional Republik Indonesia',
        'Krawang', 'Krawang Archives Inventory',),
    (3, 'GH', 'GH-PRAAD',
        'Public Records and Archives Administration Department Ghana',
        'RG1', 'Archives of the ministery of justice',),
    (4, 'GH', 'GH-PRAAD',
        'Public Records and Archives Administration Department Ghana',
        'MFA', 'Ministry of Foreign Affairs Archives',),
    (5, 'SR', 'SR-NAS', 'Nationaalarchief Suriname', '1.10.01.01.02',
        'Archief van het Districtcommissariaat Nickerie',),
    (6, 'LK', 'LK-NASL', 'National Archives Sri Lanka', 'RG. 145',
        'Co-operative Employees Commission',),
    (7, 'IN', 'IN-ChTNA', 'Chennai Tamil Nadu Archives', 'DR', 'Voorlopige inventaris van de archieven van de VOC ',),
    (8, 'LK', 'LK-NASL', 'National Archives Sri Lanka', 'RG. 01',
        'The Dutch Central Government of Coastal Ceylon',),
    (9, 'ZA', 'ZA-WC', 'Western Cape Archives and Records Services',
        'POS Inventory No. 1.103', 'Port Officer, Simon\'s Town',),
    (10, 'ZA', 'ZA-NARSSA',
         'National Archives and Records Service of South Africa',
         'T346/HCG',
         'Archive of the Secretary of the Holland Corps'
         ' and Garrison Service',),
    (11, 'IN', 'IN-DL NAI 005', 'National Archives of India', 'PA',
         'Microfilm Collection Of Dutch East India Company',),
    #       (12, 'BR', 'BR-RJANRIO', 'Arquivo Nacional Brasil', 'EG',

    (12, 'ID', 'ID-ANRI', 'test', 'K66a', '...'),
    (13, 'RU', 'RU-RSMA', 'Russian State Military Archives', '01',
         'Microfilms of the documents of Belgium, the Netherlands,'
         ' Luxembourg in the Russian State Military Archive',),
]
from restrepo.browser import log
# patch log_events
_events_log = []


def new_log_events(db, user, events):
    for event in events:
        event['user'] = user
        _events_log.append(event)

log.log_events = new_log_events


class BaseRepoTest(unittest.TestCase):

    def setUp(self):
        # cf. http://docs.pylonsproject.org/docs/pyramid/en/latest/narr/testing.html
        request = pyramid_testing.DummyRequest()
        settings = {}
        settings['tm.commit_veto'] = 'restrepo.db.commit_veto'
        self.config = pyramid_testing.setUp(request=request, settings=settings)
        self.config.include('pyramid_tm')
        self.maxDiff = None
        self.default_institution = 'GH-PRAAD'
        self.default_archive = 'RG1'
        self.default_country = 'GH'
        self.default_language = 'nl'
        self.search_data = {
            'institution': self.default_institution,
            'archive': self.default_archive,
            'archiveFile': 'a_repo',
            'country': self.default_country,
        }
        self.scan_data = {
            'archive_id': 3,
            'archiveFile': 'a_repo',
            'timeFrameFrom': '2012-09-10',
            'date': '2012-09-20T15:08:32.452547+00:00',
            'status': config.STATUS_NEW,
        }

        self.repo_path = tempfile.mktemp(".restrepo")
        self.wsgi_app = main({}, **{
            'sqlalchemy.url': PSQL_URL,
            'restrepo.repository_path': self.repo_path,
            'solr.url': 'http://127.0.0.1:9110/solr/',
            'ipauth.ipaddrs': '127.0.0.* 127.0.1.*',
            'ipauth.proxies': '127.0.0.*',
            'ipauth.principals': 'locals',
            'publish_in_pagebrowser.url': 'http://127.0.0.1/publish',
            'unpublish_in_pagebrowser.url': 'http://127.0.0.1/delete',
            'watermark_file': os.path.join(TESTFILES_DIR, 'watermark.png'),
            'watermark_pos_x': '14',
            'watermark_pos_y': '17',
            'watermark_size': '10%',
            'watermark_image_format': 'jpeg',
        })
        self.app = TestApp(self.wsgi_app, extra_environ={"REMOTE_ADDR": "127.0.0.1"})
        self.registry = self.app.app.registry
        baseurl = self.app.app.registry.settings['solr.url']

        self.solr = Solr(baseurl + 'entity')
        self.solr_scan = SolrWrapper(self.solr, 'scan', 'number')
        self.solr_ead = SolrWrapper(self.solr, 'ead', 'ead_id')
        self.solr_eadcomponent = SolrWrapper(self.solr, 'eadcomponent', 'eadcomponent_id')
        self.solr_archivefile = SolrWrapper(self.solr, 'archivefile', 'archivefile_id')

        try:
            self.solr.delete_by_query('*:*')
        except ConnectionError:  # this is the first solr request that we do, so if it fails we give the user some feedback
            msg = ''
            msg += 'Error trying to connect to {baseurl}'.format(**locals())
            msg += '\n(perhaps you should start it with bin/circusd, bin/circusctl start test_solr ?)'
            raise Exception(msg)

        from restrepo.tests import fixture
        self.session = fixture.Session()

        self.app.app.registry.settings['db.session'] = lambda: self.session  # @IgnorePep8

        self.db = self.session

        # fill the archives table
        from restrepo.db.archive import archive_table
        for archive in TEST_ARCHIVES:
            self.session.execute(archive_table.insert(archive))
        current_max = max(a[0] for a in TEST_ARCHIVES)
        new_max = current_max + 1
        self.session.execute("ALTER SEQUENCE archive_id_seq RESTART WITH %i" % new_max)

        self.session.commit()

        def tear_down():
            nuke_storage()
            self.session.expire_all()
            self.session.rollback()
            # This is fragile, sorry.
            # The order of the emptied tables is important
            # In particular log_object MUST be emptied before log_action
            # A reverse lexicographic sort is used to achieve this
            for table in reversed(metadata.tables.values()):
                self.session.execute(table.delete())
            self.session.commit()
            self.solr.delete_by_query('*:*', commit=True)
        # We use addCleanup because self.tearDown won't be called if
        # there was an error during setUp, that might be the case if
        # a subclass calls super() and then put_one_something that fails
        self.addCleanup(tear_down)
        # In case of unclean exit, we hook nuke_storage at system exit
        atexit.register(nuke_storage)

    def tearDown(self):
        self.reset_events_log()
        pyramid_testing.tearDown()
        shutil.rmtree(self.repo_path)
        super(BaseRepoTest, self).tearDown()

    @property
    def events_log(self):
        return _events_log

    def reset_events_log(self):
        global _events_log
        _events_log = []

    def assert_dict_equality(self, a, b):
        """
        Return True if all elements in a are equal to those in b.

        Strings representing the same datetime with different timezone
        are treated as equal.

        The _version_ key is ignored
        """
        keys_a = set(a.keys())
        if '_version_' in keys_a:
            keys_a.remove('_version_')
        keys_b = set(b.keys())
        if '_version_' in keys_b:
            keys_b.remove('_version_')
        self.assertEqual(keys_a, keys_b)  # , 'the keys in the two dictionaries are not equal')
        self.assert_dict_subset(a, b, keys_a)

    def assert_dict_subset(self, a, b, keys=None):
        """
        Return True if al elements in a are equal to those in b.
        Strings representing the same datetime with different timezone
        are treated as equal.
        """
        def parse_date(string):
            res = parser.parse(string)
            if not res.tzinfo:
                res = res.replace(tzinfo=UTC)
            return res
        if not keys:
            keys = a.keys()
        for key in keys:
            vala, valb = a[key], b[key]
            if vala != valb:
                vala = parse_date(vala)
                valb = parse_date(valb)

                # solr drops microsecond, so we dont care about them
                vala = vala.replace(microsecond=0)
                valb = valb.replace(microsecond=0)
            self.assertEqual(
                vala, valb,
                "a['%s'] = %s, but b['%s'] = %s" % (key, vala, key, valb))

    def add_five_scans(self, additional_data={}, **kwargs):
        data = dict(self.scan_data)
        data.update(additional_data)
        data.update(kwargs)
        results = []
        files = (TEST_IMAGE_JPG, TEST_IMAGE_TIFF, TEST_IMAGE_PNG,
                 TEST_IMAGE_GIF, TEST_IMAGE_TIFF)
        for contents in files:
            results.append(self.add_one_scan(data,
                                             filecontents=contents,
                                             enabled_web_chat=False).json)
        return results

    def add_one_scan(self, scan_data=None, filename=DEFAULT_FILENAME,
                     filecontents=TEST_IMAGE, status=200,
                     enabled_web_chat=True,
                     dontlog=False,):
        "params: scan_data, filename, filecontents, status, enabled_web_chat"
        if not scan_data:
            scan_data = self.scan_data

        if isinstance(filename, type([])):
            files = zip(filename, filecontents)
        else:
            files = [(filename, filecontents)]
        upload_files = [('file', fn, filecontent) for fn, filecontent in files]
        if dontlog:
            dontlog = '1'
        else:
            dontlog = '' if enabled_web_chat else '1'

        if 'transcription' in scan_data:
            scan_data['transcription'] = (scan_data['transcription'].encode('utf8'))
        return self.app.post(
            config.SERVICE_SCAN_COLLECTION,
            scan_data,
            status=status,
            upload_files=upload_files,
            extra_environ={'dontlog_web_chats': dontlog},
        )

    def assertMoreRecent(self, value, then):
        """
        Assert that value (a datetime object) is more recent
        than `then`.
        """
        self.assertTrue(type(value) in (str, unicode, datetime))
        if type(value) in (str, unicode):
            value = parser.parse(value)
        if type(then) in (str, unicode):
            then = parser.parse(then)
        value = value.replace(microsecond=0)
        then = then.replace(microsecond=0)
        self.assertTrue(value >= then, '%s should be greater or equal than %s' % (value, then))

    def get_default_filecontents(self, filename='short_ead.xml'):
        return get_samplefile_content(filename)

    def add_one_ead(
        self,
        filecontents=None,
        status=200,
        dontlog=False,
        additional_data={},
        filename='test_file_123.xml',
    ):
        if not filecontents:
            filecontents = self.get_default_filecontents()
        dontlog = '1' if dontlog else ''
        filetuple = ('file', filename, filecontents)

        response = self.app.post('/ead', additional_data, status=status, upload_files=[filetuple], extra_environ={'dontlog_web_chats': dontlog})
        return response

    def change_ead(
        self, filecontents, dontlog=False,
        status=200,
        additional_data={},
        filename='test_file_123.xml',
    ):

        if not filecontents:
            filecontents = self.get_default_filecontents()
        dontlog = '1' if dontlog else ''
        filetuple = ('file', filename, filecontents)
        return self.app.put(
            localurl('/ead/%s' % filename), additional_data,
            status=status,
            upload_files=[filetuple],
            extra_environ={'dontlog_web_chats': dontlog})

    def delete_ead(self, ead_id):
        self.app.delete(localurl(config.SERVICE_EAD_ITEM.format(ead_id=ead_id)))


def localurl(url):
    return str(url.replace('http://localhost', ''))
