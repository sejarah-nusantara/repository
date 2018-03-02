#
# copyright Gerbrandy SRL
# www.gerbrandy.com
# 2013-..
#
import os

from restrepo.tests.base import BaseRepoTest

UNKNOWN = {'REMOTE_ADDR': '10.10.10.10'}

PROXIED = {
    'REMOTE_ADDR': '127.0.0.1',
    "HTTP_X_FORWARDED_FOR": "123.123.0.1"
}


class TestSecurity(BaseRepoTest):

    def test_add_scan(self):
        # We expect a 403 (unauthorized) from an unknown IP
        self.app.post('/scans', extra_environ=UNKNOWN, status=401)
        # But from a known IP the usual validation (we're not sending a valid request) applies
        self.app.post('/scans', extra_environ={'REMOTE_ADDR': '127.0.0.1'}, status=400)

    def test_move_scan(self):
        self.app.post('/scans/12/move', extra_environ=UNKNOWN, status=401)

    def test_update_scan(self):
        self.app.put('/scans/12', extra_environ=UNKNOWN, status=401)

    def test_delete_scan(self):
        self.app.delete('/scans/12', extra_environ=UNKNOWN, status=401)

    def test_add_ead(self):
        self.app.post('/ead', extra_environ=UNKNOWN, status=401)

    def test_edit_ead(self):
        self.app.put('/ead/test', extra_environ=UNKNOWN, status=401)

    def test_delete_then_add_an_ead(self):
        response = self.add_one_ead()
        # we added one ead file - we should find the file and
        ead_id = response.json['ead_id']
        # we should find our file now stored where it should
        self.assertTrue(os.path.exists(os.path.join(self.repo_path, 'ead_files', ead_id)))
        self.assertTrue(ead_id in [x['ead_id'] for x in self.app.get('/ead').json['results']])
        # now if we try to delete it, but are not authorized to do so, both ead
        self.app.delete(str('/ead/' + ead_id), extra_environ=UNKNOWN, status=401)
        self.assertTrue(os.path.exists(os.path.join(self.repo_path, 'ead_files', ead_id)))
        self.assertTrue(ead_id in [x['ead_id'] for x in self.app.get('/ead').json['results']])

    def test_proxied_request(self):
        response = self.app.get('/admin_archives', extra_environ=PROXIED, status=401)
        self.assertTrue(response.headers['WWW-Authenticate'])

        # Add admin/admin credentials
        # (to not have the password in clear, we encrypt it:)
        # import base64
        # base64.b64encode('admin:PASSWORD')}

        headers = {'Authorization': 'Basic %s' % 'YWRtaW46N1hKblJuVlQ='}
        self.app.get('/admin_archives', extra_environ=PROXIED, headers=headers)
