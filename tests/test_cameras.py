# pylint:disable=C0114,C0115,C0116,C0413,E0401
# standard library
import os
import sys
from unittest import mock, TestCase
# add path so that imports work in tests the same way as in handler.py
sys.path.append(os.path.abspath('src'))
# project
import cameras
# testing
from tests import examples


class TestBaseCamera(TestCase):
    """
    Not much to test here, skip that in the sake of time.
    """


class TestRidgetecCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.RidgetecCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_parse_metadata(self):
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertEqual(camera.get_additional_metadata(), {
            'filename': 'an_image.jpg',
            'img_url': 'https://web.org/images/XWka0ylxSDAldA5WSAHrWeVtZpRHX5FBlLGA',
            'imei': '0815', 'date_time_created': '2020-01-01',
            'account_id': 'someone'})

    def test_format_exifdata(self):
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertEqual(
            camera.prep_new_tags(existing_exif=None), {
            'Make': 'RidgeTec', 'SerialNumber': '0815',
            'DateTimeOriginal': '2020:01:01',
            'UserComment': 'AccountId=someone'})

    @mock.patch('helpers.download_image')
    def test_get_images(self, download_image):
        download_image.return_value = '/tmp_path/an_image.jpg'
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        images = camera.get_images()
        self.assertEqual(list(images), ['/tmp_path/an_image.jpg'])
        download_image.assert_called_once()
        download_image.assert_called_with(
            'an_image.jpg',
            'https://web.org/images/XWka0ylxSDAldA5WSAHrWeVtZpRHX5FBlLGA')


class TestCuddebackCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.CuddebackCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_get_cam_id(self):
        camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
        exif = [{'EXIF:UserComment': 'ID=B,OTHER=X'}]
        self.assertEqual(
            camera.prep_new_tags(existing_exif=exif), {'SerialNumber': 'B'})

    # # TODO: figure out how to make save_attached_images return a predictable temp path
    # @mock.patch('helpers.save_attached_images')
    # def test_get_images(self, save_attached_images):
    #     save_attached_images.return_value = {} # TODO: dict to expect as return value
    #     camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
    #     images = camera.get_images()
    #     self.assertEqual(list(images), ['/tmp_path/an_image.jpg']) # TODO: list of dicts as specidied above


class TestSwiftCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.SwiftCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_parse_metadata(self):
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL)
        self.assertEqual(camera.get_additional_metadata(), {
            'camera_id': 'TEST CAM',
            'date_time_created': '2026:07:10 11:15:46',
            'imei': '8680200354319711'})

    def test_format_exifdata_no_existing(self):
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL)
        self.assertEqual(
            camera.prep_new_tags(existing_exif=None), {
                'Make': 'Swift',
                'SerialNumber': '8680200354319711',
                'DateTimeOriginal': '2026:07:10 11:15:46',
                'UserComment': 'CameraId=TEST CAM'})

    def test_format_exifdata_with_existing(self):
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL)
        existing_exif = [{
            'EXIF:Make': 'SIMCOM',
            'EXIF:DateTimeOriginal': '2026:07:10 12:32:44'}]
        # Make always overwrites; DateTimeOriginal is preserved because the
        # image already has one.
        self.assertEqual(
            camera.prep_new_tags(existing_exif=existing_exif), {
                'Make': 'Swift',
                'SerialNumber': '8680200354319711',
                'UserComment': 'CameraId=TEST CAM'})

    def test_parse_metadata_real_eml(self):
        """
        Exercise the real-world multipart/mixed structure and the base64
        MIME-encoded subject line from a production Swift email.
        """
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL_REAL)
        self.assertTrue(camera.evaluate_make())
        self.assertEqual(camera.get_additional_metadata(), {
            'camera_id': 'TEST CAM',
            'date_time_created': '2026:07:10 12:32:44',
            'serial_number': 'SYPR0799'})

    @mock.patch('helpers.save_attached_images')
    def test_get_images(self, save_attached_images):
        save_attached_images.return_value = ['/tmp_path/an_image.jpg']
        camera = cameras.SwiftCamera(examples.SWIFT_EMAIL)
        images = camera.get_images()
        self.assertEqual(list(images), ['/tmp_path/an_image.jpg'])
        save_attached_images.assert_called_once_with(examples.SWIFT_EMAIL)


class TestUOVisionCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.UOVisionCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_parse_metadata(self):
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        self.assertEqual(camera.get_additional_metadata(), {
            'img_url': (
                'https://msp-thumbnail.oss-eu-central-1.aliyuncs.com'
                '/35318_59471_20260720_080813575.jpg'),
            'filename': '35318_59471_20260720_080813575.jpg',
            'date_time_created': '2026:07:20 12:07:42',
            'camera_name': 'TILLY'})

    def test_format_exifdata_no_existing(self):
        # camera_name is always used as SerialNumber
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        self.assertEqual(
            camera.prep_new_tags(existing_exif=None), {
                'Make': 'UOVision',
                'SerialNumber': 'TILLY',
                'DateTimeOriginal': '2026:07:20 12:07:42',
                'UserComment': 'CameraName=TILLY'})

    def test_format_exifdata_existing_serial_preserved(self):
        # SerialNumber already in image EXIF — do not overwrite
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        existing_exif = [{'EXIF:SerialNumber': 'TILLY'}]
        result = camera.prep_new_tags(existing_exif=existing_exif)
        self.assertNotIn('SerialNumber', result)

    def test_format_exifdata_existing_datetime_preserved(self):
        # DateTimeOriginal already in image EXIF — do not overwrite
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        existing_exif = [{'EXIF:DateTimeOriginal': '2026:07:20 08:08:13'}]
        result = camera.prep_new_tags(existing_exif=existing_exif)
        self.assertNotIn('DateTimeOriginal', result)

    @mock.patch('helpers.download_image')
    def test_get_images(self, download_image):
        download_image.return_value = '/tmp/35318_59471_20260720_080813575.jpg'
        camera = cameras.UOVisionCamera(examples.UOVISION_EMAIL)
        images = camera.get_images()
        self.assertEqual(
            list(images), ['/tmp/35318_59471_20260720_080813575.jpg'])
        download_image.assert_called_once_with(
            '35318_59471_20260720_080813575.jpg',
            'https://msp-thumbnail.oss-eu-central-1.aliyuncs.com'
            '/35318_59471_20260720_080813575.jpg')


