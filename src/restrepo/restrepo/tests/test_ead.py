#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013
#


"""
Tests for EAD CRUD and validation

for test on live server you can use commands like:

> curl -X POST --form "file=@/tmp/test_ead.xml" http://127.0.0.1:5000/ead
> curl -X DELETE http://127.0.0.1:5000/ead/test_ead.xml

"""
import re
import os
from lxml import etree
from base import BaseRepoTest, localurl
from restrepo import config
from restrepo.utils import now
from restrepo.db.ead import EadFile
from restrepo.config import ERRORS
from base import TESTFILES_DIR

BASIC_EAD = "<ead></ead>"


class TestEad(BaseRepoTest):

    def test_invalid_xml(self):
        res = self.add_one_ead(dontlog=False,
            filecontents="<wrongfile><b>Nonsense</wrongfile>", status=400)
        error = res.json['errors'][0]
        self.assertTrue('line 1' in error['description'])
        self.assertEqual(error['location'], 'postdata')
        self.assertEqual(error['name'], ERRORS.xml_syntax_error.name)

    def test_valid_xml_but_wrong_as_dtd(self):
        res = self.add_one_ead(
            filecontents="<wrongfile><b>Hello</b></wrongfile>", status=400)
        errors = res.json['errors']
        self.assertTrue('No declaration for element wrongfile'
                        in errors[0]['description'])
        self.assertTrue('No declaration for element b'
                        in errors[1]['description'])
        self.assertEqual(errors[0]['location'], 'postdata')
        self.assertEqual(errors[0]['name'], ERRORS.xml_dtd_validation_error.name)

    def test_add(self):
        """Add an EAD file"""
        res = self.add_one_ead(additional_data={'status': '2'})
        self.assertTrue('ead_id' in res.json)
        self.assertEqual(res.json['status'], 2)

    def test_add_with_lost_of_slashes(self):
        res = self.add_one_ead(filename="\\mixed/back/and/\\\\forward/slash").json
        self.assertEqual(res['ead_id'], 'slash')

    def test_disallow_direct_status_update_to_0(self):
        """Status updates to 9 are not allowed"""
        res = self.add_one_ead(additional_data={'status': 0}, status=400).json
        self.assertEqual(res['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_add_invalid_status(self):
        res = self.add_one_ead(status=400,
                               additional_data={'status': '10'})
        self.assertTrue('errors' in res.json)

    def test_error_if_upload_twice_id_from_content(self):
        """
        Uploading the same file twice gives an error.
        Id comes from file content.
        """
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents, dontlog=True)
        self.assertEqual(res.json['status'], 1)
        res = self.add_one_ead(filecontents=filecontents,
            dontlog=True, status=400)
        self.assertEqual(res.json['errors'][0]['description'],
             "A file with id 'test_file_123.xml' is already present")

    def test_error_if_upload_twice_id_from_filename(self):
        "Uploading the same file twice gives an error. Id comes from filename"
        res = self.add_one_ead()
        self.assertEqual(res.json['status'], 1)
        res = self.add_one_ead(status=400)
        self.assertEqual(res.json['errors'][0]['description'],
             "A file with id 'test_file_123.xml' is already present")

    def test_get_ead(self):
        "After storing a file we can get its contents at URL"
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents, dontlog=True)
        url = localurl(res.json['URL'])
        ead = self.app.get(url)
        self.assertEqual(ead.json['institution'], self.default_institution)
        self.assertEqual(ead.json['title'], 'Title')
        self.assertEqual(ead.json['country'], self.default_country)

    def test_get_nonexistent_ead(self):
        "Requesting a non existent url results in a 404"
        res = self.app.get('/ead/foo', status=404).json
        self.assertEqual(res['errors'][0], {
            u'description': u'File foo was not found in the database',
            u'location': u'url',
            u'name': u'ead_not_found',
        })

    def test_get_raw_ead(self):
        "After storing a file we can get its contents at URL"
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents, dontlog=True)
        url = localurl(res.json['URL'])
        ead = self.app.get(url + '/file')
        self.assertEqual(ead.content_type, 'text/xml')
        self.assertEqual(ead.body, filecontents)

    def test_delete(self):
        """delete an EAD file"""
        put_res = self.add_one_ead(dontlog=True)
        res = self.app.get('/ead')
        self.assertEqual(len(res.json['results']), 1)
        url = put_res.json['URL']
        self.app.delete(localurl(url))
        res = self.app.get('/ead')
        self.assertEqual(len(res.json['results']), 0)
        # trying to get the EAD should now return an 400 error
        self.app.get(localurl(url), status=404)
        # we should now be able to add a new file with the same id
        put_res = self.add_one_ead(dontlog=True)

    def test_ead_update(self):
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents)
        url = localurl(res.json['URL'])
        TO_REPLACE = 'UNITTITLE'
        self.assertTrue(TO_REPLACE in filecontents)
        newfilecontents = filecontents.replace(TO_REPLACE, 'changed_string')
        filetuple = ('file', 'test_file_123.xml', newfilecontents)
        then = now()
        res = self.app.put(url, upload_files=[filetuple], extra_environ={'dontlog_web_chats': '1'})
        self.assertMoreRecent(res.json['dateLastModified'], then)
        ead = self.app.get(url + '/file', extra_environ={'dontlog_web_chats': '1'})
        self.assertEqual(ead.content_type, 'text/xml')
        self.assertEqual(ead.body, newfilecontents)

    def test_ead_update_with_empty_body(self):
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents, dontlog=True)
        url = localurl(res.json['URL'])
        # an empty body should just return a 200 OK and leave the data intact
        res1 = self.app.put(url)
        self.assertEqual(res.json, res1.json)

    def test_ead_update_status1(self):
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents)
        url = localurl(res.json['URL'])
        # change the status
        res = self.app.put(url, {'status': 2}).json
        self.assertEqual(res['status'], 2)
        # check if the status is really there
        res = self.app.get(url).json
        self.assertEqual(res['status'], 2)

    def test_ead_update_status0(self):
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents)
        url = localurl(res.json['URL'])
        res = self.app.put(url, {'status': 0}, status=400).json
        self.assertEqual(res['errors'][0]['name'], ERRORS.invalid_parameter.name)

    def test_ead_update_different_filename(self):
        filecontents = self.get_default_filecontents()
        res = self.add_one_ead(filecontents=filecontents).json
        url = localurl(res['URL'])
        new_filecontents = filecontents.replace('test_file_123.xml', 'another_id')
        filetuple = ('file', 'another_filename.xml', new_filecontents)
        res = self.app.put(url, upload_files=[filetuple], status=400).json

    def test_search(self):
        default_filecontents = self.get_default_filecontents()
        filecontents = default_filecontents.replace(
            'GH-PRAAD', 'ID-JaAN').replace('RG1', 'HR')

        self.add_one_ead(filecontents=filecontents,
            filename="1.xml", dontlog=True)

        self.add_one_ead(filecontents=filecontents,
            filename="2.xml", dontlog=True)

        filecontents = default_filecontents.replace(
            'GH-PRAAD', 'ID-JaAN').replace('RG1', 'Krawang')
        self.add_one_ead(filecontents=filecontents,
            filename="3.xml", dontlog=True)
        filecontents = default_filecontents.replace(
            'GH-PRAAD', 'GH-PRAAD').replace('RG1', 'MFA')
        self.add_one_ead(filecontents=filecontents,
            filename="4.xml", dontlog=True)

        res = self.app.get(config.SERVICE_EAD_COLLECTION).json
        self.assertEqual(res['total_results'], 4)
        self.assertEqual(len(res['results']), 4)

        res = self.app.get(config.SERVICE_EAD_COLLECTION,
            {'institution': 'ID-JaAN'}).json
        self.assertEqual(res['total_results'], 3)

        res = self.app.get(config.SERVICE_EAD_COLLECTION,
            {'institution': 'XXX'}).json
        self.assertEqual(res['total_results'], 0)

        res = self.app.get(config.SERVICE_EAD_COLLECTION,
            {'archive': 'MFA'}).json
        self.assertEqual(res['total_results'], 1)

        res = self.app.get(config.SERVICE_EAD_COLLECTION, {'archive_id': '1'}).json
        self.assertEqual(res['total_results'], 2)

        res = self.app.get(config.SERVICE_EAD_COLLECTION,
            {'findingaid': 'FindingAid'}).json
        self.assertEqual(res['total_results'], 4)

        res = self.app.get(config.SERVICE_EAD_COLLECTION,
            {'findingaid': 'NonExistingFindingAid'}).json
        self.assertEqual(res['total_results'], 0)

    def test_persistency(self):
        """test if all data survice saving and indexing"""
        original = self.add_one_ead().json
        # if we get the single file from its url directly, the results should be the same
        direct_result = self.app.get(original['URL']).json
        original_without_URL = dict(original)
        del original_without_URL['URL']
        self.assert_dict_equality(original_without_URL, direct_result)

        # search_result comes from SOLR
        search_result = self.app.get(config.SERVICE_EAD_COLLECTION).json['results'][0]
        self.assert_dict_equality(original, search_result)

    def do_check_file_path_is_ignored(self, path):
        filecontents = self.get_default_filecontents()
        filetuple = ('file', path, filecontents)
        ead = self.app.post('/ead', upload_files=[filetuple]).json
        self.assertEqual(ead['ead_id'], 'somefile.xml')

    def test_linux_style_file_path_is_ignored(self):
        self.do_check_file_path_is_ignored(
            "/tmp/somedir/anotherlevel/somefile.xml"
        )

    def test_windows_style_file_path_is_ignored(self):
        self.do_check_file_path_is_ignored(
            r"C:\Programs\Adobe\Photoshop\whatever\somefile.xml"
        )

    def test_get_archive_info(self):
        filecontents = self.get_default_filecontents()
        then = now()
        res = self.add_one_ead(filecontents=filecontents, dontlog=True).json

        self.assertEqual(res['institution'], self.default_institution)
        self.assertEqual(res['archive'], self.default_archive)
        self.assertMoreRecent(res['dateLastModified'], then)
        self.assertEqual(res['language'], self.default_language)
        self.assertEqual(res['findingaid'], 'FindingAid')

        # if we change the filecontents, we should see that reflected in the reult
        filecontents = filecontents.replace(self.default_institution, 'ID-JaAN')
        filecontents = filecontents.replace(self.default_archive, 'Krawang')
        res = self.change_ead(filecontents=filecontents).json
        self.assertEqual(res['archive'], 'Krawang')

    def test_error_on_archive_info(self):
        # TODO: these test should also pass after "PUT"
        valid_content = self.get_default_filecontents()

        # if no repo code is given, we should get an error
        invalid_content = re.sub('repositorycode=".*?"', '', valid_content)
        res = self.add_one_ead(filecontents=invalid_content,
            dontlog=True, status=400).json
        self.assertTrue('invalid value for institution' in
            res['errors'][0]['description'].lower())

        # if the whole element where we look for the instutition is missing,
        # we should get an error.
        invalid_content = re.sub(
            '<unitid.*?repositorycode=".*?".*?>.*?</unitid>', '', valid_content
        )
        res = self.add_one_ead(filecontents=invalid_content,
            dontlog=True, status=400).json
        self.assertTrue('invalid value for institution' in
            res['errors'][0]['description'].lower())

        # if the content of the eadid tag is missing, we cannot find an archive
        invalid_content = re.sub(self.default_archive, '', valid_content)
        res = self.add_one_ead(filecontents=invalid_content,
            dontlog=True, status=400).json
        self.assertTrue('invalid value for archive' in
            res['errors'][0]['description'].lower())

        # we cannot upload a file with an non-existing archive,
        invalid_content = re.sub(self.default_institution, 'ghost_institution', valid_content)
        res = self.add_one_ead(filecontents=invalid_content,
            dontlog=True, status=400)
        self.assertEqual(res.status, '400 Bad Request')

    def test_ead_with_archiveFile_with_spaces(self):
        """if an archiveFile contains spaces, it the EAD file should be rejected"""
        valid_content = self.get_default_filecontents()
        valid_content = valid_content.replace('ARCHIVE_FILE_ID', 'an archive id with spaces')
        # an archiveFile id (<unitid>) with spaces is accepted by the DTD
        self.add_one_ead(filecontents=valid_content, dontlog=True, status=200)

    def test_no_error_when_normal_field_is_missing(self):
        """nothing should break if the 'normal' attribute of unitdate is missing"""
        filecontents = self.get_default_filecontents()
        filecontents = filecontents.replace('normal="1612/1812"', '')
        _res = self.add_one_ead(filecontents=filecontents, dontlog=True).json

    def test_extract_components(self):
        ead_id = 'ID-ANRI_K.66a_01.ead.xml'
        fp = os.path.join(TESTFILES_DIR, ead_id)
        ead_file = EadFile(context=self, ead_id=ead_id)
        # a hack to make this work quickly

        def _get_xml_tree():
            _tree = etree.parse(fp)
            return _tree
        ead_file._get_xml_tree = _get_xml_tree

        components = ead_file.extract_components()
        self.assertEqual(len(components), 43)
        for x in components:
            self.assertEqual(x.ead_id, ead_id)

        self.assertEqual(components[11].parent, components[9].eadcomponent_id)
        self.assertEqual(components[1].text, ['K.66a'])
        self.assertEqual(components[1].title, 'Identification')
        self.assertEqual(components[1].search_source, 'K.66a')

        self.assertTrue(components[20].text[0].startswith('Handwritten documents'))
        self.assertTrue('handwritten documents' in components[20].search_source.lower())

        # now we should have two root elements that are components
        self.assertEqual(len([c for c in components if c.is_component]), 9)
        self.assertEqual(len([c for c in components if c.is_component and not c.parent]), 2)

    def test_ead_with_invalid_date(self):
        filename = 'invalid_date.ead.xml'

        filecontents = open(os.path.join(TESTFILES_DIR, filename)).read()
        filetuple = ('file', filename, filecontents)
        dontlog = '1'
        response = self.app.post('/ead', upload_files=[filetuple], extra_environ={'dontlog_web_chats': dontlog})
        # we DELETE a
        self.app.delete(localurl(response.json['URL']))
        # now we add it again
        response = self.app.post('/ead', upload_files=[filetuple], extra_environ={'dontlog_web_chats': dontlog})
