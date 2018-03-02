import os
import grequests
import requests
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from restrepo.db.scans import Scan

from base import BaseRepoTest
from base import DEFAULT_FILENAME, TEST_IMAGE


class TestConcurrentRequests(BaseRepoTest):
    def setUp(self):
        super(TestConcurrentRequests, self).setUp()
        self.five_scans = self.add_five_scans()
        self.five_more_scans = self.add_five_scans()
        self.scans = self.five_scans + self.five_more_scans
        self.port = os.environ['TEST_INSTANCE_PORT']
        PSQL_URL = os.environ['TEST_DB_URL']
        settings = {
            'sqlalchemy.url': PSQL_URL,
        }
        engine = engine_from_config(settings, prefix='sqlalchemy.')
        self.session = sessionmaker(bind=engine)()

        # test the connection
        try:
            requests.get(self.localurl('http://localhost/scans'))
        except Exception:
            # TODO: when test_instance is not available, give a decent warning
            raise

    def localurl(self, url):
        return str(url.replace('https', 'http').replace('http://localhost', 'http://localhost:{}'.format(self.port)))

    def assert_invariants(self, scan):
        # we expect that in the database, all sequence numbers are consecutive
        if hasattr(scan, 'archiveFile'):
            archiveFile = scan.archiveFile
        else:
            archiveFile = scan['archiveFile']
        scans = self.session.query(Scan).filter(Scan.archiveFile == archiveFile).all()
        nrs = [x.sequenceNumber for x in scans]
        nrs.sort()
        if nrs != range(1, len(nrs) + 1):
            raise Exception('numbers from db: {}'.format(nrs))

        # and the same for the results from the index as well
        url = '/scans?archiveFile={}'.format(archiveFile)
        response = self.app.get(url)
        results = response.json['results']
        nrs = [x['sequenceNumber'] for x in results]
        nrs.sort()
        if nrs != range(1, len(nrs) + 1):
            raise Exception('numbers from solr index: {}'.format(nrs))

    def test_concurrent_delete(self):
        # set up concurrent request to delete 4 out of 10 scans
        urls = [self.localurl(scan['URL']) for scan in self.scans]
        # GET the urls (testing sanity)
        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 10)
        rs = (grequests.get(u) for u in urls)
        print urls
        responses = grequests.map(rs)
        for response in responses:
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

            self.assertEqual(response.status_code, 200)

        # now we DELETE 7 scans concurrently
        rs = (grequests.delete(u) for u in urls[:7])
        responses = grequests.map(rs)
        for response in responses:
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

            self.assertEqual(response.status_code, 200)

        self.assert_invariants(self.scans[-1])

        # we now expect to have only 3 scans left
        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 3)

    def test_concurrent_move(self):
        scans = self.five_scans + self.five_more_scans
        rs = []
        rs.append(grequests.post(self.localurl(os.path.join(scans[1]['URL'], 'move')), data={'after': '3'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[3]['URL'], 'move')), data={'after': '5'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[5]['URL'], 'move')), data={'after': '5'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[7]['URL'], 'move')), data={'after': '2'}))
        # now we send all reqeust concurrently
        responses = grequests.map(rs)
        for response in responses:
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

        self.assert_invariants(scans[3])

        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 10)

    def test_concurrent_update_archivefile(self):
        scans = self.five_scans + self.five_more_scans
        rs = []
        rs.append(grequests.put(self.localurl(os.path.join(scans[1]['URL'])), data={'archiveFile': '2'}))
        rs.append(grequests.put(self.localurl(os.path.join(scans[3]['URL'])), data={'archiveFile': '2'}))
        rs.append(grequests.put(self.localurl(os.path.join(scans[5]['URL'])), data={'archiveFile': '2'}))
        rs.append(grequests.put(self.localurl(os.path.join(scans[7]['URL'])), data={'archiveFile': '2'}))
        # now we send all reqeust concurrently
        responses = grequests.map(rs)
        for response in responses:
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

        self.assert_invariants(scans[3])

        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 10)

    def test_concurrent_delete_and_move(self):
        # set up concurrent request to delete 4 out of 10 scans
        # we delete 4 scans, and move 4 others
        scans = self.scans
        urls_to_delete = [self.localurl(scans[i]['URL']) for i in [2, 4, 6, 8]]
        rs = []
        rs += [grequests.delete(u) for u in urls_to_delete]
        rs.append(grequests.post(self.localurl(os.path.join(scans[1]['URL'], 'move')), data={'after': '3'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[3]['URL'], 'move')), data={'after': '5'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[5]['URL'], 'move')), data={'after': '5'}))
        rs.append(grequests.post(self.localurl(os.path.join(scans[7]['URL'], 'move')), data={'after': '2'}))
        # now we send all reqeust concurrently
        responses = grequests.map(rs)
        for response in responses:
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

        # we now expect to have only 1 scans left
        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 6)
        self.assertEqual([scan['sequenceNumber'] for scan in response.json['results']], range(1, 7))
        self.assert_invariants(response.json['results'][3])

    def test_concurrent_add(self):
        data = self.scan_data
        response = self.app.get('/scans')

        # test sanity
        self.assertEqual(response.json['total_results'], 10)
        self.assert_invariants(response.json['results'][0])

        filename = DEFAULT_FILENAME
        filecontent = TEST_IMAGE
        files = {'file': (filename, filecontent)}
        rs = []

        # 10 requests to add the same scan
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))
        rs.append(grequests.post(self.localurl('http://localhost/scans'), data=data, files=files))

        responses = grequests.map(rs)

        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 20)
        i = 0
        for response in responses:
            i += 1
            try:
                self.assertEqual(response.status_code, 200)
            except:
                open('/tmp/tmp.html', 'w').write(response.content)
                raise

            self.assert_invariants(response.json())

        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 20)

    def test_add(self):
        data = self.scan_data
        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 10)
        filename = DEFAULT_FILENAME
        filecontent = TEST_IMAGE
        files = {'file': (filename, filecontent)}
        # we had a bug (we called request.db.commit()) that only occurred in a running instance, not in test
        response = requests.post(self.localurl('http://localhost/scans'), data=data, files=files)
        try:
            self.assertEqual(response.status_code, 200)
        except Exception as error:
            print response.content[:200]
            open('/tmp/tmp.html', 'w').write(response.content)
            msg = 'Perhaps the testrepository is not running? Try bin/circusctl start test_repository'
            raise Exception(unicode(error) + '\n' + msg)
        # now we should have 11 scans
        response = self.app.get('/scans')
        self.assertEqual(response.json['total_results'], 11)
