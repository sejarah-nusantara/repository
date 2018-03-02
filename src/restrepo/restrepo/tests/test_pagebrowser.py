# encoding=utf8
"""
Tests for pagebrowser
"""
from lxml import etree
from restrepo import config
from base import BaseRepoTest
from base import localurl


class TestPageBrowser(BaseRepoTest):

    def test_pagelist(self):
        five_scans = self.add_five_scans({'timeFrameFrom': '1700-02-03', 'timeFrameTo': '1702-09-12', 'status': config.STATUS_PUBLISHED})

        archiveFile = self.scan_data['archiveFile']
        archive_id = self.scan_data['archive_id']
        url = config.SERVICE_PAGEBROWSER_PAGELIST
        url = url.replace('{archiveFile}', archiveFile)
        url = url.replace('{archive_id}', str(archive_id))
        response = self.app.get(url)
        tree = etree.fromstring(response.body)
        self.assertEqual(tree.tag, 'bookservice')
        self.assertEqual(len(tree.xpath('//page')), len(five_scans))
        self.assertEqual(tree.xpath('//page')[1].attrib['timeFrameFrom'], '1700-02-03')
        self.assertEqual(tree.xpath('//page')[1].attrib['timeFrameTo'], '1702-09-12')

        # move a scan to check if the ordering in the pagelist works well
        self.app.post(localurl(five_scans[0]['URL']) + '/move', {'after': 5})
        response = self.app.get(url)
        tree = etree.fromstring(response.body)
        self.assertEqual(tree.xpath('//page')[4].attrib['id'], str(five_scans[0]['number']))
        self.assertEqual(tree.xpath('//page')[0].attrib['id'], str(five_scans[1]['number']))
