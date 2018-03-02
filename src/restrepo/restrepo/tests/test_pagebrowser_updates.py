from restrepo.tests.base import BaseRepoTest, localurl
from restrepo import config
from restrepo import celery_tasks


class TestPagebrowserUpdates(BaseRepoTest):

    def setUp(self):
        super(TestPagebrowserUpdates, self).setUp()
        #
        # instead of really pinging our urls, we store them in an attribute to be able to check them later
        #
        self._published_archivefiles = []
        self.patch_celery_tasks()
#         celery_tasks.app.conf.update(CELERY_ALWAYS_EAGER=True)

#     def tearDown(self):
#         celery_tasks.app.conf.update(CELERY_ALWAYS_EAGER=False)

    def patch_celery_tasks(self):
        def patched_update_book(action, url, ead_id, archivefile_id):
            record = (ead_id, archivefile_id)
            if action == 'refresh':
                self._published_archivefiles.append(record)
            elif action == 'delete':
                if record in self._published_archivefiles:
                    self._published_archivefiles.remove(record)

        celery_tasks.update_book.delay = patched_update_book
#         celery_tasks.update_book.ping_url = patched_update_book

    def assert_published_in_pagebrowser(self, ead_id, archivefile_id):
        self.assertTrue((ead_id, archivefile_id) in self._published_archivefiles)

    def assert_not_published_in_pagebrowser(self, ead_id, archivefile_id):
        if ead_id:
            self.assertFalse((ead_id, archivefile_id) in self._published_archivefiles)
        else:
            self.assertFalse(archivefile_id in [x[1] for x in self._published_archivefiles])

    def add_archivefile(self):
        # publish an ead file and choose an archivefile
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        ead_info = self.add_one_ead().json
        ead_id = self.ead_id = ead_info['ead_id']
        archivefiles = self.app.get(collection_url, {'ead_id': ead_id}).json['results']
        self.archivefile = archivefiles[0]
        self.archivefile_url = localurl(self.archivefile['URL'])
        return (self.archivefile, self.archivefile_url)

    def test_archivefile_published_and_unpublish(self):
        """
        """
        archivefile, archivefile_url = self.add_archivefile()
        ead_id = self.ead_id
        self.assert_not_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])

        # publish the archive file
        response = self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        self.assert_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])

        # unpublish the archive file
        self.app.put(archivefile_url, {'status': config.STATUS_NEW})
        self.assert_not_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])

    def test_update_with_many_eads(self):
        archivefile, archivefile_url = self.add_archivefile()
        ead_id1 = self.ead_id
        # and another ead file with the same contents
        ead_id2 = self.add_one_ead(filename='file2.xml').json['ead_id']
        ead_id3 = self.add_one_ead(filename='file3.xml').json['ead_id']
        ead_id4 = self.add_one_ead(filename='file4.xml').json['ead_id']

        self.assert_not_published_in_pagebrowser(ead_id=ead_id1, archivefile_id=archivefile['id'])
        self.assert_not_published_in_pagebrowser(ead_id=ead_id2, archivefile_id=archivefile['id'])
        self.assert_not_published_in_pagebrowser(ead_id=ead_id3, archivefile_id=archivefile['id'])
        self.assert_not_published_in_pagebrowser(ead_id=ead_id4, archivefile_id=archivefile['id'])

        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})

        self.assert_published_in_pagebrowser(ead_id=ead_id1, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id2, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id3, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id4, archivefile_id=archivefile['id'])

    def test_delete_ead(self):
        archivefile, archivefile_url = self.add_archivefile()
        ead_id = self.ead_id
        # publish it again, and then delete the ead file
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        self.assert_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])
        self.app.delete(localurl(config.SERVICE_EAD_ITEM.replace('{ead_id}', ead_id)))
        self.assert_not_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])

    def test_delete_and_readd_ead(self):
        archivefile, archivefile_url = self.add_archivefile()
        ead_id = self.ead_id
        # and another ead file with the same contents
        response = self.add_one_ead(filename='anotherfile.xml')
        ead_id2 = response.json['ead_id']
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})

        self.assert_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id2, archivefile_id=archivefile['id'])
        # remove the first ead
        self.app.delete(localurl(config.SERVICE_EAD_ITEM.replace('{ead_id}', ead_id)))
        # now the first book should be unpublished, the second book still be there
        self.assert_not_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id2, archivefile_id=archivefile['id'])
        # now if we readd the first ead, both books should be available in the pagebrowser again
        self.add_one_ead()
        self.assert_published_in_pagebrowser(ead_id=ead_id, archivefile_id=archivefile['id'])
        self.assert_published_in_pagebrowser(ead_id=ead_id2, archivefile_id=archivefile['id'])

    def test_archivefile_without_ead_is_not_published(self):
        """an archifile without ead is not published"""
        # create an archivefile
        archiveFile = self.scan_data['archiveFile']
        self.add_one_scan(self.scan_data)
        collection_url = config.SERVICE_ARCHIVEFILE_COLLECTION
        archivefiles = self.app.get(collection_url, {'archiveFile': archiveFile}).json['results']
        archivefile_url = localurl(archivefiles[0]['URL'])

        # publish the archive file
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})

        #  since this archivefile is not connected to an ead file, we did not ping the pagebrowser
        self.assert_not_published_in_pagebrowser(ead_id=None, archivefile_id=archivefiles[0]['id'])

    def test_update_on_update_ead(self):
        archivefile, archivefile_url = self.add_archivefile()
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

        ead_id = self.ead_id
        ead_url = localurl(config.SERVICE_EAD_ITEM.replace('{ead_id}', ead_id))

        # reset the list of published archivefiles so we can check if a refresh request has been sent
        self._published_archivefiles = []
        filecontents = self.get_default_filecontents()
        newfilecontents = filecontents.replace(archivefile['title'], 'changed_string')
        filetuple = ('file', 'test_file_123.xml', str(newfilecontents))
        self.app.put(ead_url, upload_files=[filetuple], extra_environ={'dontlog_web_chats': '1'})
        # now our archive should have been republished
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

    def test_update_on_add_or_delete_scans(self):
        archivefile, archivefile_url = self.add_archivefile()
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        scan_data = self.scan_data
        scan_data['archiveFile'] = archivefile['archiveFile']

        # we reset the list of self._published_archivefiles
        self._published_archivefiles = []

        self.add_one_scan(scan_data)
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

        self._published_archivefiles = []
        self.assert_not_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])
        result = self.add_one_scan(scan_data)
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

        self._published_archivefiles = []
        # now delete the scan
        self.app.delete(localurl(result.json['URL']))
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

    def test_update_on_reorder_scans(self):
        archivefile, archivefile_url = self.add_archivefile()
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        self.scan_data['archiveFile'] = archivefile['archiveFile']
        scans = self.add_five_scans()
        url = localurl(scans[1]['URL']) + '/move'

        # reset the list of self._published_archivefiles
        self._published_archivefiles = []
        self.assert_not_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])
        self.app.post(url, {'after': 5})
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])

    def test_update_on_publishing_unpublishing_scans(self):
        archivefile, archivefile_url = self.add_archivefile()
        self.app.put(archivefile_url, {'status': config.STATUS_PUBLISHED})
        scan_data = self.scan_data
        scan_data['archiveFile'] = archivefile['archiveFile']
        response = self.add_one_scan(scan_data)
#         scan_url = localurl(response.json['URL'])

        # reset the list of self._published_archivefiles
        self._published_archivefiles = []
        # now if we publish the scan we should refresh the archivefile
        scan_url = localurl(response.json['URL'])
        self.assert_not_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])
        self.app.put(scan_url, {'status': config.STATUS_PUBLISHED})
        self.assert_published_in_pagebrowser(ead_id=self.ead_id, archivefile_id=archivefile['id'])
