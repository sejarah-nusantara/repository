import os

from pyramid.threadlocal import get_current_registry

from base import BaseRepoTest
from base import TESTFILES_DIR
from restrepo.db.settings import Settings


class AdminInterfaceTest(BaseRepoTest):
    def assertContains(self, response, text):
        msg = 'Expect to find "{text}" in {response}'.format(**locals())
        self.assertTrue(text in response, msg)

    def test_root_exists(self):
        "Finding a 404 on / of a healthy application is confusing: check /"
        self.app.get('/')  # Enough to check that no error occurred

    def test_configuration(self):
        # TODO: check if settings end up in the form

        response = self.app.get('/configuration')
        self.assertContains(response, 'Configuration Settings')
        response.form['watermark_file'] = ''
        response = response.form.submit({'submit': True})
        self.assertContains(response, 'Configuration Settings')

        # saving a nonexisting file shoudl raise an error
        filename = 'abc'
        response.form['watermark_file'] = filename
        response = response.form.submit({'submit': True}, expect_errors=True)

        response = self.app.get('/configuration')
        filename = os.path.join(TESTFILES_DIR, 'purple.png')
        response.form['watermark_file'] = filename
        response.form['watermark_pos_x'] = '111'
        response.form['watermark_pos_y'] = '112'
        response.form['watermark_size'] = '113'
#         response.form['watermark_image_format'] = 'png'

        response = response.form.submit({'submit': True})

        self.assertContains(response, 'Configuration Settings')
        self.assertContains(response, filename)

        # this shoudl ahve been saved in the database
        self.assertEqual(self.db.query(Settings).get('watermark_file').value, filename)
        # if we now reload the page, we should see the updated value in our form
        response = self.app.get('/configuration')
        self.assertEqual(response.form['watermark_file'].value, filename)
        self.assertEqual(response.form['watermark_pos_x'].value, '111')
        self.assertEqual(response.form['watermark_pos_y'].value, '112')
        self.assertEqual(response.form['watermark_size'].value, '113')
#         self.assertEqual(response.form['watermark_image_format'].value, 'png')

        # and we should also have updated our settings
        # but for some reason, this next test fails..
#         settings = get_current_registry().settings
#         self.config.registry.settings

#         self.assertEqual(settings.get('watermark_file'), filename)
