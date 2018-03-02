from base import BaseRepoTest, TEST_IMAGE_TIF, localurl
from base import TEST_IMAGE_GIF, TEST_IMAGE_JPG, TEST_IMAGE_PNG
from restrepo.db.archive import get_archive, get_archives
from restrepo.config import status as status_values
from restrepo.config import ERRORS
from restrepo import config
from restrepo.utils import now, string_to_datetime


class TestScans(BaseRepoTest):
    def test_add(self):
        res = self.app.get(config.SERVICE_SCAN_COLLECTION).json['results']
        self.assertEqual(res, [])
        data = dict(self.scan_data)
        data['user'] = 'atestuser'
        data['title'] = 'a title'
        data['type'] = 'some type'
        data['language'] = 'nl'
        result = self.add_one_scan(data)
        self.assertTrue(result.json['number'])

        all_scans = self.app.get(config.SERVICE_SCAN_COLLECTION).json['results']
        self.assertEqual(len(all_scans), 1)
        storedscan = all_scans[0]
        self.assert_dict_subset(data, storedscan)

    def test_add_lastmodified(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        then = now()
        result = self.add_one_scan(scan_data).json
        self.assertEqual(result['archive_id'], 3)
        self.assertMoreRecent(result['dateLastModified'], then)

    def test_default_value_date_on_add(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        then = now()
        result = self.add_one_scan(scan_data).json
        self.assertTrue(result['date'])
        self.assertMoreRecent(result['date'], then)
        # these two dates should be approximately the same (give or take a millisecond)
        self.assertEqual(result['date'][:20], result['dateLastModified'][:20])

        a_date = string_to_datetime('2012-01-01')
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo', 'date': a_date}
        then = now()
        result = self.add_one_scan(scan_data).json
        self.assertEqual(string_to_datetime(result['date']), a_date)

    def test_add_validate_status(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo', 'status': 12}
        result = self.add_one_scan(scan_data, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_add_missing_archiveFile(self):
        scan_data = dict(self.scan_data)
        del scan_data['archiveFile']
        result = self.add_one_scan(scan_data, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_update_several_fields_separately(self):
        #
        # becuase of optimization code in db.scans get_solr_data
        # we need to make sure that when we update, we really calculate all relevant fields
        #
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        result = self.add_one_scan(scan_data).json
        url = localurl(result['URL'])
        new_data = {
            'archive_id': 2,
            'archiveFile': 'another_repo',
            'contributor': 'contributor_value',
            'creator': 'another creator',
            'date': '2222-02-22',
            'folioNumber': '345',
            'originalFolioNumber': '314159',
            'format': 'another format',
            'language': 'language',
            'publisher': 'publisher',
            'relation': 'relation',
            'rights': 'rights',
            'relation': 'relation',
            'source': 'source',
            'status': 2,
            'subjectEN': 'subjectNE',
            'type': 'type2',
            'title': 'xxx',
            'timeFrameFrom': '2002-02-02',
            'timeFrameTo': '2030-03-03',
            'transcription': 'transcription',
            'transcriptionAuthor': 'aslfkdjlj ',
            'transcriptionDate': '2011-02-03',
            'translationEN': 'tarslkj ',
            'translationENDate': '2011-02-04',
            'translationENAuthor': 'translationENAuthor_value',
            'translationID': 'lsdajfasdf',
            'translationIDAuthor': 'translationENAuthor_value',
            'translationIDDate': '2012-08-07',
            # file:
            'URI': 'URI_value',
            'user': 'someone',
        }

        for k in new_data:
            self.app.put(url, {k: new_data[k]})
            result = self.app.get(url).json
            if 'date' in k.lower():
                self.assertEqual(result[k][:10], new_data[k])
            else:
                self.assertEqual(result[k], new_data[k])

    def test_delete(self):
        """
        A deleted scan is really deleted and gone.
        """
        scans = self.add_five_scans()
        url = localurl(scans[1]['URL'])
        self.app.delete(url)
        # The deleted scan is not accessible anymore
        res = self.app.get(url, status=404).json
        self.assertEqual(res['errors'][0]['name'], 'no scan found with this number: {}'.format(scans[1]['number']))
        # and doesn't show up in searches
        all_scans = self.app.get(config.SERVICE_SCAN_COLLECTION).json['results']
        self.assertEqual(len(all_scans), 4)
        # Scans 2, 3, 4 and 5 have been shifted
        self.assertEqual([el['sequenceNumber'] for el in all_scans], [1, 2, 3, 4])

    def test_default_status(self):
        # the default status is NEW
        data = dict(self.scan_data)
        del data['status']
        result = self.add_one_scan(data).json
        self.assertEqual(result['status'], status_values.NEW)

    def test_basic_search(self):
        self.add_five_scans()
        response = self.app.get(config.SERVICE_SCAN_COLLECTION, {'start': 2})
        self.assertEqual(response.json['total_results'], 5)
        self.assertEqual(response.json['start'], 2)
        self.assertEqual(response.json['end'], 5)

        # we had a but report that searching does not ignore status
        some_scan = response.json['results'][0]
        self.app.put(localurl(some_scan['URL']), {'status': 2})
        response = self.app.get(config.SERVICE_SCAN_COLLECTION, {'status': 2})
        self.assertEqual(response.json['total_results'], 1)
        response = self.app.get(config.SERVICE_SCAN_COLLECTION, {'status': 1})
        self.assertEqual(response.json['total_results'], 4)
        response = self.app.get(config.SERVICE_SCAN_COLLECTION)
        self.assertEqual(response.json['total_results'], 5)

    def test_search_validation(self):
        # invalid value for start should raise an error
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'start': 'a'}, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)

        # passing invalid search paramenters should raise an error
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'invalidparameter': 'a'},
            status=400).json
        self.assertEqual(result['errors'][0]['name'], 'invalid_parameter')

        # "fonds" is not a valid parameter anymore
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'fonds': 'a'}, status=400).json
        self.assertEqual(result['errors'][0]['name'], 'invalid_parameter')

    def test_search_validate_sort(self):
        self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': 'wrong'}, status=400).json
        self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_dir': '--'}, status=400).json
        self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': 'archiveFile'}).json
        self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_dir': 'ASC'}).json
        self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_dir': 'DESC'}).json

    def test_search_sort(self):
        scans = self.add_five_scans()
        an_early_date = '2000-01-01'
        first_archiveFile = 'a_arepo_this_comes_first'

        self.app.put(localurl(scans[3]['URL']), {'date': an_early_date})
        self.app.put(localurl(scans[3]['URL']), {'archive_id': 2})
        oldestid = scans[3]['number']
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': 'date'}).json
        self.assertEqual(result['results'][0]['number'], oldestid)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION,
            {'order_by': 'date', 'order_dir': 'DESC'}).json
        self.assertEqual(result['results'][-1]['number'], oldestid)

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': '-date'}).json
        self.assertEqual(result['results'][-1]['number'], oldestid)

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': '-date'}).json
        self.assertEqual(result['results'][-1]['number'], oldestid)

        self.app.put(localurl(scans[1]['URL']), {'archiveFile':
            first_archiveFile})
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': 'archiveFile'}).json
        self.assertEqual(result['results'][0]['archiveFile'],
            first_archiveFile)

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'order_by': '-archiveFile,date'}).json
        self.assertEqual(result['results'][0]['date'][:len(an_early_date)],
             an_early_date)
        self.assertEqual(result['results'][-1]['archiveFile'],
             first_archiveFile)

        # by default results are sorted
        default_result = self.app.get(config.SERVICE_SCAN_COLLECTION).json
        default_result = [img['number'] for img in default_result['results']]
        sorted_result = self.app.get(config.SERVICE_SCAN_COLLECTION,
            {'order_by': 'archive_id,archiveFile,sequenceNumber'}).json
        sorted_result = [image['number'] for image in sorted_result['results']]
        self.assertEqual(default_result, sorted_result)

    def test_sequencenumber(self):
        self.add_one_scan(self.scan_data).json
        another_scan = self.add_one_scan(self.scan_data).json
        self.assertEqual(another_scan['sequenceNumber'], 2)

    def test_scan_get_data(self):
        scan = self.add_one_scan(self.scan_data).json

        res = self.app.get(config.SERVICE_SCAN_COLLECTION + '/' + str(scan['number'])).json
        self.assert_dict_subset(self.scan_data, res)

    def test_404_scan(self):
        """
        A missing scan should issue a proper NotFound response
        and a malformed requests should result in a 400
        """
        self.app.get(config.SERVICE_SCAN_COLLECTION + '/11234', status=404)
        self.app.get(config.SERVICE_SCAN_COLLECTION + '/a', status=400)

    def test_move_scan_forward(self):
        """
        We insert 5 scans and then move the second one to the last place.
        S=Source, D=Destination

        +---+---+---+---+---+
        |   | S |   |   | D |
        +---+---+---+---+---+
        """
        scans = self.add_five_scans()
        self.assertEqual(
            [a['sequenceNumber'] for a in scans], [1, 2, 3, 4, 5])
        pre_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json
        url = localurl(scans[1]['URL']) + '/move'
        self.app.post(url, {'after': 5})
        post_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json
        # Ensure result is sorted
        numbers = [a['sequenceNumber'] for a in pre_result['results']]
        self.assertEqual(numbers, sorted(numbers))

        ids_before = [a['number'] for a in pre_result['results']]
        ids_after = [a['number'] for a in post_result['results']]
        self.assertEqual(ids_before[2], ids_after[1])  # Three elements
        self.assertEqual(ids_before[3], ids_after[2])  # should be shifted
        self.assertEqual(ids_before[4], ids_after[3])  # to the left.
        self.assertEqual(ids_before[0], ids_after[0])  # Leave him alone!

        # And the target element should have reached its position
        self.assertEqual(ids_before[1], ids_after[4])

        # now try to move a scan to some place in the middle
        pre_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        url = localurl(pre_result[1]['URL']) + '/move'
        self.app.post(url, {'after': 3})
        post_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        # we moved this scan after number 3, but the previous
        self.assertEqual(pre_result[1]['number'], post_result[2]['number'])
        self.assertEqual(post_result[2]['sequenceNumber'], 3)

    def test_move_scan_backward(self):
        """
        We insert 5 scans and then move the last one to the second place.
        S=Source, D=Destination

        +---+---+---+---+---+
        |   | D |   |   | S |
        +---+---+---+---+---+
        """
        scans = self.add_five_scans()
        pre_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json
        url = localurl(scans[4]['URL']) + '/move'
        self.app.post(url, {'after': 1})
        post_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json
        numbers = [a['sequenceNumber'] for a in post_result['results']]
        self.assertEqual(numbers, sorted(numbers))
        ids_before = [a['number'] for a in pre_result['results']]
        ids_after = [a['number'] for a in post_result['results']]
        self.assertEqual(ids_before[0], ids_after[0])  # Leave him alone!
        self.assertEqual(ids_before[1], ids_after[2])  # Three elements
        self.assertEqual(ids_before[2], ids_after[3])  # should be shifted
        self.assertEqual(ids_before[3], ids_after[4])  # to the right.

        # And the target element should have reached its position
        self.assertEqual(ids_before[4], ids_after[1])

    def test_contiguity_of_sequence_number(self):
        # We move scans in many ways, and check
        # for contigiuity of the position attribute
        def assertNoDuplicatePosition():
            pg_result = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json
            solr_result = self.solr_scan.search(q='*:*').documents
            sortkey = lambda x: x['sequenceNumber']
            solr_result.sort(key=sortkey)
            # get a list of ids sorted by respective sequenceNumbers
            pg_ids = [el['number'] for el in sorted(pg_result['results'], key=sortkey)]
            solr_ids = [el['number'] for el in sorted(solr_result, key=sortkey)]
            # Ensure the solr and postgresql are aligned
            self.assertEqual(pg_ids, solr_ids)

            for result in (pg_result['results'], solr_result):
                positions = [a['sequenceNumber'] for a in result]
                self.assertEqual(positions, range(1, 16))

        scans = []
        scans += self.add_five_scans()
        scans += self.add_five_scans()
        scans += self.add_five_scans()
        assertNoDuplicatePosition()

        url = localurl(scans[0]['URL']) + '/move'

        self.app.post(url, {'after': 0})
        assertNoDuplicatePosition()

        self.app.post(url, {'after': 15})
        assertNoDuplicatePosition()

        self.app.post(url, {'after': 15})
        assertNoDuplicatePosition()

        url = localurl(scans[-1]['URL']) + '/move'
        self.app.post(url, {'after': 0})
        assertNoDuplicatePosition()

        self.app.post(url, {'after': 0})
        assertNoDuplicatePosition()

        self.app.post(url, {'after': 5})
        assertNoDuplicatePosition()

        scans = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        scan7 = scans[6]
        self.assertEqual(scan7['sequenceNumber'], 7)
        url = localurl(scan7['URL'] + '/move')
        self.app.post(url, {'after': 7})
        assertNoDuplicatePosition()

        scans = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        scan7 = scans[6]
        self.assertEqual(scan7['sequenceNumber'], 7)
        url = localurl(scan7['URL'] + '/move')
        self.app.post(url, {'after': 7})
        assertNoDuplicatePosition()

        scans = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        scan7 = scans[6]
        self.assertEqual(scan7['sequenceNumber'], 7)
        url = localurl(scan7['URL'] + '/move')
        self.app.post(url, {'after': 7})
        assertNoDuplicatePosition()

        scans = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        scan7 = scans[6]
        self.assertEqual(scan7['sequenceNumber'], 7)
        url = localurl(scan7['URL'] + '/move')
        self.app.post(url, {'after': 6})
        assertNoDuplicatePosition()

        scans = self.app.get(config.SERVICE_SCAN_COLLECTION, self.search_data).json['results']
        scan7 = scans[6]
        self.assertEqual(scan7['sequenceNumber'], 7)
        url = localurl(scan7['URL'] + '/move')
        self.app.post(url, {'after': 8})
        assertNoDuplicatePosition()

        self.app.post(localurl(scans[3]['URL'] + '/move'), {'after': '5'})
        self.app.post(localurl(scans[5]['URL'] + '/move'), {'after': '5'})
        assertNoDuplicatePosition()

    def test_move_scan_invalid_after(self):
        scan = self.add_one_scan().json
        url = localurl(scan['URL']) + '/move'
        res = self.app.post(url, {'after': 'a'}, status=400).json
        self.assertEqual(res['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_move_scan_validation(self):
        """
        An error is raised if we ask to move a scan
        to a non-existent position
        """
        scans = self.add_five_scans()
        url = localurl(scans[1]['URL']) + '/move'
        self.app.post(url, {'after': 50}, status=400)

    def test_reject_unknown_fields_on_creation(self):
        "Unknown fields in scan creation raise a 400 error"
        result = self.add_one_scan(
            dict(self.scan_data, non_existent_field='foobar'), status=400).json
        expected = {'location': 'request',
                    'name': 'invalid_parameter',
                    'description': 'Unknown field: non_existent_field'}
        self.assertTrue(expected in result['errors'], result['errors'])

    def test_reject_unknown_fields_on_update(self):
        "Unknown fields when adding  a scan raise a 400 error"
        result = self.add_one_scan(self.scan_data)
        url = localurl(result.json['URL'])
        result = self.app.put(url,
            dict(self.scan_data, non_existent_field='foobar'), status=400)
        self.assertEqual(result.json['errors'][0]['name'], ERRORS.invalid_parameter.name)

        # also, URL should not be settable
        result = self.app.put(url,
            dict(self.scan_data, URL='foobar'), status=400)
        expected = {'location': 'postdata',
                    'description': 'Direct update not allowed',
                    'name': ERRORS.invalid_parameter.name,
                    }
        self.assertTrue(expected in result.json['errors'], result.json['errors'])

    def test_date_validator_on_create(self):
        """
        Same as :ref:`TestScans.test_date_validator_on_update`
        but on record creation
        """
        result = self.add_one_scan(
            dict(self.scan_data, timeFrameFrom='12'), status=400).json
        self.assertTrue({'location': 'request',
                         'name': 'invalid_parameter',
                         'description': 'timeFrameFrom: Invalid date'} in result['errors'], result['errors'])

    def test_completeness_of_result(self):
        "check if we get all our fields back"
        result = self.add_one_scan(self.scan_data).json
        url = localurl(result['URL'])
        # define some more or less arbitrary content
        data = {
            'archive_id': 2,
            'transcription': 'transcription_content',
            'date': '2012-10-23T09:48:04+00:00',
            'timeFrameFrom': '1800-03-02',
            'language': 'nl',
            'transcription': 'xxxx',

        }
        # put these data
        new_res = self.app.put(url, data).json
        # the data should be returned from the put
        self.assert_dict_subset(data, new_res)
        # if we now get the url, we should get all our data back
        new_res = self.app.get(url).json
        self.assert_dict_subset(data, new_res)

    def test_update_archive_id_moves_scanNumber(self):
        """
        check if scan position is updated when it's moved
        to a different collection (changing archive_id or archiveFile).
        Also check solr index stays in sync.
        """
        set1, set2 = [], []
        for _i in range(3):
            set1.append(self.add_one_scan(self.scan_data).json)
        set2_data = dict(self.scan_data, archiveFile='foo')
        for _i in range(3):
            set2.append(self.add_one_scan(set2_data).json)
        # We have two sets of scans. We move the second scan from set1 to set2
        url = localurl(set1[1]['URL'])
        self.app.put(url, dict(archiveFile='foo'))
        moved_scan = self.app.get(url).json
        self.assertEqual(moved_scan['sequenceNumber'], 4)

        pg_newset1 = self.app.get(config.SERVICE_SCAN_COLLECTION,
            dict(archiveFile='foo')).json['results']
        pg_newset2 = self.app.get(config.SERVICE_SCAN_COLLECTION,
            dict(archiveFile=self.scan_data['archiveFile'])).json['results']
        # Ensure sequenceNumbers have been updated
        self.assertEqual([a['sequenceNumber'] for a in pg_newset2], [1, 2])
        self.assertEqual([a['sequenceNumber'] for a in pg_newset1], [1, 2, 3, 4])
        solr_newset1 = self.solr_scan.search(
            q='archiveFile:' + 'foo').documents
        solr_newset2 = self.solr_scan.search(
            q='archiveFile:' + self.scan_data['archiveFile']).documents
        # Ensure sequenceNumbers have been updated
        self.assertEqual([a['sequenceNumber'] for a in solr_newset2], [1, 2])
        self.assertEqual([a['sequenceNumber'] for a in solr_newset1], [1, 2, 3, 4])

    def test_update_status(self):
        "changing status works only for valid values"
        result = self.add_one_scan(self.scan_data).json
        self.assertEqual(result['status'], 1)
        url = localurl(result['URL'])
        then = now()
        self.app.put(url, {'status': 2})
        result = self.app.get(url).json
        self.assertEqual(result['status'], 2)
        self.assertMoreRecent(result['dateLastModified'], then)

    def test_update_translationID(self):
        "translationID is correctly updated"
        result = self.add_one_scan(self.scan_data).json
        self.assertEqual(result.get('translationID'), None)
        url = localurl(result['URL'])
        then = now()
        self.app.put(url, {'translationID': 'Some new value'})
        result = self.app.get(url).json
        self.assertEqual(result['translationID'], 'Some new value')
        self.assertMoreRecent(result['dateLastModified'], then)

    def test_add_referential_integrity_archive_id(self):
        archive_id = get_archives(self)[0].id

        data = dict(self.scan_data, archive_id=archive_id)
        self.add_one_scan(data).json

        data = dict(self.scan_data, archive_id=2000)
        self.add_one_scan(data, status=400).json

        data = dict(self.scan_data, archive_id='a string')
        self.add_one_scan(data, status=400).json

    def test_update_referential_integrity_archive_id(self):

        archive_id = get_archives(self)[0].id

        data = dict(self.scan_data, archive_id=archive_id)
        self.add_one_scan(data).json

        data = dict(self.scan_data, archive_id=2000)
        self.add_one_scan(data, status=400).json

        data = dict(self.scan_data, archive_id='a string')
        self.add_one_scan(data, status=400).json

    def test_update_number_raises_error(self):
        "number and sequenceNumber are not (directly) mutable"
        result = self.add_one_scan(self.scan_data).json
        url = localurl(result['URL'])

        new_res = self.app.put(url, {'number': '12'}, status=400).json
        self.assertEqual(new_res['errors'][0]['name'], 'invalid_parameter')

        new_res = self.app.put(url, {'sequenceNumber': '12'}, status=400).json
        self.assertEqual(new_res['errors'][0]['name'], 'invalid_parameter')

    def test_date_validator_on_update(self):
        """
        `12` and `2012-13-15` are not good values for a date,
        but 2012-09-15 is.
        """
        result = self.add_one_scan(self.scan_data).json
        url = localurl(result['URL'])
        new_res = self.app.put(url,
            {'timeFrameFrom': '12'}, status=400).json
        self.assertEqual(new_res['status'], 'error')
        new_res = self.app.put(url,
            {'timeFrameFrom': '2012-13-15'}, status=400).json
        new_res = self.app.put(url,
            {'timeFrameFrom': '2012-09-15'}).json

    def test_update_status_to_0_raises_an_error(self):
        "A scan `status` can't be updated directly"
        result = self.add_one_scan(self.scan_data).json
        url = localurl(result['URL'])
        new_res = self.app.put(url, {'status': 0}, status=400).json
        self.assertEqual(new_res['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_create_with_status_0_raises_an_error(self):
        scan_data = dict(self.scan_data)
        scan_data['status'] = 0
        result = self.add_one_scan(scan_data, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_error_if_new_scan_file_is_not_an_image(self):
        "If a new file is not a TIFF, GIF, PNG or JPEG a 400 error is raised"
        res = self.add_one_scan(filecontents="Silly text", status=400)
        self.assertEqual(res.json['errors'][0]['name'], 'invalid_file')

    def test_error_if_updated_scan_file_is_not_an_image(self):
        "If an updated file is not a TIFF, GIF, PNG or JPEG a 400 error is raised"
        scan = self.add_one_scan()
        url = localurl(scan.json['URL'])
        filetuple = ('file', 'test_fn', "silly text")
        res = self.app.put(url, upload_files=[filetuple], status=400)
        self.assertEqual(res.json['errors'][0]['name'], 'invalid_file')

    def test_upload_valid_files(self):
        "The uploaded scan must be either TIFF, GIF, PNG or JPEG"
        self.add_one_scan(filecontents=TEST_IMAGE_TIF)
        self.add_one_scan(filecontents=TEST_IMAGE_GIF)
        self.add_one_scan(filecontents=TEST_IMAGE_JPG)
        self.add_one_scan(filecontents=TEST_IMAGE_PNG)

    def test_wrong_file_variable_create(self):
        "Give a proper error code when the file parameter is not a file"
        scan_data = dict(self.scan_data, file="A string")
        res = self.app.post(config.SERVICE_SCAN_COLLECTION, scan_data, status=400)
        self.assertEqual(res.json['errors'][0]['name'], 'missing_file')

    def test_wrong_file_variable_update(self):
        "Give a proper error code when the file parameter is not a file"
        scan = self.add_one_scan()
        url = localurl(scan.json['URL'])
        scan_data = dict(self.scan_data, file="A string")
        res = self.app.put(url, scan_data, status=400)
        self.assertEqual(res.json['errors'][0]['name'], 'missing_file')

    def test_persistency(self):
        """test if indeed all properties arrive safely after searching"""
        original = self.add_one_scan().json
        # if we get the single file from its url directly, the results should be the same
        direct_result = self.app.get(original['URL']).json
        self.assert_dict_equality(original, direct_result)
        # search_result comes from SOLR
        search_result = self.app.get(config.SERVICE_SCAN_COLLECTION).json['results'][0]
        self.assert_dict_equality(original, search_result)


class TestScanSearchBase(BaseRepoTest):
    # add some scans
    def add_scan(
        self,
        archiveFile=None,
        archive_id=None,
        status=None,
        date=None,
        folioNumber=None,
        originalFolioNumber=None,
        timeFrameFrom=None,
        timeFrameTo=None,
        transcription=None,
    ):
        scan_data = dict(self.scan_data)
        if archiveFile:
            scan_data['archiveFile'] = archiveFile
        if archive_id:
            scan_data['archive_id'] = archive_id
        if status:
            scan_data['status'] = status
        if date:
            scan_data['date'] = date
        if folioNumber:
            scan_data['folioNumber'] = folioNumber
        if originalFolioNumber:
            scan_data['originalFolioNumber'] = originalFolioNumber
        if timeFrameFrom:
            scan_data['timeFrameFrom'] = timeFrameFrom
        if timeFrameTo:
            scan_data['timeFrameTo'] = timeFrameTo
        if transcription:
            scan_data['transcription'] = transcription

        return self.add_one_scan(scan_data, enabled_web_chat=False).json

    def setUp(self):
        super(TestScanSearchBase, self).setUp()

        # now get some archive
        self.archive1 = get_archive(self, archive_id=1).to_dict()
        self.archive2 = get_archive(self, archive_id=2).to_dict()
        self.archive3 = get_archive(self, archive_id=6).to_dict()
        # Make sure we don't choose two archives from the same institution
        # to make examples more interesting
        self.assertNotEqual(self.archive2['institution'], self.archive3['institution'])

        # we add 5 scans
        self.scan = self.add_scan(archive_id=1)
        self.scan1 = self.add_scan(archive_id=1, archiveFile='another_repo')
        self.scan2 = self.add_scan(archive_id=2, archiveFile='another_repo', status=2, folioNumber='3')
        self.scan3 = self.add_scan(archive_id=2, archiveFile='another_repo', date='1603-01-01', folioNumber='4', originalFolioNumber='314159')
        self.scan4 = self.add_scan(archive_id=6, archiveFile='repo4', date='1603-03-03', timeFrameFrom='1603-03-03', timeFrameTo='1603-04-03')


class TestScanSearch(TestScanSearchBase):
    def test_general_data_sanity(self):
        scan = self.scan
        self.assertTrue(self.scan1['number'])
        self.assertNotEqual(scan['URL'], self.scan1['URL'])
        self.assertTrue('http' in scan['URL'])

    def test_search_for_archiveFile(self):
        scan = self.scan
        search_data = {
            'archiveFile': scan['archiveFile'],
        }
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, search_data).json
        elements = result['results']
        # ensure only one scan is returned
        # (the other one is in a different repo)
        self.assertEqual(len(elements), 1)
        self.assert_dict_equality(elements[0], scan)
        # Check other required values
        self.assertEqual(result['total_results'], 1)
        self.assertEqual(result['end'], 1)
        self.assertEqual(result['query_used'], search_data)

    def test_search_for_archiveFiles(self):
        url = config.SERVICE_SCAN_COLLECTION
        result = self.app.get(url, {'archiveFile_raw': 'another_repo'}).json
        elements = result['results']
        self.assertEqual(len(elements), 3)
        result = self.app.get(url, {'archiveFile_raw': 'repo4'}).json
        elements = result['results']
        self.assertEqual(len(elements), 1)
        result = self.app.get(url, {'archiveFile_raw': '[another_repo TO repo4]'}).json
        elements = result['results']
        self.assertEqual(len(elements), 4)
        result = self.app.get(url, {'archiveFile_raw': '(another_repo OR repo4)'}).json
        elements = result['results']
        self.assertEqual(len(elements), 4)

    def test_searching_for_archive_id(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archive_id': 2}).json
        self.assertEqual(result['total_results'], 2)

    def test_searching_for_archive(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archive': self.archive2['archive']}).json
        self.assertEqual(result['total_results'], 2)

    def test_searching_for_institution(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION,
            {'institution': self.archive1['institution']}).json
        self.assertEqual(result['total_results'], 4)

    def test_searching_for_another_institution(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION,
            {'institution': self.archive3['institution']}).json
        self.assertEqual(result['total_results'], 1)

    def test_searching_for_status(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'status': 2}).json
        self.assertEqual(result['total_results'], 1)

    def test_search_in_timeframe(self):

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '1603-3-5'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '1603-3-3'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '1603-4-3'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '1600-4-3'}).json
        self.assertEqual(result['total_results'], 0)

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '2012-09-10'}).json
        self.assertEqual(result['total_results'], 4)

        scan_data = dict(self.scan_data)
        scan_data['timeFrameFrom'] = '2000-01-01'
        self.add_one_scan(scan_data=scan_data)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '2000-01-01'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrame': '2000-1-1'}).json
        self.assertEqual(result['total_results'], 1)

        # test with several timeFrames
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrames': ['2000-01-01', '1603-4-3']},).json
        self.assertEqual(result['total_results'], 2)
        # test with several timeFrames
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrames': ['2000-01-01', '1603-4-3']},).json
        self.assertEqual(result['total_results'], 2)

        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'timeFrames': ['2000-01-01']},).json
        self.assertEqual(result['total_results'], 1)

    def test_searching_for_folionumber(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'folioNumber': '3'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'folioNumber': '4'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'folioNumber': '33333'}).json
        self.assertEqual(result['total_results'], 0)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'folioNumbers': '["2", "3", "4"]'}).json
        self.assertEqual(result['total_results'], 2)

    def test_searching_for_originalFolionumber(self):
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'originalFolioNumber': '314159'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(config.SERVICE_SCAN_COLLECTION, {'originalFolioNumber': 'not-existing'}).json
        self.assertEqual(result['total_results'], 0)

    def test_image_url(self):
        response = self.app.get(config.SERVICE_SCAN_COLLECTION)
        results = response.json['results']

        some_scan = results[2]
        # test if image_url is key
        self.assertTrue('image_url' in some_scan)
        # image_url should result in the same image as image/file
        img1 = self.app.get(localurl(some_scan['URL']) + '/image').body
        img2 = self.app.get(localurl(some_scan['image_url'])).body
        self.assertEqual(img1, img2)

    def test_archivefile_scan_count(self):
        url_archivefile = config.SERVICE_ARCHIVEFILE_ITEM.format(**self.scan)
        response = self.app.get(url_archivefile)
        self.assertEqual(response.json['number_of_scans'], 1)

        scan = self.add_scan(archiveFile=self.scan['archiveFile'], archive_id=self.scan['archive_id'], folioNumber='2')
        response = self.app.get(url_archivefile)
        self.assertEqual(response.json['number_of_scans'], 2)

        # now remove a scan
        url_scan = config.SERVICE_SCAN_ITEM.format(**self.scan)
        self.app.delete(url_scan)
        response = self.app.get(url_archivefile)
        self.assertEqual(response.json['number_of_scans'], 1)

        # now add it again
        scan = self.add_scan(archiveFile=self.scan['archiveFile'], archive_id=self.scan['archive_id'], folioNumber='3')
        response = self.app.get(url_archivefile)
        self.assertEqual(response.json['number_of_scans'], 2)
        # if we update the scan, our number should go down again
        url_scan = config.SERVICE_SCAN_ITEM.format(**scan)
        self.app.put(url_scan, {'archiveFile': 'something_else'})
        response = self.app.get(url_archivefile)
        self.assertEqual(response.json['number_of_scans'], 1)


