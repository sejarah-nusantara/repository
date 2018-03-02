from base import BaseRepoTest
from restrepo.indexes import reindex_all

TEST_FILENAME = 'ID-ANRI_K.66a_01.ead.xml'


class IndexEADTestCase(BaseRepoTest):

    def test_solr_search_components(self):
        """we test if the components return the right kinds of results"""
        filecontents = self.get_default_filecontents(filename=TEST_FILENAME)
        result = self.add_one_ead(filename=TEST_FILENAME,
             filecontents=filecontents, dontlog=True)
        self.ead_id = result.json['ead_id']

        components = self.solr_eadcomponent.search(q='*:* AND is_component:True').documents
        self.assertEqual(len(components), 9)

        # fragment of an original file
        """
        <c level="otherlevel" otherlevel="">
        <did>
            <unittitle encodinganalog="3.1.2">Net-general resolutions and -incidental- net-secret resolutions</unittitle>
            <unitid  encodinganalog="3.1.1">853..1182</unitid>
            <unitdate datechar="creation" normal="1612/1812" encodinganalog="3.1.3">1612 - 1812</unitdate>
            <physdesc><extent encodinganalog="3.1.5">Not recorded</extent></physdesc>
        </did>
        """
        """
        <c level="file">
            <did>
            <unittitle encodinganalog="3.1.2">1613 november 30 - 1620 october 1</unittitle>
            <unitid  encodinganalog="3.1.1">853</unitid>
            <unitdate datechar="creation" normal="1613-11-30/1620-10-1" encodinganalog="3.1.3">1613-11-30 - 1620-10-1</unitdate>
            <physdesc><extent encodinganalog="3.1.5">Not recorded</extent></physdesc>
            </did>
        </c>
        # """

        component = components[4]

        self.assertEqual(
            component['eadcomponent_id'], '/'.join((self.ead_id, component['xpath']))
        )

        self.assertEqual(component['country'], 'ID')
        self.assertEqual(component['institution'], 'ID-JaAN')
        self.assertEqual(component['archive'], 'HR')
        self.assertEqual(component['archive_id'], 1)
        self.assertEqual(component['title'], '1613 november 30 - 1620 october 1')
        self.assertEqual(component['text'], [''])

        docs = self.solr_eadcomponent.search(q='is_component:True AND search_source:Net-general resolutions').documents
        self.assertEqual(len(docs), 3)

        docs = self.solr_eadcomponent.search(q='is_component:True AND +search_source:"November 30"').documents
        self.assertEqual(len(docs), 1)

        docs = self.solr_eadcomponent.search(q='is_component:True AND +search_source:"not recorded"').documents
        self.assertEqual(len(docs), 7)

    def test_solr_index_on_ead_delete(self):
        result = self.add_one_ead(dontlog=True)
        self.ead_id = result.json['ead_id']

        self.app.delete('/ead/' + str(self.ead_id))
        docs = self.solr_eadcomponent.search(q='*:*').documents
        self.assertEqual(len(docs), 0)

    def test_solr_index_on_ead_update(self):
        filecontents = self.get_default_filecontents(filename=TEST_FILENAME)
        result = self.add_one_ead(filename=TEST_FILENAME,
             filecontents=filecontents, dontlog=True)
        self.ead_id = result.json['ead_id']

        filename = 'ID-ANRI_K.66a_01.ead.modified.xml'
        filecontents = self.get_default_filecontents(filename=filename)
        filetuple = ('file', TEST_FILENAME, filecontents)
        self.app.put('/ead/' + str(self.ead_id), upload_files=[filetuple])

        docs = self.solr_eadcomponent.search(q='*:* AND is_component:True').documents
        self.assertEqual(len(docs), 9)

        docs = self.solr_eadcomponent.search(q='search_source:eadfile').documents
        self.assertEqual(len(docs), 1)

    def test_reindex_all(self):
        # add some data to the databse, and check sanity
        filecontents = self.get_default_filecontents(filename=TEST_FILENAME)
        self.add_one_ead(filename=TEST_FILENAME,
             filecontents=filecontents, dontlog=True)

        self.add_five_scans()
        docs = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(docs), 5)
        docs = self.solr_ead.search(q='*:*').documents
        self.assertEqual(len(docs), 1)
        docs = self.solr_eadcomponent.search(q='*:*').documents
        self.assertEqual(len(docs), 43)
        docs = self.solr_archivefile.search(q='*:*').documents
        self.assertEqual(len(docs), 5)

        # empty the solr db (and check sanity again)
        self.solr_ead.delete_by_query('*:*', commit=True)
        self.solr_eadcomponent.delete_by_query('*:*', commit=True)
        self.solr_scan.delete_by_query('*:*', commit=True)
        self.solr_archivefile.delete_by_query('*:*', commit=True)

        self.assertEqual(self.solr.search(q='*:*').total_results, 0)

        docs = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(docs), 0)
        docs = self.solr_ead.search(q='*:*').documents
        self.assertEqual(len(docs), 0)
        docs = self.solr_eadcomponent.search(q='*:*').documents
        self.assertEqual(len(docs), 0)
        docs = self.solr_archivefile.search(q='*:*').documents
        self.assertEqual(len(docs), 0)

        # now reindex, and all should be as before
        reindex_all(context=self)

        docs = self.solr_scan.search(q='*:*').documents
        self.assertEqual(len(docs), 5)
        docs = self.solr_ead.search(q='*:*').documents
        self.assertEqual(len(docs), 1)
        docs = self.solr_eadcomponent.search(q='*:*').documents
        self.assertEqual(len(docs), 43)
        docs = self.solr_archivefile.search(q='*:*').documents
        self.assertEqual(len(docs), 5)
