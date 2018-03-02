# encoding=utf8
#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


"""
Tests for EAD CRUD and validation
"""
import re
import copy
from textwrap import dedent

from base import BaseRepoTest
from restrepo.tests.base import localurl
from restrepo.indexes.ead import get_ead_files
from restrepo.config import status, ERRORS
from restrepo.indexes import reindex_all
from restrepo import config


class TestArchiveFile(BaseRepoTest):

    def setUp(self):
        super(TestArchiveFile, self).setUp()
        self.ARCHIVE_FILE_ID_3 = 'ARCHIVE_FILE_ID_3 [with square brackets]'

    def test_get_archive_file_ids(self):
        """This service is obsolete, and replaced bh /archivefiles

        This is the original test: we keep it to garantee backwards compatibilty (or at least know when we break it or disable it)
        """
        def expected_helper(res):
            return [x['archiveFile'] for x in res['results']]

        url = config.SERVICE_ARCHIVE_FILE_ID
        ARCHIVE_FILE_ID_3 = self.ARCHIVE_FILE_ID_3

        res = self.add_one_ead(dontlog=True).json
        ead_id_1 = res['ead_id']
        archive_id_1 = res['archive_id']
        res_1 = self.app.get(url, {'ead_id': ead_id_1}).json
        self.assertEqual(expected_helper(res_1), ['ARCHIVE_FILE_ID'])

        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        res = self.add_one_ead(filecontents=filecontents, filename='1.xml', dontlog=True).json
        ead_id_2 = res['ead_id']
        archive_id_2 = res['archive_id']
        res_2 = self.app.get(url, {'ead_id': ead_id_2}).json
        self.assertEqual(expected_helper(res_2), [
            'ARCHIVE_FILE_ID_1', 'ARCHIVE_FILE_ID_2', ARCHIVE_FILE_ID_3
        ])

        # check sanity: both ead files have the same archive_id
        self.assertEqual(archive_id_1, archive_id_2)

        # expect the results to be the archive_file_ids both files combined
        res = self.app.get(url, {'archive_id': archive_id_1}).json
        self.assertEqual(len(res['results']), len(res_1['results'] + res_2['results']))

        # changing the cXX tags into <c> tags should not change the result
        filecontents = re.sub('c0[0-9]', 'c', filecontents)
        res = self.add_one_ead(filecontents=filecontents,
            filename='2.xml', dontlog=True).json
        ead_id_3 = res['ead_id']
        res_3 = self.app.get(url, {'ead_id': ead_id_3}).json
        self.assertEqual(expected_helper(res_3), [
            'ARCHIVE_FILE_ID_1', 'ARCHIVE_FILE_ID_2', ARCHIVE_FILE_ID_3
        ])

        # check sanity: we should now find 3 files with this archive_id
        ead_files = get_ead_files(context=self, archive_id=archive_id_1)
        self.assertEqual(len(ead_files), 3)
        # but the list of searching for archive_id remains the same as before
        # because we filter duplicates
        res = self.app.get(url, {'archive_id': archive_id_1}).json
        self.assertEqual(len(res['results']), len(res_1['results'] + res_2['results']))

        # we create a duplicate archive File ID
        filecontents = filecontents.replace(self.ARCHIVE_FILE_ID_3, 'ARCHIVE_FILE_ID_2')

        # if not parameters are given, we should get an error
        res = self.app.get(url, status=400).json
        self.assertEqual(res['errors'][0]['location'], 'querystring')

    def test_get_archivefiles_from_ead(self):
        def expected_helper(res):
            return [x['archiveFile'] for x in res]

        url = config.SERVICE_ARCHIVEFILE_COLLECTION

        res = self.add_one_ead(dontlog=True).json
        ead_id_1 = res['ead_id']
        archive_id_1 = res['archive_id']
        res_1 = self.app.get(url, {'ead_id': ead_id_1}).json
        self.assertEqual(expected_helper(res_1['results']), ['ARCHIVE_FILE_ID'])

        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        res = self.add_one_ead(filecontents=filecontents,
            filename='1.xml', dontlog=True).json
        ead_id_2 = res['ead_id']
        archive_id_2 = res['archive_id']
        res_2 = self.app.get(url, {'ead_id': ead_id_2}).json
        self.assertEqual(expected_helper(res_2['results']), [
            'ARCHIVE_FILE_ID_1', 'ARCHIVE_FILE_ID_2', self.ARCHIVE_FILE_ID_3
        ])

        # check sanity: both ead files have the same archive_id
        self.assertEqual(archive_id_1, archive_id_2)

        # expect the results to be the archive_file_ids of both files combined
        res = self.app.get(url, {'archive_id': archive_id_1}).json
        self.assertEqual(res['results'], res_1['results'] + res_2['results'])

        # changing the cXX tags into <c> tags should not change the result
        filecontents = re.sub('c0[0-9]', 'c', filecontents)
        res = self.add_one_ead(filecontents=filecontents,
            filename='2.xml', dontlog=True).json
        ead_id_3 = res['ead_id']
        res_3 = self.app.get(url, {'ead_id': ead_id_3}).json
        self.assertEqual(expected_helper(res_3['results']), [
            'ARCHIVE_FILE_ID_1', 'ARCHIVE_FILE_ID_2', self.ARCHIVE_FILE_ID_3
        ])

        # check sanity: we should now find 3 files with this archive_id
        ead_files = get_ead_files(context=self, archive_id=archive_id_1)
        self.assertEqual(len(ead_files), 3)
        # but the list of searching for archive_id remains the same as before
        # because we filter duplicates
        res = self.app.get(url, {'archive_id': archive_id_1}).json
        self.maxDiff = 5000
        self.assertItemsEqual(expected_helper(res['results']), expected_helper(res_1['results'] + res_2['results']))

        # if we delete an ead file, we should also not find our archivefiles anymore

    def test_get_archivefiles_from_scan(self):
        url = config.SERVICE_ARCHIVEFILE_COLLECTION

        scandata = self.add_one_scan(self.scan_data, dontlog=True).json

        res_3 = self.app.get(url).json
        result = res_3['results'][0]
        self.assertEqual(result['archive_id'], self.scan_data['archive_id'])
        self.assertEqual(result['archiveFile'], self.scan_data['archiveFile'])

        # now if we delete this scan, we should also not find this archiveFile int he list sanymore
        archivefiles_before_delete = res_3['results']
        self.app.delete(localurl(scandata['URL']))
        res_3 = self.app.get(url).json
        archivefiles_after_delete = res_3['results']
        self.assertEqual(len(archivefiles_after_delete), len(archivefiles_before_delete) - 1)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_get_archivefile(self):
        scandata = self.add_one_scan(self.scan_data, dontlog=True).json
        url = config.SERVICE_ARCHIVEFILE_ITEM.replace('{archive_id}', str(scandata['archive_id'])).replace('{archiveFile}', scandata['archiveFile'])
        response = self.app.get(url)
        self.assertEqual(response.status_code, 200)

        url = config.SERVICE_ARCHIVEFILE_ITEM.replace('{archive_id}', 'x').replace('{archiveFile}', 'y')
        response = self.app.get(url, status=400)
        # we expect a 400 Bad request, because 'x' isnot a number
        self.assertEqual(response.status_code, 400)

        url = config.SERVICE_ARCHIVEFILE_ITEM.replace('{archive_id}', str(scandata['archive_id'])).replace('{archiveFile}', 'y')
        response = self.app.get(url, status=404)
        # we expect a 404 Not found
        self.assertEqual(response.status_code, 404)

    def test_archive_file_id_with_spaces(self):
        scandata = copy.deepcopy(self.scan_data)
        scandata['archiveFile'] = 'xxx y'
        # we changed the behavior - archiveFile with spaces are allowed after all
        scandata = self.add_one_scan(scandata, dontlog=True, status=200).json
        # now we expect to find our archiveFile at its URL
        url = config.SERVICE_ARCHIVEFILE_ITEM.format(**scandata)
        self.app.get(url, status=200)

    def test_get_archivefiles_returned_results_are_ok(self):
        """test if the datamodel is as we expect it"""

        url = config.SERVICE_ARCHIVEFILE_COLLECTION
        expected_keys = [
            'archive_id',
            'status',
            'archiveFile',
            'number_of_scans',
            'ead_ids',
            'URL',
            'id',
            'title',
            'titles',
        ]

        # archivefiles from ead
        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        self.add_one_ead(filecontents=filecontents, filename='1.xml', dontlog=True).json

        response = self.app.get(url)

        self.assertEqual(set(response.json['results'][0].keys()), set(expected_keys))
        self.assertEqual(response.json['results'][0]['title'], 'Original Letter')
        self.assertEqual(response.json['results'][0]['titles'], {u'en': u'Original Letter'})
        self.assertEqual(response.json['results'][0]['id'], '3/ARCHIVE_FILE_ID_1')

        # now we add a scan to one fo the archive files of the ead
        scan_data = self.scan_data
        first_component = response.json['results'][0]
        scan_data['archiveFile'] = first_component['archiveFile']
        scan_data['archive_id'] = first_component['archive_id']

        # archivefiles from scan
        scandata = self.add_one_scan(self.scan_data).json

        response = self.app.get(url, {'archive_id': scandata['archive_id']})
        self.assertEqual(set(response.json['results'][0].keys()), set(expected_keys))
        self.assertEqual(response.json['results'][0]['title'], 'Original Letter')
        self.assertEqual(response.json['results'][0]['titles'], {'en': 'Original Letter'})

    def test_sorting_of_archivefiles(self):
        # archive files should, by default, be sorted by id, but taking account of numeric values
        # so we expect this order:
        # 9/9
        # 9/10
        # 10/9
        # 10/10
        # a/a
        for archive_id, archiveFile in [
            (3, 'a'),
            (3, '10'),
            (3, '9'),
            ]:
            scan_data = copy.copy(self.scan_data)
            scan_data['archive_id'] = archive_id
            scan_data['archiveFile'] = archiveFile
            self.add_archivefile(scan_data)

        url = config.SERVICE_ARCHIVEFILE_COLLECTION
        response = self.app.get(url)
        results = response.json['results']
        results = [archivefile['id'] for archivefile in results]
        expected_results = [u'3/9', u'3/10', u'3/a']

        self.assertEqual(results, expected_results)

    def test_get_archivefiles_search(self):
        """test if all search parameters are behaving as expected"""

        # add an EAD that has some archive files defined
        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        ead_data = self.add_one_ead(filecontents=filecontents,
            filename='1.xml', dontlog=True).json

        # also add an archive file by adding a scan
        scan_data = copy.deepcopy(self.scan_data)  # make a copy, so we don't poison any later tests
        scan_data['archiveFile'] = 'something_unique'
        scan_data['archive_id'] = 9
        scan_data = self.add_one_scan(scan_data, dontlog=True).json

        # we have the following search parameters that should work:
        # * **archive_id:**
        #    return archivefiles that are refenced by the archive identified by archive_id
        # * **archiveFile:**
        #    return the archivefile with this id
        # * **has_scans:**
        #    if the value of *has_scans* is True, then return only archivefiles
        #    that are referenced by one or more scans
        # * **status:**
        #    a status: a value among :ref:`status_values` (except 0)
        # * **start:**
        #    index of the first element returned (used in pagination)
        # * **limit:**
        #    max # of objects to return
        #
        url = config.SERVICE_ARCHIVEFILE_COLLECTION
        response = self.app.get(url)
        a0 = response.json['results'][0]
        a1 = response.json['results'][1]
        a2 = response.json['results'][2]
        a3 = response.json['results'][3]

        self.assertEqual(response.json['total_results'], 4)
        self.assertEqual(len([x for x in response.json['results'] if x['status'] == status.NEW]), 4)

        response = self.app.get(url, {'archive_id': scan_data['archive_id']})
        self.assertEqual(response.json['total_results'], 1)

        response = self.app.get(url, {'archiveFile': scan_data['archiveFile']})
        self.assertEqual(response.json['total_results'], 1)

        response = self.app.get(url, {'archiveFile': scan_data['archiveFile']})
        self.assertEqual(response.json['total_results'], 1)

        # we can pass multiple values for archiveFile
        response = self.app.get(url, {'archiveFile': [a1['archiveFile'], a2['archiveFile']]})
        self.assertEqual(response.json['total_results'], 2)

        response = self.app.get(url, {'archiveFile': [a1['archiveFile'], a2['archiveFile'], a3['archiveFile']]})
        self.assertEqual(response.json['total_results'], 3)

        response = self.app.get(url, {'ead_id': ead_data['ead_id']})
        self.assertEqual(response.json['total_results'], 3)

        response = self.app.get(url, {'has_scans': False})
        self.assertEqual(response.json['total_results'], 3)

        response = self.app.get(url, {'has_scans': True})
        self.assertEqual(response.json['total_results'], 1)

        response = self.app.get(url, {'status': status.NEW})
        self.assertEqual(response.json['total_results'], 4)

        item_url = localurl(response.json['results'][0]['URL'])
        response = self.app.put(item_url, {'status': status.PUBLISHED})
        self.assertEqual(response.json['status'], status.PUBLISHED)
        response = self.app.get(url, {'status': status.PUBLISHED})
        self.assertEqual(response.json['total_results'], 1)
        response = self.app.get(url)
        self.assertEqual(len([x for x in response.json['results'] if x['status'] == status.NEW]), 3)
        self.assertEqual(len([x for x in response.json['results'] if x['status'] == status.PUBLISHED]), 1)

        range_value = '[{a1[archiveFile]} TO {a3[archiveFile]}]'.format(**locals())
        response = self.app.get(url, {'archiveFile': range_value})
        self.assertEqual(response.json['total_results'], 3)
        range_value = '[{a0[archiveFile]} TO {a3[archiveFile]}]'.format(**locals())
        response = self.app.get(url, {'archiveFile': range_value})
        self.assertEqual(response.json['total_results'], 4)
        range_value = '[{a2[archiveFile]} TO {a3[archiveFile]}]'.format(**locals())
        response = self.app.get(url, {'archiveFile': range_value})

        range_value = '[{a0[archiveFile]} TO {a2[archiveFile]}]'.format(**locals())
        response = self.app.get(url, {'archiveFile': [range_value, a3['archiveFile']]})
        self.assertEqual(response.json['total_results'], 4)

        range_value = '[{a0[archiveFile]} TO {a1[archiveFile]}]'.format(**locals())
        response = self.app.get(url, {'archiveFile': [range_value, a3['archiveFile']]})
        self.assertEqual(response.json['total_results'], 3)

    def add_archivefile(self, scan_data=None):
        """add an archivefile, return a json representing it"""
        url = config.SERVICE_ARCHIVEFILE_COLLECTION
        if not scan_data:
            scan_data = self.scan_data

        self.add_one_scan(scan_data, dontlog=True).json
        res_3 = self.app.get(url).json
        result = res_3['results'][0]

        scan_data['user'] = 'someuser'
        self.add_one_scan(scan_data, dontlog=False).json
        return result

    def test_archivefile_item_post(self):
        url = self.add_archivefile()['URL']
        url = localurl(url)

        # test if POST requests are picked up as well
        response = self.app.post(url, {'status': status.NEW})
        self.assertEqual(response.json['status'], status.NEW)
        # check if our response is the same as the one we GET
        self.assertEqual(self.app.get(url).json, response.json)

        response = self.app.post(url, {'status': status.PUBLISHED})
        self.assertEqual(response.json['status'], status.PUBLISHED)
        # check if our response is the same as the one we GET
        self.assertEqual(self.app.get(url).json, response.json)

        # test logging
        self.reset_events_log()
        response = self.app.post(url, {'status': status.NEW, 'user': 'someuser'})
        self.assertEqual(response.json['status'], status.NEW)

        # check if our response is the same as the one we GET
        self.assertEqual(self.app.get(url).json, response.json)

        # self.assertEqual(len(self.events_log), 1)
        # self.assertEqual(self.events_log[-1]['user'], 'someuser')

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_add_archivefile(self):
        url = self.add_archivefile()['URL']
        url = localurl(url)

        # default status should be NEW
        response = self.app.get(url)
        self.assertEqual(response.json['status'], status.NEW)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_get_archivefiles_paging(self):
        def expected_helper(res):
            return [x['archiveFile'] for x in res]

