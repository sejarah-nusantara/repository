# encoding=utf8
import StringIO
import csv
from restrepo import config

from test_scans import TestScanSearchBase


class TestScans(TestScanSearchBase):

    def test_basic_search(self):
        response = self.app.get(config.SERVICE_SCAN_COLLECTION_CSV)

        result = csv.reader(StringIO.StringIO(response.body), delimiter=',', quoting=csv.QUOTE_ALL)
        result = list(result)
        # length is number of results + headers
        self.assertEqual(len(result), 5 + 1)

    def assert_csv_length(self, response, length):
        result = csv.reader(StringIO.StringIO(response.body), delimiter=',', quoting=csv.QUOTE_ALL)
        # length is number of results + headers
        self.assertEqual(len(list(result)) - 1, length)

    def test_search_for_archiveFiles(self):
        url = config.SERVICE_SCAN_COLLECTION_CSV

        response = self.app.get(url, {'archiveFile_raw': 'another_repo'})
        self.assert_csv_length(response, 3)

        response = self.app.get(url, {'archiveFile_raw': 'repo4'})
        self.assert_csv_length(response, 1)

        response = self.app.get(url, {'archiveFile_raw': '[another_repo TO repo4]'})
        self.assert_csv_length(response, 4)

        response = self.app.get(url, {'archiveFile_raw': '(another_repo OR repo4)'})
        self.assert_csv_length(response, 4)

    def test_with_diacritics(self):
        url = config.SERVICE_SCAN_COLLECTION_CSV
        text_with_diacritics = u'üüèèááu\xeb'
        scan = self.add_scan(transcription=text_with_diacritics)
        response = self.app.get(url)
        self.assertTrue(text_with_diacritics in response.body.decode('utf8'))


