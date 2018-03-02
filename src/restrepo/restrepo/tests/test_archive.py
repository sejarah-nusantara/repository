"""
Tests for EAD CRUD and validation
"""
from restrepo import config
from base import BaseRepoTest
from restrepo.db.archive import get_archives


class TestArchive(BaseRepoTest):

    def setUp(self):
        super(TestArchive, self).setUp()
        self.an_archive = get_archives(context=self)[1]
        self.an_archive.url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(self.an_archive.id))

    def test_get(self):
        response = self.app.get(self.an_archive.url)
        self.assertEqual(response.json, self.an_archive.to_dict())

    def test_add(self):
        url = config.SERVICE_ARCHIVE_COLLECTION
        response = self.app.post(url, {'archive': 'xxx', 'institution': 'yyy'})

        self.assertEqual(response.json['archive'], 'xxx')
        self.assertEqual(response.json['institution'], 'yyy')
        self.assertTrue(response.json['id'])

    def test_delete(self):
        archive_id = self.an_archive.id
        self.assertTrue(archive_id in [x.id for x in get_archives(self)])
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(archive_id))
        self.app.delete(url)
        # now we should not have this archive in our list anymore
        self.assertFalse(archive_id in [x.id for x in get_archives(self)])

    def test_update(self):
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(self.an_archive.id))
        response = self.app.put(url, {'archive_description': 'zzz'})
        self.assertEqual(response.json['archive_description'], 'zzz')

    def test_error_on_delete_or_update_archive_with_scans(self):
        # sanity check - we should have the db set up so that this archive has a scan
        self.add_five_scans({'archive_id': self.an_archive.id})
        response = self.app.get(config.SERVICE_SCAN_COLLECTION, {'archive_id': self.an_archive.id})
        self.assertEqual(response.json['total_results'], 5)
        # trying to delete this archive should raise an error
        response = self.app.delete(self.an_archive.url, status=400)

        response = self.app.put(self.an_archive.url, {'archive': 'xxxxx'}, status=400)
        response = self.app.put(self.an_archive.url, {'institution': 'xxxxx'}, status=400)

    def test_error_on_delete_or_update_archive_with_eads(self):
        response = self.add_one_ead(dontlog=True)
        archive_id = response.json['archive_id']
        # assert sanity
        response = self.app.get(config.SERVICE_EAD_COLLECTION, {'archive_id': archive_id})
        self.assertEqual(response.json['total_results'], 1)
        # trying to delete this archive should raise an error
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(archive_id))
        response = self.app.delete(url, status=400)

        response = self.app.put(url, {'archive': 'xxxxx'}, status=400)
        response = self.app.put(url, {'institution': 'xxxxx'}, status=400)

    def test_error_on_empty_archive_or_institution(self):
        # adding an ampety institution or archive should raise an error
        url = config.SERVICE_ARCHIVE_COLLECTION
        data = {
            'institution': '',
            'archive': 'arch',
        }
        self.app.post(url, data, status=400)

        data = {
            'institution': 'inst',
            'archive': '',
        }
        self.app.post(url, data, status=400)

        # updating an archive and setting institution or archive to '' should raise an error
        data = {
            'institution': 'ints',
            'archive': 'arch',
        }
        response = self.app.post(url, data, status=200)
        archive_id = response.json['id']
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(archive_id))
        self.app.put(url, dict(data, institution=''), status=400)
        self.app.put(url, dict(data, archive=''), status=400)

    def test_error_on_duplicate_archive_and_institution(self):
        url = config.SERVICE_ARCHIVE_COLLECTION
        data = {
            'institution': 'ints',
            'archive': 'arch',
        }
        response = self.app.post(url, data, status=200)
        archive_id = response.json['id']

        # adding a second archive with these data should return an error
        self.app.post(url, data, status=400)
        # although adding an insitution or archive by itself should be fine
        response = self.app.post(url, dict(data, institution='xxx'), status=200)
        another_archive_id = response.json['id']
        self.assertNotEqual(archive_id, another_archive_id)

        self.app.post(url, dict(data, archive='xxx'), status=200)

        # with the current archive we can do what we want
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(archive_id))
        self.app.put(url, dict(data, institution='xxx2'), status=200)
        self.app.put(url, dict(data, archive='xxx2'), status=200)
        # make sure to reset to original data, so we don't break the following tests
        self.app.put(url, data, status=200)

        # another archive we cannot update with the same data
        url = config.SERVICE_ARCHIVE_ITEM.replace('{archive_id}', str(another_archive_id))
        self.app.put(url, data, status=400)
