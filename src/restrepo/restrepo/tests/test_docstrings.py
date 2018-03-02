import unittest
from restrepo import config


class TestDocStrings(unittest.TestCase):
    def test_docstrings(self):
        from restrepo.browser import scans, ead
        self.assertTrue(
            config.PARAM_ARCHIVE_ID in scans.add_scan.__doc__)
        self.assertTrue(
            config.PARAM_ARCHIVE_ID in scans.search_scans.__doc__)
        self.assertTrue(
            config.SERVICE_SCAN_ITEM in scans.get_scan_image_item_raw.__doc__)
        self.assertTrue(
            config.PARAM_STATUS in ead.update_ead_file.__doc__)
