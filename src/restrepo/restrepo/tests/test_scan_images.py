import os
import glob
from StringIO import StringIO
from base import BaseRepoTest
from base import TEST_IMAGE_TIF, localurl
from base import TEST_IMAGE_PNG
from base import TEST_IMAGE_ZACKTHECAT
from base import TEST_IMAGE_300DPI
from PIL import Image
from restrepo.db.scans import Scan
from restrepo.db.scan_images import ScanImage
from restrepo.storage import real_path


class TestScanImages(BaseRepoTest):

    def test_delete_removes_files(self):
        scan_data = self.add_one_scan().json
        id = scan_data['images'][0]['id']  # @ReservedAssignment
        scan = self.db.query(Scan).one()
        # create a thumbnail (note that our image is 2x2, so we need to make it just one pixel
        self.app.get(localurl(scan_data['URL'] + '/image'), {'size': 'x1'})
        thumbnail_dir = real_path(scan._get_thumbnail_dir())
        # just cehck for sanity that the htumanil dir exists
        self.assertTrue(os.path.exists(thumbnail_dir))

        # add another scan to check that the first one is not affected
        scan_data2 = self.add_one_scan().json
        id2 = scan_data2['images'][0]['id']
        self.app.get(localurl(scan_data2['URL'] + '/image'), {'size': 'x1'})
        scan2 = self.db.query(Scan).filter(Scan.number == scan_data2['number']).one()

        # check if images and thumbnailsare all there
        self.assertTrue(os.path.exists(real_path(scan.get_file_path(id))))
        self.assertTrue(os.path.exists(real_path(scan2.get_file_path(id2))))
        self.assertTrue(os.path.exists(thumbnail_dir))
        thumbnails = glob.glob(real_path(scan._thumbnail_basepath(id)) + '*')
        self.assertEqual(len(thumbnails), 1)
        thumbnails = glob.glob(real_path(scan2._thumbnail_basepath(id2)) + '*')
        self.assertEqual(len(thumbnails), 1)

        # now delete the first scan
        self.app.delete(localurl(scan_data['URL']))

        # the files of the first scan should all be gone
        self.assertFalse(os.path.exists(real_path(scan.get_file_path(id))))
        thumbnails = glob.glob(real_path(scan._thumbnail_basepath(id)) + '*')
        self.assertEqual(len(thumbnails), 0)

        # check also that the second scan files are still there
        self.assertEqual(self.db.query(Scan).count(), 1)
        self.assertTrue(os.path.exists(real_path(scan2.get_file_path(id2))))
        thumbnails = glob.glob(real_path(scan2._thumbnail_basepath(id2)) + '*')
        self.assertEqual(len(thumbnails), 1)

    def test_get_image(self):
        "Get image returns the correct content/type"
        result = self.add_one_scan(self.scan_data).json
        url = localurl(result['URL'])
        result = self.app.get(url + '/image')

    def test_update_image(self):
        """changing image removes all previous images"""
        result = self._add_one_scan_with_two_images()
        then = result['dateLastModified']
        self.assertEqual(len(result['images']), 2)
        scan_url = localurl(result['URL'])

        # now change the file
        filetuple = ('file', 'test_fn', TEST_IMAGE_TIF)
        result = self.app.put(scan_url, upload_files=[filetuple], extra_environ={'dontlog_web_chats': ''})
        self.assertEqual(len(result.json['images']), 1)
        self.assertMoreRecent(result.json['dateLastModified'], then)

        self.app.put(scan_url, {'user': 'someuser'}, upload_files=[filetuple], extra_environ={'dontlog_web_chats': ''})

    def test_update_image_post(self):
        """changing image removes all previous images

        [this is the exact same test as test_update_imge, but using a post request]
        """

        result = self._add_one_scan_with_two_images()
        self.assertEqual(len(result['images']), 2)
        url = localurl(result['URL'])

        # now change the file
        filetuple = ('file', 'test_fn', TEST_IMAGE_TIF)
        result = self.app.post(url, upload_files=[filetuple], extra_environ={'dontlog_web_chats': ''})
        self.assertEqual(len(result.json['images']), 1)

    def test_scan_thumbnail_validation(self):
        "Invalid values for `size` should trigger a meaningful error"
        scan = self.add_one_scan().json
        url = localurl(scan['URL']) + '/image?size='
        self.app.get(url + 'x', status=400)
        self.app.get(url + 'ax', status=400)
        self.app.get(url + '120xc', status=400)
        self.app.get(url + 'axb', status=400)

    def test_scan_thumbnail_width(self):
        "Ensure a thumbnail is correctly generated"
        scan = self.add_one_scan(filecontents=TEST_IMAGE_ZACKTHECAT).json
        url = localurl(scan['URL']) + '/image?size=100x'
        res = self.app.get(url)
        self.assertEqual(res.content_type, 'image/jpeg')
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.size, (100, 91))

    def test_scan_thumbnail_height(self):
        "Ensure a thumbnail is correctly generated"
        scan = self.add_one_scan(filecontents=TEST_IMAGE_ZACKTHECAT).json
        url = localurl(scan['URL']) + '/image?size=x100'
        res = self.app.get(url)
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.size, (109, 99))

    def test_scan_thumbnail_height_width(self):
        "Ensure a thumbnail is correctly generated"
        scan = self.add_one_scan(filecontents=TEST_IMAGE_ZACKTHECAT).json
        url = localurl(scan['URL']) + '/image?size=80x80'
        res = self.app.get(url)
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.size, (80, 72))

        # just passing a number is interpreted as a max on the height
        url = localurl(scan['URL']) + '/image?size=80'
        res = self.app.get(url)
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.size[1], 79)

        # 0 should give us a 404
        url = localurl(scan['URL']) + '/image?size=0'
        res = self.app.get(url, expect_errors=True)
        self.assertEqual(res.status_code, 400)
        url = localurl(scan['URL']) + '/image?size=0x'
        res = self.app.get(url, expect_errors=True)
        self.assertEqual(res.status_code, 400)
        url = localurl(scan['URL']) + '/image?size=x0'
        res = self.app.get(url, expect_errors=True)
        self.assertEqual(res.status_code, 400)
        url = localurl(scan['URL']) + '/image?size=0x0'
        res = self.app.get(url, expect_errors=True)
        self.assertEqual(res.status_code, 400)

    def test_scan_dpi(self):
        "Ensure a thumbnail is correctly generated"
        img = Image.open(StringIO(TEST_IMAGE_300DPI))
        self.assertEqual(img.info['dpi'], (300, 300))

        scan = self.add_one_scan(filecontents=TEST_IMAGE_300DPI).json
        url = localurl(scan['URL']) + '/image?size=80x80'
        res = self.app.get(url)
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.info['dpi'], (300, 300))

        url = localurl(scan['URL']) + '/image?size=10000x10000'
        res = self.app.get(url)
        img = Image.open(StringIO(res.body))
        self.assertEqual(img.info['dpi'], (300, 300))

    def test_scan_thumbnail_is_erased_on_update(self):
        "After updating a scan all its thumbnails are recalculated"
        scan = self.add_one_scan(filecontents=TEST_IMAGE_ZACKTHECAT).json
        url = localurl(scan['URL'])
        first_thumbnail = self.app.get(url + '/image?size=100x').body
        filetuple = ('file', 'test_fn', TEST_IMAGE_TIF)
        self.app.put(url, upload_files=[filetuple])
        second_thumbnail = self.app.get(url + '/image?size=100x').body
        self.assertTrue(first_thumbnail != second_thumbnail)

    def _add_one_scan_with_two_images(self):
        scan = self.add_one_scan(
            filename=['img1', 'img2'],
            filecontents=[TEST_IMAGE_PNG, TEST_IMAGE_PNG],
            enabled_web_chat=False).json
        return scan

    def test_scan_get_has_key_images(self):
        # add multiple images with the post request
        scan = self._add_one_scan_with_two_images()
        # the result should contain info aobut hte added images
        self.assertEqual(len(scan['images']), 2)

    def test_404_on_wrong_image_id(self):
        "A 404 is returned in case of not existing image"
        scan = self._add_one_scan_with_two_images()
        url = localurl(scan['images'][0]['URL']) + '444'  # non-existent scan
        self.app.get(url + '444', status=404)

    def test_images_item_get(self):
        scan = self._add_one_scan_with_two_images()
        # now, get the info of this scan
        scan_info = self.app.get(localurl(scan['URL']))
        self.assertEqual(len(scan_info.json['images']), 2)
        # files are uploaded in the order given
        self.assertEqual(scan_info.json['images'][0]['filename'], 'img1')
        self.assertEqual(scan_info.json['images'][1]['filename'], 'img2')
        # they have a url argument (where the info of the image can be found
        self.assertTrue('URL' in scan_info.json['images'][0])
        url = localurl(scan_info.json['images'][0]["URL"])
        scaninfo = self.app.get(url).json
        self.assertEqual(scaninfo["filename"], 'img1')
        self.assertEqual(scaninfo["is_default"], True)
        url = localurl(scan_info.json['images'][1]["URL"])
        scaninfo = self.app.get(url).json
        self.assertEqual(scaninfo["is_default"], False)

    def test_images_collection_get(self):
        scan = self._add_one_scan_with_two_images()
        response = self.app.get(localurl(scan['URL'] + '/images'))
        self.assertEqual(response.json['total_results'], 2)
        self.assertEqual(response.json['results'][0]['filename'], 'img1')
        self.assertEqual(response.json['results'][1]['filename'], 'img2')
        self.assertEqual(response.json['results'][0]['is_default'], True)

    def test_images_collection_item_delete(self):
        scan = self._add_one_scan_with_two_images()
        response = self.app.get(localurl(scan['URL'] + '/images'))
        img1_url = localurl(response.json['results'][0]['URL'])
        img2_url = localurl(response.json['results'][1]['URL'])
        # delete the first image on the collection
        self.app.delete(img1_url)
        response = self.app.get(localurl(scan['URL'] + '/images'))
        # we have one image left
        self.assertEqual(response.json['total_results'], 1)
        # and the single image is img2
        self.assertEqual(localurl(response.json['results'][0]['URL']), img2_url)
        # it became the default one
        self.assertEqual(response.json['results'][0]['is_default'], True)
        # if we try to delete the last image, we raise an error
        response = self.app.delete(img2_url, status=400)

    def test_images_collection_post(self):
        scan = self.add_one_scan(enabled_web_chat=False).json
        # check sanity - we should have one image at this point
        response = self.app.get(localurl(scan['URL'] + '/images'))
        self.assertEqual(response.json['total_results'], 1)

        # we add another image to this scan
        image_data = {'is_default': True}
        upload_files = [('file', 'img3', TEST_IMAGE_PNG)]
        response = self.app.post(localurl(scan['URL'] + '/images'), image_data, upload_files=upload_files)
        self.assertEqual(response.json['success'], True)
        self.assertEqual(len(response.json['results']), 1)

        # and we now find two images for this scan
        response = self.app.get(localurl(scan['URL'] + '/images'))
        self.assertEqual(response.json['total_results'], 2)
        self.assertTrue(response.json['results'][0]['is_default'])
        self.assertFalse(response.json['results'][1]['is_default'])
        # the non default image (the second one) should be the original one
        self.assertEqual(scan['images'][0]['URL'], response.json['results'][1]['URL'])
        image_data['user'] = 'someotheruser'
        self.app.post(localurl(scan['URL'] + '/images'), image_data, upload_files=upload_files)

    def test_key_image_url(self):
        """ the image_url at /scan/{number} should always point at the default image, and it should be unique for that image"""

        def get_identifying_url(url):
            # strip the last part of the url, that is the has value to guarantee uniqueness
            url = url.split('_')[0]
            self.assertTrue(url.endswith('/file'))
            url = url.strip('/file')
            return url

        scan = self.add_one_scan(enabled_web_chat=False).json
        # the scan has an image
        self.assertTrue('image_url' in scan)
        scan_url = localurl(scan['URL'])
        image_file_url1 = scan['image_url']
        image_url1 = get_identifying_url(image_file_url1)

        # the image_url should correspond with the default image
        response = self.app.get(scan_url + '/images')
        self.assertEqual(response.json['total_results'], 1)
        self.assertEqual(response.json['results'][0]['URL'], image_url1)

        # if we add a second image as a default image, the 'image_url' should reflect that
        # the new image is the default image
        image_data = {'is_default': True}
        upload_files = [('file', 'img3', TEST_IMAGE_PNG)]
        self.app.post(scan_url + '/images', image_data, upload_files=upload_files)
        response = self.app.get(scan_url + '/images')
        image_urls = [x['URL'] for x in response.json['results']]
        self.assertTrue(image_url1 in image_urls)

        image_urls.remove(image_url1)
        image_url2 = image_urls[0]

        self.app.put(localurl(image_url2), {'is_default': True, 'user': 'someotheruseragain'})

        scan = self.app.get(scan_url)
        self.assertEqual(get_identifying_url(scan.json['image_url']), image_url2)

        # making the first image the default again will update image_url
        self.app.put(localurl(image_url1), {'is_default': True})
        scan = self.app.get(scan_url)
        self.assertEqual(get_identifying_url(scan.json['image_url']), image_url1)

        # dleete image1, and check if it is logged ok
        self.app.delete(localurl(image_url1), params={'user': 'someuser2'})

        # if we delete an image, the other one becomes default
        scan = self.app.get(scan_url)
        self.assertEqual(get_identifying_url(scan.json['image_url']), image_url2)

        # now if we add a new image, we expect to get a new url as well
        self.app.post(scan_url + '/images', image_data, upload_files=upload_files)
        response = self.app.get(scan_url + '/images')
        image_urls = [x['URL'] for x in response.json['results']]
        self.assertFalse(image_url1 in image_urls)

    def test_images_collection_item_put(self):
        scan = self._add_one_scan_with_two_images()

        img1_url = localurl(scan['images'][0]['URL'])
        upload_files = [('file', 'img3', TEST_IMAGE_PNG)]
        self.app.put(img1_url, upload_files=upload_files)

        # now we should find the new image on this URL
        response = self.app.get(img1_url)
        self.assertEqual(response.json['filename'], 'img3')
        # also, the last modified date of the scan should have changed
        new_scan = self.app.get(scan['URL']).json
        self.assertTrue(scan['dateLastModified'] <= new_scan['dateLastModified'], '%s should be earlier than %s' % (scan['dateLastModified'], new_scan['dateLastModified']))

    def test_images_collection_thumbnail_is_erased_on_update(self):
        "After updating a scan all its thumbnails are recalculated"
        scan = self._add_one_scan_with_two_images()
        img1_url = localurl(scan['images'][0]['URL'])

        # add the first file
        upload_files = [('file', 'img3', TEST_IMAGE_PNG)]
        self.app.put(img1_url, upload_files=upload_files)
        first_thumbnail = self.app.get(img1_url + '/file?size=100x').body
        upload_files = [('file', 'img3', TEST_IMAGE_ZACKTHECAT)]

        self.app.put(img1_url, upload_files=upload_files)
        second_thumbnail = self.app.get(img1_url + '/file?size=100x').body
        self.assertTrue(first_thumbnail != second_thumbnail)

    def test_images_collection_set_default_image(self):
        scan = self._add_one_scan_with_two_images()

        img1_url = localurl(scan['images'][0]['URL'])
        img2_url = localurl(scan['images'][1]['URL'])

        response = self.app.get(img1_url)
        self.assertEqual(response.json['is_default'], True)
        response = self.app.get(img2_url)
        self.assertEqual(response.json['is_default'], False)

        self.app.put(img2_url, {'is_default': True})

        response = self.app.get(img1_url)
        self.assertEqual(response.json['is_default'], False)
        response = self.app.get(img2_url)
        self.assertEqual(response.json['is_default'], True)

        # now if we delete the default image, we want to other image to becausem the default image
        self.app.delete(img2_url)
        response = self.app.get(img1_url)
        self.assertEqual(response.json['is_default'], True)

    def test_images_collection_item_raw_file(self):
        scan = self._add_one_scan_with_two_images()
        img1_url = localurl(scan['images'][0]['URL'])
        response = self.app.get(os.path.join(img1_url, 'file'))
        self.assertEqual(response.status_code, 200)
        result1 = response.body
        response = self.app.get(os.path.join(img1_url, 'filearbitrary_hash_value'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, result1)

    def test_file_url(self):
        scan_data = self._add_one_scan_with_two_images()
        images_collection_data = self.app.get(localurl(os.path.join(scan_data['URL'], 'images'))).json
        image1_url = localurl(scan_data['images'][0]['URL'])
        image1_data = self.app.get(localurl(image1_url)).json
        self.assertEqual(scan_data['image_url'], images_collection_data['results'][0]['image_url'])
        self.assertEqual(scan_data['image_url'], image1_data['image_url'])


class TestScanObject(BaseRepoTest):
    TEST_IMAGE = TEST_IMAGE_PNG

    def setUp(self):
        super(TestScanObject, self).setUp()
        self.scan = Scan()
        self.scan.number = 1
        self.scan.archiveFile = 'one'
        self.scan.archive_id = 1
        image = ScanImage(filename="foobar", id=1)
        self.scan.images.append(image)
        self.scan.store_file(self.TEST_IMAGE, image.id)
        self.imageid = self.scan.images[0].id

    def test_scan_store_file(self):
        path = self.scan.get_real_path(self.imageid)
        with open(path) as fh:
            self.assertEqual(fh.read(), self.TEST_IMAGE,
                "Stored image is not the same as the one provided")

    def test_scan_thumbnail(self):
        self.scan.store_file(TEST_IMAGE_ZACKTHECAT, self.imageid)
        path = self.scan.get_real_thumbnail_path('100x', self.imageid)
        with open(path) as fh:
            img = Image.open(fh)
        self.assertEqual(img.size, (100, 91))

    def test_scan_thumbnail_validation(self):
        with self.assertRaises(ValueError):
            self.scan.get_real_thumbnail_path('100xa', self.imageid)
        with self.assertRaises(ValueError):
            self.scan.get_real_thumbnail_path('x', self.imageid)
        with self.assertRaises(ValueError):
            self.scan.get_real_thumbnail_path('xd20', self.imageid)
        with self.assertRaises(ValueError):
            self.scan.get_real_thumbnail_path('ax20', self.imageid)
        with self.assertRaises(ValueError):
            self.scan.get_real_thumbnail_path('xaa', self.imageid)
