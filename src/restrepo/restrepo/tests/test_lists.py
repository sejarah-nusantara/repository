from base import BaseRepoTest
from restrepo import config


class TestLists(BaseRepoTest):

    def test_archives(self):
        url = config.SERVICE_ARCHIVE_COLLECTION
        result = self.app.get(url).json

        # check sanity
        self.assertTrue('total_results' in result)
        self.assertTrue('results' in result)

        results = result['results']
        self.assertTrue(len(results) > 0)
        self.assertTrue('id' in results[0])

        # test some possible queriesTestLists
        result = self.app.get(url, {'country': 'GH'}).json
        self.assertEqual(result['total_results'], 2)

        result = self.app.get(url, {'institution': 'GH-PRAAD'}).json
        self.assertEqual(result['total_results'], 2)

        result = self.app.get(url, {'archive': 'RG1'}).json
        self.assertEqual(result['total_results'], 1)
        result = self.app.get(url,
            {'institution': 'GH-PRAAD', 'archive': 'RG1'}).json
        self.assertEqual(result['total_results'], 1)

        result = self.app.get(config.SERVICE_ARCHIVE_COLLECTION,
            {'archive_id': 1}).json

        self.assertEqual(result['total_results'], 1)

    def test_list_findingaid(self):
        url = config.SERVICE_FINDINGAID_COLLECTION
        self.add_one_ead()
        result = self.app.get(url).json
        self.assertEqual(result['results'], [{'id': 'FindingAid'}])

        filecontents = self.get_default_filecontents(filename='longer_ead.xml')
        self.add_one_ead(filecontents=filecontents, filename="anotherfile.xml")
        result = self.app.get(url).json
        self.assertEqual(result['results'], [{'id': 'FindingAid'}, {'id': 'HR'}])

    def test_with_a_large_file(self):
        filecontents = self.get_default_filecontents('ica-atom.atcha.nl_15893.ead.xml')
        response = self.add_one_ead(filecontents=filecontents, status=200)
        ead_id = response.json['ead_id']
#        response = self.app.get(config.SERVICE_ARCHIVE_FILE_ID, {'ead_id': ead_id})
        response = self.app.get(config.SERVICE_COMPONENT_TREE, {'ead_id': ead_id})

        # regression test: if we had large files, we would only return a partial tree
        self.assertEqual(len(response.json['results']), 7)