#        res = self.add_one_ead(dontlog=True).json
        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        self.add_one_ead(filecontents=filecontents, filename='1.xml', dontlog=True).json

        url = config.SERVICE_ARCHIVEFILE_COLLECTION

        response = self.app.get(url)
        self.assertEqual(response.json['total_results'], 3)
        self.assertEqual(len(response.json['results']), 3)
        self.assertEqual(response.json['start'], 0)
        self.assertEqual(response.json['end'], 3)

        response = self.app.get(url, {'limit': 2})
        self.assertEqual(response.json['total_results'], 3)
        self.assertEqual(response.json['start'], 0)
        self.assertEqual(response.json['end'], 2)
        self.assertEqual(len(response.json['results']), 2)
        response = self.app.get(url, {'start': 1})
        self.assertEqual(response.json['total_results'], 3)
        self.assertEqual(len(response.json['results']), 2)
        self.assertEqual(response.json['start'], 1)
        self.assertEqual(response.json['end'], 3)

    def test_edit_archivefile_from_scan(self):
        # add an archive file via a scan
        scandata = self.add_one_scan(self.scan_data).json
        # find the archive file
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        response = self.app.get(collection_url, {'archive_id': scandata['archive_id'], 'archiveFile': scandata['archiveFile']})
        # sanity
        self.assertEqual(response.json['total_results'], 1)
        # get the url of the archivefile
        item_url = response.json['results'][0]['URL']
        item_url = localurl(item_url)
        self._test_edit_archivefile(item_url)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def _test_edit_archivefile(self, item_url):
        response = self.app.get(item_url)
        # default value for status is status_values.NEW
        self.assertEqual(response.json['status'], status.NEW)

        # now set it to "status=True"
        self.app.put(item_url, {'status': 1})
        # test if it 'took'
        response = self.app.get(item_url)
        self.assertEqual(response.json['status'], 1)

        # if we add no data at all, we should keep the old value
        self.app.put(item_url)

        # test if it 'took'
        response = self.app.get(item_url)
        self.assertEqual(response.json['status'], 1)

        self.app.put(item_url, {'status': 2})
        response = self.app.get(item_url)
        self.assertEqual(response.json['status'], 2)

        response = self.app.put(item_url, {'status': 0})
        self.assertEqual(response.json['status'], 0)
        response = self.app.get(item_url)
        self.assertEqual(response.json['status'], 0)

    def test_edit_archivefile_from_ead(self):
        #
        # same as test_edit_archivefile_from_scan,
        ead_data = self.add_one_ead(dontlog=True).json
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        response = self.app.get(collection_url, {'ead_id': ead_data['ead_id']})
        # sanity
        self.assertEqual(response.json['total_results'], 1)
        # get the url of the archivefile
        item_url = response.json['results'][0]['URL']
        item_url = localurl(item_url)
        self._test_edit_archivefile(item_url)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_archivefile_deleting(self):
        # add an archive file via a scan
        scandata = self.add_one_scan(self.scan_data).json
        # find the archive file
        collection_url = localurl(config.SERVICE_ARCHIVEFILE_COLLECTION)
        response = self.app.get(collection_url, {'archive_id': scandata['archive_id'], 'archiveFile': scandata['archiveFile']})
        # sanity
        self.assertEqual(response.json['total_results'], 1)
        # get the url of the archivefile
        item_url = response.json['results'][0]['URL']
        item_url = localurl(item_url)
        # deleting the archivefile shoudl raise an error, because it has scans
        response = self.app.delete(item_url, status=400)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['errors'][0]['name'], ERRORS.archivefile_has_scans.name)

        # delete the scan
        self.app.delete(localurl(scandata['URL']))

        # now the archive file does not exist anymore (because it is deleted with the scan)
        response = self.app.delete(item_url, status=404)

        # we add our scan back
        scandata = self.add_one_scan(self.scan_data).json
        # we edit our item, thus creating a database record
        self.app.put(item_url, {'status': 1})
        self.app.delete(localurl(scandata['URL']))

        # and it is really gone
        self.app.get(item_url, status=404)

        # TODO: add this test: the same exercise with an EAD file

    def test_if_archivefiles_are_identified(self):
        """test if we add archive files with the same id from different sources, they end up as the same archive file"""
        # add an ead
        self.add_one_ead(dontlog=True)
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        archivefiles_from_ead = self.app.get(collection_url).json['results']
        archivefile = archivefiles_from_ead[0]
        # now we hadd two scans with this archive file
        scan_data = copy.deepcopy(self.scan_data)
        scan_data['archiveFile'] = archivefile['archiveFile']
        scan_data['archive_id'] = archivefile['archive_id']
        # add two scans
        self.add_one_scan(scan_data)
        self.add_one_scan(scan_data)
        # we should still get the same list of archivefiles
        self.assertEqual([x['id'] for x in archivefiles_from_ead], [x['id'] for x in self.app.get(collection_url).json['results']])

    def test_archivefile_creation_duplicate_id(self):
        """if we add scans (or eads) in which the same archiveFile occurs (but with different archive_id) we should have no problems"""

        archiveFile = self.scan_data['archiveFile']
        _archive1 = self.scan_data['archive_id']
        archive2 = 2

        self.add_one_scan(self.scan_data)
        self.scan_data['archive_id'] = archive2
        self.add_one_scan(self.scan_data)

        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        archivefiles = self.app.get(collection_url, {'archiveFile': archiveFile}).json['results']
        # now we expect to have two different archivefile
        self.assertEqual(len(archivefiles), 2)

        # afteer reindexing, these should reamin
        reindex_all(context=self)
        archivefiles = self.app.get(collection_url, {'archiveFile': archiveFile}).json['results']
        self.assertEqual(len(archivefiles), 2)

    def test_indexing_preserves_published(self):
        """after reindexing an archive file, its data remain intact"""

        # create an archivefile
        archiveFile = self.scan_data['archiveFile']
        self.add_one_scan(self.scan_data)
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        archivefiles = self.app.get(collection_url, {'archiveFile': archiveFile}).json['results']
        archivefile_url = localurl(archivefiles[0]['URL'])

        # publish the archive file
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})

        original_data = self.app.get(archivefile_url).json
        self.assertEqual(original_data['status'], config.STATUS_PUBLISHED)

        # after reindexing, the original data should still be available
        reindex_all(context=self)
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_archivefile_with_several_eads(self):
        # add nl file
        filecontents_nl = self.get_default_filecontents()
        self.add_one_ead(filecontents=filecontents_nl, filename='ead_nl.xml').json

        # create en file and add it
        filecontents_en = filecontents_nl.replace('langcode="nl"', 'langcode="en"').replace('Original Letter', 'title_in_english')
        self.add_one_ead(filecontents=filecontents_en, filename='ead_en.xml').json

        # create id file and add it
        filecontents_id = filecontents_nl.replace('langcode="nl"', 'langcode="id"').replace('Original Letter', 'title_in_indonesian')
        self.add_one_ead(filecontents=filecontents_id, filename='ead_id.xml').json

        # we have one archivefile 'collection'
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(len(archivefiles), 1)
        archivefile = archivefiles[0]
        self.assertEqual(archivefile['ead_ids'], ['ead_nl.xml', 'ead_en.xml', 'ead_id.xml'])
        self.assertEqual(archivefile['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})

        # also check if the right data are in the invidual archivefile result
        archivefile_data = self.app.get(archivefile['URL']).json
        self.assertEqual(archivefile_data['ead_ids'], ['ead_nl.xml', 'ead_en.xml', 'ead_id.xml'])
        self.assertEqual(archivefile_data['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})

        # test how we fare with unicode
        filecontents_en3 = filecontents_en.replace('title_in_english', u'“Catatan Berita” bulanan, berisi')
        filecontents_en3 = filecontents_en3.encode('utf8')
        self.change_ead(filecontents=filecontents_en3, filename='ead_en.xml').json
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        archivefile = archivefiles[0]
        self.assertEqual(archivefile['titles']['en'], u'“Catatan Berita” bulanan, berisi')

        filecontents_id4 = filecontents_id.replace('title_in_indonesian', 'Monthly &#039;Memories des Nouvelles&#039; with news')
        self.change_ead(filecontents=filecontents_id4, filename='ead_id.xml').json
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        archivefile = archivefiles[0]
        self.assertEqual(archivefile['titles']['id'], "Monthly 'Memories des Nouvelles' with news")
        self.assertEqual(archivefile['titles']['en'], u'“Catatan Berita” bulanan, berisi')
        self.assertEqual(archivefile['titles']['nl'], u'Original Letter')

        # now we add a new archivefile to the filecontents

        another_archivefile = dedent("""<c level="file">
        <did>\n        <unittitle>Letter5</unittitle>
        <unitdate datechar="creation" normal="1612/1812" encodinganalog="3.1.3">1612 - 1812</unitdate>
        <unitid>ARCHIVE_FILE_ID2</unitid>
        </did>\n
        </c>\n""")

        #
        # first update the nl file
        #
        filecontents5 = filecontents_nl.replace('</dsc>', another_archivefile + '\n</dsc>')
        self.change_ead(filecontents=filecontents5, filename='ead_nl.xml').json
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(len(archivefiles), 2)
        archivefile = archivefiles[0]
        self.assertEqual(archivefile['titles']['id'], "Monthly 'Memories des Nouvelles' with news")
        self.assertEqual(archivefile['titles']['en'], u'“Catatan Berita” bulanan, berisi')
        self.assertEqual(archivefile['titles']['nl'], u'Original Letter')
        self.assertEqual(archivefiles[1]['titles'], {u'nl': u'Letter5'})

        filecontents6 = filecontents_en.replace('</dsc>', another_archivefile.replace('Letter5', '“Catatan Berita”') + '\n</dsc>')

        # check for sanity that we really have another file
        self.assertNotEqual(filecontents_en, filecontents6)
        #
        # results should be the same if we delete and then add a file
        #
        self.delete_ead('ead_en.xml')
        self.add_one_ead(filecontents6, filename='ead_en.xml')
        self.change_ead(filecontents_id, filename='ead_id.xml')

        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(len(archivefiles), 2)
        archivefile = archivefiles[1]
        self.assertEqual(archivefiles[0]['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})
        self.assertEqual(archivefiles[1]['titles'], {u'nl': u'Letter5', u'en': u'“Catatan Berita”'})

        #
        # results should remain the same if we update a file
        #
        filecontents7 = filecontents_en.replace('</dsc>', another_archivefile.replace('Letter5', 'FILE7') + '\n</dsc>')

        self.change_ead(filecontents=filecontents7, filename='ead_en.xml')

        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(len(archivefiles), 2)
        self.assertEqual(archivefiles[0]['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})
        self.assertEqual(archivefiles[1]['titles'], {u'nl': u'Letter5', u'en': u'FILE7'})

        # choose an archive file from our ead, and publish it
        archivefile_url = localurl(archivefiles[0]['URL'])
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        self.app.put(archivefile_url, {'status': config.STATUS_NEW})
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(archivefiles[0]['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})

        # add a scan for to this archivefile, and see what happens
        # now we add a scan to one and connect it to our archivefile
        self.scan_data['archiveFile'] = self.app.get(archivefile_url).json['archiveFile']
        self.scan_data['archive_id'] = archivefiles[0]['archive_id']

        # we hadd a bug in which when we add TWO scans, the titles get messed up...
        self.add_one_scan(self.scan_data)
        self.add_one_scan(self.scan_data).json['URL']
        archivefiles = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION).json['results']
        self.assertEqual(archivefiles[0]['titles'], {'en': 'title_in_english', 'nl': 'Original Letter', 'id': 'title_in_indonesian'})

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_archivefile_index_ead_operations(self):
        """test various manipulations of ead files, and their effects on archive file info"""

        # publish an ead file
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        filecontents = self.get_default_filecontents('longer_ead.xml')
        ead_info = self.add_one_ead(filecontents=filecontents).json
        ead_id = ead_info['ead_id']
        self.app.put(localurl(ead_info['URL']), {'status': config.STATUS_PUBLISHED})
        archive_id = ead_info['archive_id']

        # choose an archive file from our ead, and publish it
        archivefiles = self.app.get(collection_url, {'ead_id': ead_id}).json['results']
        archivefile_url = localurl(archivefiles[0]['URL'])
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        original_data = self.app.get(archivefile_url).json

        # check sanity
        self.assertTrue(original_data['title'])
        self.assertEqual(original_data['status'], config.STATUS_PUBLISHED)

        # data should remain unchanged after reindexing
        reindex_all(context=self)
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # now we add a scan to one and connect it to our archivefile
        self.scan_data['archiveFile'] = self.app.get(archivefile_url).json['archiveFile']
        self.scan_data['archive_id'] = archive_id
        scan_url = self.add_one_scan(self.scan_data).json['URL']
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        # except for the number of scans, our original data should remain unchanged
        original_data['number_of_scans'] = 1
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # data should remain unchanged after reindexing
        reindex_all(context=self)
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # the status of the ead file is independent of the status (or other data) of the archivefile
        self.app.put(localurl(ead_info['URL']), {'status': config.STATUS_NEW})
        self.assertEqual(original_data, self.app.get(archivefile_url).json)
        self.app.put(localurl(ead_info['URL']), {'status': config.STATUS_PUBLISHED})
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # and again, reindexing should not make any difference
        reindex_all(context=self)
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # if we upload the ead a second time, the data should not change in any way
        self.change_ead(filecontents=filecontents, filename=ead_id).json
        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # also, if we delete it and re-add it, other data should persist
        self.delete_ead(ead_id=ead_id)
        self.add_one_ead(filecontents=filecontents).json

        self.assertEqual(original_data, self.app.get(archivefile_url).json)

        # removing the reference to the archiveFile from the EAD should not remove this archiveFile
        # (because it is still referenced by a scan)
        filecontents = filecontents.replace(original_data['archiveFile'], 'new_archiveFileID')
        filecontents = str(filecontents)
        self.change_ead(filecontents=filecontents, filename=ead_id).json

        # we should loose most of the data, but not the identifying info and the fact that it is published
        minimal_data = copy.deepcopy(original_data)
        minimal_data['ead_ids'].remove(ead_id)
#         original_title = minimal_data['title']
#         minimal_data['title'] = None
        self.assertEqual(minimal_data['status'], config.STATUS_PUBLISHED)

#         self.assertEqual(self.app.get(archivefile_url).json, minimal_data)

        # restoring the EAD file its original state should restore our original archiveFile data
        filecontents = str(filecontents.replace('new_archiveFileID', original_data['archiveFile']))
        self.change_ead(filecontents=filecontents, filename=ead_id).json
#         minimal_data['title'] = original_title
        self.assertEqual(self.app.get(archivefile_url).json, original_data)

        # now delete the EAD file.
        self.app.delete(localurl(ead_info['URL']))
        self.assertEqual(minimal_data, self.app.get(archivefile_url).json)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

        # we keep on checking invariance under indexing
        reindex_all(context=self)
        # TODO: the next test should pass

        # if we add the EAD again, the status of the archiveFile should remain the same
        self.add_one_ead(filecontents=filecontents).json
        self.assertEqual(self.app.get(archivefile_url).json, original_data)

        # now, if we both the EAD file as the scans, also the archivefile should be removed
        self.app.delete(localurl(ead_info['URL']))
        self.app.delete(localurl(scan_url))
        self.app.get(archivefile_url, status=404)

        reindex_all(context=self)
        self.app.get(archivefile_url, status=404)

        # test if sort_field is indexed
        response1 = self.solr_archivefile.search(q='*:*')
        response2 = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response1.total_results, response2.total_results)

    def test_archivefile_that_needs_solr_escaping(self):
        scandata = dict(self.scan_data)
        archiveFile = 'archive file [with square brackets]'
        scandata['archiveFile'] = archiveFile
        response = self.add_one_scan(scandata)
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        response = self.app.get(collection_url, {'archive_id': scandata['archive_id'], 'archiveFile': scandata['archiveFile']})
        self.assertEqual(response.json['total_results'], 1)
        archivefile_url = str(response.json['results'][0]['URL'])
        response = self.app.get(archivefile_url)
        self.assertEqual(response.json['archiveFile'], archiveFile)

        response = self.app.put(archivefile_url, {'status': 2})
        response = self.app.put(archivefile_url, {'status': 1})
