from .base import BaseRepoTest, localurl


class TestSolrInterface(BaseRepoTest):
    def test_error_raises_exception(self):
        "When a solr query triggers an error it should raise an exception"
        with self.assertRaises(Exception):
            self.solr_scan.search(q='invalid query:"')
        with self.assertRaises(Exception):
            self.solr_scan.update({'nonexistent': 1})


class TestSolrEad(BaseRepoTest):
    "Ensure ead files are indexed in solr on creation/update/deletion"

    def test_solr_ead_create(self):
        self.add_one_ead()
        docs = self.solr_ead.search(q='country:%s' % self.default_country).documents
        self.assertEqual(len(docs), 1)
        docs = self.solr_ead.search(q='institution:%s' % self.default_institution).documents
        self.assertEqual(len(docs), 1)

    def test_ead_delete(self):
        res = self.add_one_ead().json
        self.app.delete(localurl(res['URL']))
        docs = self.solr_ead.search(q='*:*').documents
        self.assertEqual(len(docs), 0)

    def test_solr_ead_update(self):
        res = self.add_one_ead().json
        # Brutal string substitution. It might break XML.
        # The new values must be among the ones listed in /lists/archives
        new_filecontents = self.get_default_filecontents().replace(self.default_institution, 'RU-RSMA').replace(self.default_archive, '01')
        filetuple = ('file', res['ead_id'], new_filecontents)
        self.app.put(localurl(res['URL']), upload_files=[filetuple])
        docs = self.solr_ead.search(q='institution:RU-RSMA').documents
        self.assertEqual(len(docs), 1)


class TestSolrScans(BaseRepoTest):
    def test_solr_scan_create(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        self.add_one_scan(scan_data).json
        scans = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(scans), 1)

    def test_solr_scan_update(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        result = self.add_one_scan(scan_data).json
        scans = self.solr_scan.search(q='archiveFile:a_repo').documents
        self.assertEqual(len(scans), 1)
        self.app.put(localurl(result['URL']),
            {'archiveFile': 'another_archive'})
        scans = self.solr_scan.search(q='archiveFile:another_archive').documents
        self.assertEqual(len(scans), 1)

    def test_solr_scan_delete(self):
        scan_data = {'archive_id': 3, 'archiveFile': 'a_repo'}
        result = self.add_one_scan(scan_data).json
        scans = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(scans), 1)
        self.app.delete(localurl(result['URL']))
        scans = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(scans), 0)


class TestSolrWrappers(BaseRepoTest):
    def setUp(self):
        super(TestSolrWrappers, self).setUp()
        self.add_one_scan()
        self.add_one_ead()

    def test_isolation(self):
        self.assertEqual(len(self.solr_scan.search(q='*:*').documents), 1)
        self.assertEqual(len(self.solr_eadcomponent.search(q='*:* AND is_component:True').documents), 1)
        self.assertEqual(len(self.solr_ead.search(q='*:*').documents), 1)
