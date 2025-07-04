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
            'an_image.jpg', 'https://web.org/images/an_image.jpg')


class TestCuddebackCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.CuddebackCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_get_cam_id(self):
        camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
        # TODO: get exif
        exif = camera.get_exif()
        self.assertEqual(
            camera.prep_new_tags(existing_exif=exif), {'SerialNumber': 'B'})

    # # TODO: figure out how to make save_attached_images return a predictable temp path
    # @mock.patch('helpers.save_attached_images')
    # def test_get_images(self, save_attached_images):
    #     save_attached_images.return_value = {} # TODO: dict to expect as return value
    #     camera = cameras.CuddebackCamera(examples.CUDDEBACK_EMAIL)
    #     images = camera.get_images()
    #     self.assertEqual(list(images), ['/tmp_path/an_image.jpg']) # TODO: list of dicts as specidied above


