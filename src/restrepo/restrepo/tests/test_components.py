import os
import copy
from lxml import etree
from base import BaseRepoTest

from restrepo import config
from restrepo.indexes.lists import search_components
from restrepo.db.ead import ead2view
from restrepo.tests.base import localurl
from restrepo.config import ERRORS
from restrepo.indexes import reindex_all

from base import TESTFILES_DIR

TEST_FILENAME = 'ID-ANRI_K.66a_01.ead.xml'


class TestComponents(BaseRepoTest):

    def _add_some_eads(self):
        """add two eads: the default one, and the ID-ANRI... one,

        return two ead_id's
        """
        ead_response1 = self.add_one_ead(dontlog=True)

        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        ead_response2 = self.add_one_ead(filecontents=filecontents, filename=test_fn, dontlog=True)

        self.ead_id1 = ead_id1 = ead_response1.json['ead_id']
        self.ead_id2 = ead_id2 = ead_response2.json['ead_id']

        url = config.SERVICE_COMPONENTS_COLLECTION
        self.some_component = self.app.get(url, {'ead_id': ead_id2, 'is_component': True}).json['results'][4]
        return (ead_id1, ead_id2)

    def test_search(self):
        ead_id1, ead_id2 = self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION

        res = self.app.get(url, {'ead_id': ead_id1, 'is_component': True}).json
        self.assertEqual(res['total_results'], 1)

        res = self.app.get(url, {'ead_id': ead_id2, 'is_component': True}).json
        # do we have all (and only) the number of expected results?
        self.assertEqual(res['total_results'], 9)

    def test_search_by_xpath(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component
        res = self.app.get(url, {
            'xpath': component['xpath'],
            'ead_id': component['ead_id']}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(results), 1)

    def test_search_by_archive_id(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'archive_id': component['archive_id'], 'is_component': True}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(results), 9)

    def test_search_by_archive(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'archive': component['archive'], 'is_component': True}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertEqual(len(res['results']), 9)
        self.assertTrue(component['ead_id'] in results)

    def test_search_by_archiveFile(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'archiveFile': component['archiveFile'], 'is_component': True, }).json
        results = [x['ead_id'] for x in res['results']]
        self.assertEqual(len(res['results']), 1)
        self.assertTrue(component['ead_id'] in results)

    def test_search_by_country(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'country': component['country'], 'is_component': True, }).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(res['results']), 9)

    def test_search_by_is_archiveFile(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'is_archiveFile': True, 'is_component': True, }).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(res['results']), 5)
        self.assertTrue(res['results'][2]['is_archiveFile'])
        self.assertTrue(res['results'][0]['is_archiveFile'])

    def test_search_by_contains_text(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        res = self.app.get(url, {'contains_text': 'recorded', 'is_component': True}).json
        self.assertEqual(len(res['results']), 7)
        # note the behavior is to search for phrase OR prase:
        res = self.app.get(url, {'contains_text': 'Not recorded', 'is_component': True}).json
        self.assertEqual(len(res['results']), 7)
        res = self.app.get(url, {'contains_text': 'november', 'is_component': True}).json
        self.assertEqual(len(res['results']), 1)
        res = self.app.get(url, {'contains_text': 'january', 'is_component': True}).json
        self.assertEqual(len(res['results']), 3)
        self.assertTrue('january' in res['results'][0]['snippet'][0])

        res = self.app.get(url, {'contains_text': 'jalan', 'is_component': False}).json
        self.assertEqual(len(res['results']), 1)
        self.assertTrue('Jalan' in res['results'][0]['snippet'][0])

        # test if using capitals is ignored
        res = self.app.get(url, {'contains_text': 'JalaN', 'is_component': False}).json
        self.assertEqual(len(res['results']), 1)

        res = self.app.get(url, {'contains_text': 'ID-JaAN'}).json
        self.assertEqual(len(res['results']), 2)
        res = self.app.get(url, {'contains_text': 'JaAN'}).json
        self.assertEqual(len(res['results']), 2)

    def test_search_by_ead_id(self):
        ead_id1, ead_id2 = self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION

        res = self.app.get(url, {'ead_id': ead_id1, 'is_component': True}).json
        self.assertEqual(len(res['results']), 1)
        res = self.app.get(url, {'ead_id': ead_id2, 'is_component': True}).json
        self.assertEqual(len(res['results']), 9)

    def test_search_combined_search(self):
        """try some 'combined' searches"""
        # TODO: write this test

    def test_search_start_limit(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        # test start and limit arguments
        res = self.app.get(url, {'start': 1, 'limit': 3, 'is_component': True}).json
        self.assertEqual(res['total_results'], 10)
        self.assertEqual(res['start'], 1)
        self.assertEqual(res['end'], 4)
        self.assertEqual(len(res['results']), 3)

        res = self.app.get(url, {'start': 5, 'limit': 100, 'is_component': True}).json
        self.assertEqual(res['total_results'], 10)
        self.assertEqual(res['start'], 5)
        self.assertEqual(res['end'], 10)
        self.assertEqual(len(res['results']), 5)

    def test_search_by_institution(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component
        res = self.app.get(url, {'institution': component['institution'], 'is_component': True}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(res['results']), 9)

        res = self.app.get(url, {'archive': 'RG1', 'is_component': True}).json
        self.assertEqual(len(res['results']), 1)

    def test_search_by_findingaid(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component
        res = self.app.get(url, {'findingaid': component['findingaid'], 'is_component': True}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(res['results']), 9)

    def test_search_by_language(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        component = self.some_component

        res = self.app.get(url, {'language': component['language'], 'is_component': True}).json
        results = [x['ead_id'] for x in res['results']]
        self.assertTrue(component['ead_id'] in results)
        self.assertEqual(len(res['results']), 9)

    def test_search_by_date(self):
        _ead1, ead2 = self._add_some_eads()
        url = config.SERVICE_COMPONENTS_COLLECTION
        all_components = self.app.get(url, {'ead_id': ead2, 'is_component': True}).json['results']
        component0 = all_components[0]
        component4 = all_components[4]

        # first we check if the data from the XML file is sane
        self.assertEqual(component4['date'], '1613-11-30 - 1620-10-1')

        # the date_to value should default to 12-31
        self.assertEqual(component0['date'], '1612 - 1812')
        self.assertEqual(component0['date_from'][:10], '1612-01-01')
        self.assertEqual(component0['date_to'][:10], '1812-12-31')

        res = self.app.get(url, {'date_from': '1620-10-02', 'is_component': True}).json
        self.assertTrue(component0 in res['results'])
        self.assertFalse(component4 in res['results'])

        res = self.app.get(url, {'date_to': '1613-11-29', 'is_component': True}).json
        self.assertTrue(component0 in res['results'])
        self.assertFalse(component4 in res['results'])

        res = self.app.get(url, {'date_to': '1611-01-01', 'is_component': True}).json
        self.assertFalse(component0 in res['results'])

        res = self.app.get(url, {'date_from': '1611-01-01', 'date_to': '1811-01-01', 'is_component': True}).json
        self.assertTrue(component0 in res['results'])
        res = self.app.get(url, {'date_from': '1613-01-01', 'date_to': '1811-01-01', 'is_component': True}).json
        self.assertTrue(component0 in res['results'])
        res = self.app.get(url, {'date_from': '1811-01-01', 'date_to': '1817-01-01', 'is_component': True}).json
        self.assertTrue(component0 in res['results'])

    def test_search_invalid_arguments(self):
        self.add_one_ead(dontlog=True)
        url = config.SERVICE_COMPONENTS_COLLECTION
        self.app.get(url, {'unknown parameter': 'xxx'}, status=400).json

        # xpath is only valid in combination with ead_id
        self.app.get(url, {'xpath': '/'}, status=400).json
        # datefrom and date_to should be of the right format

        result = self.app.get(url, {'date_from': 'xxx'}, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)
        result = self.app.get(url, {'date_to': 'xxx'}, status=400).json
        self.assertEqual(result['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_component_tree(self):
        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        ead = self.add_one_ead(filecontents=filecontents, dontlog=True, filename=test_fn).json
        url = config.SERVICE_COMPONENT_TREE
        res = self.app.get(url, {'ead_id': ead['ead_id']}).json

        results = res['results']
        self.assertEqual(len(results), 5)

        # the structure of the components is as follows
        result_0 = results[3]
        result_0_0 = result_0['children'][0]
        result_0_0_0 = result_0_0['children'][0]
        result_0_0_0_0 = result_0_0_0['children'][0]
        self.assertEqual(len(result_0['children']), 1)
        self.assertEqual(len(result_0_0['children']), 1)
        self.assertEqual(len(result_0_0_0['children']), 1)
        self.assertEqual(result_0_0_0['title'], 'General Resolutions')
        # the tree should be pruned by default - i.e. leaf nodes should be missing
        self.assertEqual(len(result_0_0_0_0['children']), 0)

        # now do the same but with an unpruned tree
        res = self.app.get(url, {'ead_id': ead['ead_id'], 'prune': False}).json

        results = res['results']
        self.assertEqual(len(results), 5)

        # the structure of the components is as follows
        result_0 = results[3]
        result_0_0 = result_0['children'][0]
        result_0_0_0 = result_0_0['children'][0]
        result_0_0_0_0 = result_0_0_0['children'][0]
        self.assertEqual(len(result_0['children']), 1)
        self.assertEqual(len(result_0_0['children']), 1)
        self.assertEqual(len(result_0_0_0['children']), 1)
        self.assertEqual(result_0_0_0['title'], 'General Resolutions')
        self.assertEqual(len(result_0_0_0_0['children']), 3)

    def test_component_structure(self):
        """test if the component gives back all fields with decent content"""
        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        self.add_one_ead(filecontents=filecontents, dontlog=True).json
        res = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, {'is_component': True}).json
        component = res['results'][0]

        self.assertEqual(component['title'], u'Decision making')
        self.assertEqual(component['description'],
            u'this entry has <b>markup</b> in html')

        self.assertEqual(component['scopecontent'],
             '<p>This section contains archival records</p>')
        self.assertEqual(component['date'], '1612 - 1812')
        self.assertEqual(component['custodhist'], '<p>CUSTODHIST IS NEW..</p>')

        self.assertFalse('search_source' in component)
        self.assertFalse('is_rootlevel' in component)

        self.assertTrue('number_of_scans' in component)

    def test_component_number_of_scans(self):
        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        response = self.add_one_ead(filecontents=filecontents, dontlog=True).json
        ead_id = response['ead_id']
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, {'ead_id': ead_id, 'is_archiveFile': True})
        # get a leaf node
        c = response.json['results'][0]
        # now add some scans to this leaf
        scans = self.add_five_scans({'archiveFile': c['archiveFile'], 'archive_id': c['archive_id']})
        qry = {'ead_id': c['ead_id'], 'archiveFile': c['archiveFile']}
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, qry)
        new_c = response.json['results'][0]
        self.assertEqual(new_c['number_of_scans'], 5)

        # and now that we are at it, check if we did not mess too much with the existing data
        self.assertEqual(set(c.keys()), set(new_c.keys()))
        self.assertEqual(c['title'], new_c['title'])

        # now we delete a scan
        self.app.delete(localurl(scans[0]['URL']))
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, qry)
        new_c = response.json['results'][0]
        self.assertEqual(new_c['number_of_scans'], 4)

        # now if we assign one scan to another archive_id, should have one scan less
        self.app.put(localurl(scans[1]['URL']), {'archiveFile': 'some_other_archivefile'})

        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, qry)
        new_c = response.json['results'][0]
        self.assertEqual(new_c['number_of_scans'], 3)

        # we expect that all other fields (of the component) are still there
        for k in c:
            if k not in ['number_of_scans', '_version_']:
                self.assertEqual(c[k], new_c[k], k)

    def test_component_status(self):
        """check that the status of the corresponding archivefile is returned with the component"""
        ead_data = self.add_one_ead(dontlog=True).json
        # get a  component
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, {'ead_id': ead_data['ead_id'], 'is_archiveFile': True})
        component = response.json['results'][0]
        # get the info of this component from the component
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_data['ead_id'], 'xpath': component['xpath']})
        component = response.json['results'][0]

        self.assertEqual(component['status'], config.STATUS_NEW)
        # now change the status of the corresponding archive file
        archivefile_url = config.SERVICE_ARCHIVEFILE_ITEM.replace('{archive_id}', str(component['archive_id'])).replace('{archiveFile}', component['archiveFile'])

        self.app.put(localurl(archivefile_url), {'status': config.STATUS_PUBLISHED})

        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_data['ead_id'], 'xpath': component['xpath']})
        component = response.json['results'][0]
        self.assertEqual(component['status'], config.STATUS_PUBLISHED)

        # if we reindex the component, we should have the same data
        reindex_all(context=self)
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_data['ead_id'], 'xpath': component['xpath']})
        self.assert_dict_equality(component, response.json['results'][0])

    def test_for_non_c_elements(self):
        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        response = self.add_one_ead(filecontents=filecontents, dontlog=True).json
        ead_id = response['ead_id']
        response_components = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, {'ead_id': ead_id, 'is_component': True})
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, {'ead_id': ead_id, 'is_component': False})
        # we should find our components
        self.assertTrue(response_components.json['results'][1] in response.json['results'])
        # we now should find also non-c-components
        self.assertTrue(response.json['total_results'] > response_components.json['total_results'])

        # search for some text that we know is only available in a certain component
        txt = 'Handwritten documents on paper'
        qry = {'ead_id': ead_id, 'is_component': False, 'contains_text': txt}
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, qry)
        self.assertEqual(response.json['total_results'], 1)

        # this text occurs in exactly one component
        txt = "1622 january 26 - 1623 january 31"
        qry = {'ead_id': ead_id, 'is_component': False, 'contains_text': txt}
        response = self.app.get(config.SERVICE_COMPONENTS_COLLECTION, qry)
        self.assertEqual(response.json['total_results'], 1)

    def test_search_components(self):
        filecontents = self.get_default_filecontents(filename=TEST_FILENAME)
        result = self.add_one_ead(filename=TEST_FILENAME,
             filecontents=filecontents, dontlog=True)
        ead_id = result.json['ead_id']

        self.assertEqual(search_components(context=self, ead_id=ead_id)['total_results'], 43)
        self.assertEqual(search_components(context=self, ead_id=ead_id, is_component=True)['total_results'], 9)
        self.assertEqual(search_components(context=self, ead_id=ead_id, is_archiveFile=True)['total_results'], 4)
        self.assertEqual(search_components(context=self, ead_id=ead_id, is_component=True, is_archiveFile=False)['total_results'], 5)

    def test_ead2view(self):
        # parse an example file
        example_fn = os.path.join(TESTFILES_DIR, 'marco-roling-archief.ead.xml')
        root = etree.parse(example_fn)
        ls = ead2view()

        # test for each xpath if it is valid by runnig it
        for l in ls:
            try:
                root.xpath(l.xpath)
            except etree.XPathEvalError, error:
                raise Exception('%s (%s)' % (l.xpath, error))

        # here are some test data taken from marco's document, pairs of header and expected value
        test_data = [
            ('Identification', ['Inventaris_MROL-AAAARCH']),
            ('Creator', ['NL-Marco']),
#            ('Title', ['']),
            ('Author', ['Nog maar eens een opmerking van de archivaris']),
            ('Publisher', ['Marco Archief Instelling']),
            ('Date of publication', ['2012-12-21']),
            ('Language', ['Dutch']),
            ('Archive description rules', ['Blablabla geen regels']),
            ('Archive Introduction', ['']),
            # note that title occurs several times, and we ony test for the latest
            ('Title', ['Marco Archief']),
            ('Reference code', ['MROL-AAAARCH']),
            ('Repository code', ['NL-Marco']),
            ('Date period', ['2012-1-1 - 2012-12-31']),
            ('Name of creator(s) of the description', ['Marco Roling']),
            ('Extent and medium', ['Heel veel meters papier. Eindeloze meters.\nEr komt gewoon geen einde aan zeg ik.']),
            ('Repository name', ['Marco Archief Instelling']),
            ('Repository address', ['Ergens 123', 'Amsterdammertje', 'Daaro', 'Netherlands', '1234XX', 'Telephone: 06123456789', 'Fax: 01231234567', 'Email: info@marcoroling.nl', 'www.marcoroling.nl']),
            ('Main language of the original', ['Dutch']),
            ('Archive Description', ['']),
            ('Scope and content', ['Een levendig archief']),
            ('System of arrangement', ['Volkomen willekeurige bijeengeschraapte hoeveelheid papier in twee series geknikkerd']),
            ('Physical and technical characteristics ', ['Let op brandbaar materiaal en je kunt er alleen bij met een Atari spelcomputer']),
            ('Appraisal, destruction, scheduling', ['Een poging om het in de fik te steken is mislukt']),
            ('Source of acquisition', ['Van niemand overgenomen']),
            ('Accruals', ['Eke dag komt er een blaadje bij']),
            ('Archival history', ['Ergens in de zeventiger jaren is het verplaatst ergens naar toe.']),
            ('Location of originals', ['Er zijn geen originelen elders']),
            ('Location of copies', [u'Er zijn geen kopi\xebn elders']),
            ('Related units of description', ['Er zijn geen ander archieven die met dit archief te maken hebben']),
            ('Conditions governing access', ['Niks illegaals aan']),
            ('Conditions governing reproduction', ['Kopieer alles maar']),
            ('Other finding aids', ['Verloren gegaan bierviltje, heb ik al gezegd']),
            ('Publication note', ['Jantje zag eens pruimen hangen\nO als eieren zo groot', 'En van je hela hola we nemen er nog eentje']),
        ]

        caption2xpath = dict((l.caption_en, l.xpath) for l in ls if not l.xpath.startswith('/ead/archdesc[@level="fonds"]/dsc/'))
        for header, expected_value in test_data:
            xpath = caption2xpath[header]
            result = root.xpath(xpath)
            result = [x.strip() for x in result]

            msg = {
                'xpath': xpath,
                'header': header,
                'expected_value': expected_value,
                'result': result,
            }
            self.assertEqual(expected_value, result, unicode(msg))

    def test_get_component_for_viewer(self):
        self._add_some_eads()
        url = config.SERVICE_COMPONENT_TREE
        ead_id = self.ead_id2
        components = self.app.get(url, {'ead_id': ead_id}).json['results']

        url = config.SERVICE_GET_COMPONENT_FOR_VIEWER

        #
        # the first result is a text node, and should have children as defined in ead2view
        #
        response = self.app.get(url, {
            'xpath': components[0]['xpath'],
            'ead_id': ead_id})
        results = response.json['results']
        # check sanity
        self.assertEqual(len(results), 1)
        component = results[0]

        self.assertTrue(component['children'])
        self.assertEqual(component['children'][0]['title'], 'Identification')
        self.assertEqual(component['children'][1]['title'], 'Creator', component['children'])

        #
        # The second result
        #
        response = self.app.get(url, {
            'xpath': components[1]['xpath'],
            'ead_id': ead_id}
            )
        results = response.json['results']
        # check sanity
        self.assertEqual(len(results), 1)
        component = results[0]

        self.assertTrue(component['children'])

        # get the child with the addressline
        child_address = [x for x in component['children'] if 'addressline' in x['xpath']][0]
        self.assertEqual(child_address['title'], 'Repository address')
        self.assertEqual(child_address['text'][1], 'Jakarta')
        # this is not a component
        self.assertEqual(child_address['is_component'], False)
        # it has a single breadcrumbs, consisting of its parent
        self.assertEqual(child_address['breadcrumbs'], [[u'/ead/archdesc/did/text()[1]', u'Archive Introduction']])

        origination = [x for x in component['children'] if 'origination' in x['xpath']][0]
        self.assertTrue(origination['text'][0].startswith('the Governor-General'), origination)

        #
        # the last two results are component nodes.
        # They should have children only when they are parents of archiveFile nodes
        #
        response = self.app.get(url, {
            'xpath': components[-1]['xpath'],
            'ead_id': ead_id})
        results = response.json['results']
        self.assertEqual(len(results), 1)
        component = results[0]
        self.assertEqual(len(component['children']), 1)

        response = self.app.get(url, {
            'xpath': components[-2]['xpath'],
            'ead_id': ead_id})
        results = response.json['results']
        self.assertEqual(len(results), 1)
        component = results[0]
        self.assertEqual(len(component['children']), 1)

        #
        # check if our results are complete
        #
        response = self.app.get(url, {'xpath': components[-1]['xpath'], 'ead_id': ead_id})

    def test_get_component_for_viewer_by_archiveFile(self):
        """components are also searchable by archiveFile"""

        self._add_some_eads()
        ead_id = self.ead_id2

        url = config.SERVICE_GET_COMPONENT_FOR_VIEWER

        # get a component that has archiveFile defined
        response = self.app.get(url, {
            'archiveFile': '855',
            'ead_id': ead_id})

        self.assertEqual(response.json['results'][0]['archiveFile'], '855')

    def test_get_component_for_viewer_is_ordered(self):
        test_fn = 'ID-ANRI_K.66a_01.ead.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        response = self.add_one_ead(filecontents, filename=test_fn)
        ead_id = response.json['ead_id']

        # check if the components have a sequenceNumber
        def assert_components_have_sequenceNumber():
            for c in search_components(self)['results']:
                assert c.get('sequenceNumber') is not None, c

        assert_components_have_sequenceNumber()

        # get a component that has archiveFile defined
        def get_ordered_archives():
            response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {
                'xpath': '/ead/archdesc/dsc/c[1]/c/c/c',
                'ead_id': ead_id})

            children = response.json['results'][0]['children']
            return [c['archiveFile'] for c in children]

        original_order = ['853', '854', '855']

        self.assertEqual(get_ordered_archives(), original_order)

        scan_data = copy.deepcopy(self.scan_data)
        scan_data['archive_id'] = '1'
        scan_data['archiveFile'] = original_order[0]
        scan_data = self.add_one_scan(scan_data=scan_data).json

        self.assertEqual(get_ordered_archives(), original_order)

        # we we publish the first archiveFile, and hope the order does not change
        self.app.post(config.SERVICE_ARCHIVEFILE_ITEM.format(archive_id=1, archiveFile=original_order[1]), {'status': config.STATUS_PUBLISHED})
        self.app.post(config.SERVICE_ARCHIVEFILE_ITEM.format(archive_id=1, archiveFile=original_order[0]), {'status': config.STATUS_NEW})
        self.app.post(config.SERVICE_ARCHIVEFILE_ITEM.format(archive_id=1, archiveFile=original_order[0]), {'status': config.STATUS_PUBLISHED})

        self.assertEqual(get_ordered_archives(), original_order)
        # now remove our scan
        self.app.delete(localurl(scan_data['URL']))
        self.assertEqual(get_ordered_archives(), original_order)

        assert_components_have_sequenceNumber()

        # now upload another file with similar contents at the same ead_id
        test_fn2 = 'ID-ANRI_K.66a_01.ead.modified.xml'
        filecontents = self.get_default_filecontents(filename=test_fn2)
        response = self.change_ead(filecontents, filename=test_fn)
        assert_components_have_sequenceNumber()

        # now we upload the original file again, and we should have our original order back
        filecontents = self.get_default_filecontents(filename=test_fn)
        response = self.change_ead(filecontents, filename=test_fn)
        assert_components_have_sequenceNumber()

    def test_get_component_for_viewer_southafrica(self):
        """the EAD from south africa has the property that the components of type 'file' have children themselves"""
        test_fn = 'southafrica.xml'
        filecontents = self.get_default_filecontents(filename=test_fn)
        response = self.add_one_ead(filecontents=filecontents, dontlog=True).json

        # these are all root elements of the tree
        url = config.SERVICE_COMPONENT_TREE
        ead_id = response['ead_id']
        components = self.app.get(url, {'ead_id': ead_id}).json['results']

        # we now get one branch of the tre        self._add_some_eads()e
        url = config.SERVICE_GET_COMPONENT_FOR_VIEWER
        response = self.app.get(url, {
            'xpath': components[-2]['xpath'],
            'ead_id': ead_id})
        # now the component we found should have children and children of children
        children = response.json['results'][0]['children']
        children_of_children = children[0]['children']
        self.assertTrue(children_of_children)

        # these children of children should not be in the tree
        self.assertEqual(children_of_children[0]['show_in_tree'], False)
        # and neither their parents
        self.assertEqual(children[0]['show_in_tree'], False)

        # we don't want to see the direct parents of children of children in the breadcrumbs

        self.assertFalse(children[0]['xpath'] in [x[0] for x in children_of_children[0]['breadcrumbs']])

    def test_attributes(self):
        _ead_id1, ead_id2 = self._add_some_eads()
        # check if attributes are there
        component = self.some_component
        self.assertEqual(component['level'], 'file')
        self.assertEqual(component['xpath'], '/ead/archdesc/dsc/c[1]/c/c/c/c[1]')
        self.assertEqual(component['ead_id'], ead_id2)
        self.assertEqual(component['title'], u'1613 november 30 - 1620 october 1')

        self.assertEqual(len(component['breadcrumbs']), 4)
        self.assertEqual(type(component['breadcrumbs']), type([]))
        self.assertEqual(type(component['breadcrumbs'][1]), type([]))

        # now check if all non-tree components have a breadcrumb
        url = config.SERVICE_COMPONENTS_COLLECTION
        components = self.app.get(url).json['results']
        # each of these components should hav breadcrumbs defined, it if it not shown in the tree
        for component in components:
            if not component['show_in_tree']:
                self.assertTrue(component['breadcrumbs'], component)

    def test_translation_of_captions(self):
        # add the file that has langusage= ind
        ead_id = 'ID-ANRI_K.66a_01.ead.modified.xml'
        filecontents = self.get_default_filecontents(filename=ead_id)
        self.add_one_ead(filename=ead_id, filecontents=filecontents, dontlog=True)

        url = config.SERVICE_GET_COMPONENT_FOR_VIEWER
        xpath = '/ead/eadheader/text()[1]'
        response = self.app.get(url, {'xpath': xpath, 'ead_id': ead_id})
        self.assertEqual(response.json['results'][0]['title'], 'Deskripsi sarana temu balik arsip')

    def test_if_all_components_are_reindexed(self):
        """a regression bug: add ead files in different languages, publish an archive file of one, components are not updated in both"""
        fn = 'ID-ANRI_K.66a_01.ead.xml'
        ead_id_eng = 'ead_eng.xml'
        ead_id_ind = 'ead_ind.xml'
        archivefile_id = '856'

        filecontents_eng = self.get_default_filecontents(filename=fn)
        filecontents_ind = filecontents_eng.replace('langcode="eng"', 'langcode="ind"')

        self.add_one_ead(filename=ead_id_eng, filecontents=filecontents_eng, dontlog=True)
        self.add_one_ead(filename=ead_id_ind, filecontents=filecontents_ind, dontlog=True)

        #
        # now we should have an archive file in both languages
        #
        response = self.app.get(config.SERVICE_ARCHIVEFILE_COLLECTION, {'archiveFile': archivefile_id})
        # assert sanity: we should find one archive file
        self.assertEqual(response.json['total_results'], 1)
        archivefile_info = response.json['results'][0]
        self.assertEqual(archivefile_info['status'], config.STATUS_NEW)

        # now get the component information of the english ead
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_id_eng, 'archiveFile': archivefile_id})
        # the reported bug was about the status value
        self.assertEqual(response.json['results'][0]['status'], archivefile_info['status'])
        # repeat for the indoneisan version
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_id_ind, 'archiveFile': archivefile_id})
        self.assertEqual(response.json['results'][0]['status'], archivefile_info['status'])

        # now publisch the archive file
        self.app.put(localurl(archivefile_info['URL']), {'status': config.STATUS_PUBLISHED})
        archivefile_info = self.app.get(localurl(archivefile_info['URL'])).json
        self.assertEqual(archivefile_info['status'], config.STATUS_PUBLISHED)

        # now get the component information of the english ead
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_id_eng, 'archiveFile': archivefile_id})
        # the reported bug was about the status value
        self.assertEqual(response.json['results'][0]['status'], archivefile_info['status'])
        # repeat for the indoneisan version
        response = self.app.get(config.SERVICE_GET_COMPONENT_FOR_VIEWER, {'ead_id': ead_id_ind, 'archiveFile': archivefile_id})
        self.assertEqual(response.json['results'][0]['status'], archivefile_info['status'])

    def test_if_sort_field_is_indexed(self):
        # each component shoudl turn up as an archivefile, and as such have a sort_field
        self._add_some_eads()

        response = self.solr_archivefile.search(q='*:*')

        self.assertEqual(response.total_results, 5)
        response = self.solr_archivefile.search(q='sort_field:[* TO *]')
        self.assertEqual(response.total_results, 5)