class TestDeleteScans(BaseRepoTest):
    def setUp(self):
        super(TestDeleteScans, self).setUp()
        self.scan_data['archive_id'] = '2'  # don't use the same as the one from add_one_ead()
        self.add_five_scans(archiveFile='a1')
        self.add_five_scans(archiveFile='a2')
        self.add_one_ead()

    def test_delete_all_scans_with_an_archivefile(self):

        # check sanity
        archive_id = self.scan_data['archive_id']
        res = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archiveFile': 'a1'}).json
        self.assertEqual(res['total_results'], 5)
        res = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archiveFile': 'a2'}).json
        self.assertEqual(res['total_results'], 5)

        # now we delete all scans with archiveFile a2
        url = config.SERVICE_UTILS_SCAN_DELETE

        self.app.post(config.SERVICE_UTILS_SCAN_DELETE, params={'archiveFile': 'a2', 'archive_id': archive_id, 'user': 'some_user'})
        # test the logging
        # self.reset_events_log()
        # self.assertEqual(len(self.events_log), 5, self.events_log)
        # self.assertEqual(self.events_log[-1]['object_type'], 'scan')
        # self.assertEqual(self.events_log[-1]['message'], 'delete')
        # self.assertEqual(self.events_log[-1]['user'], 'some_user')

        # a1 should be untouched, a2 should have no scans anymore
        res = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archiveFile': 'a1'}).json
        self.assertEqual(res['total_results'], 5)
        res = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archiveFile': 'a2'}).json
        self.assertEqual(res['total_results'], 0)

        # a2 should also be removed from the list of archiveFiles
        response = self.app.get('/archivefiles', {'archiveFile': 'a1'})
        self.assertEqual(response.json['total_results'], 1)
        response = self.app.get('/archivefiles', {'archiveFile': 'a2'})
        self.assertEqual(response.json['total_results'], 0)

        # check if we indeed reaise errors if all parameters are not given...
        result = self.app.post(url, {'archiveFile': 'a2', }, expect_errors=True)
        self.assertEqual(result.json['errors'][0]['name'], ERRORS.invalid_parameter.name)
        result = self.app.post(url, {'archive_id': archive_id}, expect_errors=True)
        self.assertEqual(result.json['errors'][0]['name'], ERRORS.invalid_parameter.name)

        # try to remove the archivefile a second time
        result = self.app.post(config.SERVICE_UTILS_SCAN_DELETE, params={'archiveFile': 'a2', 'archive_id': archive_id})
        self.assertTrue(result.json['success'], 'True')
