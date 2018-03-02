# encoding=utf8
import datetime
import unittest

from restrepo.utils import is_NMTOKEN
from restrepo.utils import string_to_datetime


class UtilsTest(unittest.TestCase):
    def test_is_NMTOKEN(self):
        self.assertTrue(is_NMTOKEN('aaa'))
        self.assertTrue(is_NMTOKEN(u'aàa'))
        self.assertTrue(is_NMTOKEN('-.'))
        self.assertFalse(is_NMTOKEN('a/a'))
        self.assertFalse(is_NMTOKEN('a a'))

    def test_string_to_datetime(self):
        self.assertEqual(string_to_datetime('2000').year, 2000)
        self.assertEqual(string_to_datetime('2000').month, 1)
        self.assertEqual(string_to_datetime('2000').day, 1)
        self.assertEqual(string_to_datetime('2000', default=datetime.datetime(1234,12, 31)).day, 31)
