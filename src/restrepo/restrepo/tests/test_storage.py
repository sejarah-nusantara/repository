import unittest
from restrepo.storage import store_file, get_file_content
from restrepo.storage import move_file, delete_file, file_exists

from base import BaseRepoTest


class StorageScans(BaseRepoTest):
    PATH = "a/random/path/for.a.file"
    def test_store_get_delete(self):
        store_file(self.PATH, "My content")
        content = get_file_content(self.PATH)
        self.assertEqual("My content", content)
        self.assertTrue(file_exists(self.PATH))
        delete_file(self.PATH)
        self.assertTrue(not file_exists(self.PATH))
        self.assertRaises(Exception, get_file_content, [self.PATH])
    def test_move(self):
        store_file(self.PATH, "My content")
        move_file(self.PATH, "another/path")
        self.assertTrue(not file_exists(self.PATH))
        self.assertTrue(file_exists("another/path"))
        content = get_file_content("another/path")
        self.assertEqual("My content", content)

