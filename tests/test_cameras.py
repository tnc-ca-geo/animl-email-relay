# standard library
import os
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory
from types import SimpleNamespace
from unittest import mock, TestCase
# add path so that imports work in tests the same way as in handler.py
sys.path.append(os.path.abspath('src'))
# project
import cameras
import parsers
# testing
from tests import examples


class TestRidgetecCamera(TestCase):

    def test_evaluate_make(self):
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertTrue(camera.evaluate_make())
        camera = cameras.RidgetecCamera(examples.OTHER_EMAIL)
        self.assertFalse(camera.evaluate_make())

    def test_parse_metadata(self):
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertEqual(camera.get_metadata(), {
            'filename': 'an_image.jpg',
            'img_url': 'https://web.org/images/an_image.jpg',
            'imei': '0815', 'date_time_created': '2020-01-01',
            'account_id': 'someone'})

    def test_format_exifdata(self):
        metadata = {
            'filename': 'an_image.jpg',
            'img_url': 'https://web.org/images/an_image.jpg',
            'imei': '0815', 'date_time_created': '2020-01-01',
            'account_id': 'someone'}
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        self.assertEqual(
            camera.format_and_merge_exif_data(extra_data=None), {
            'Make': 'RidgeTec', 'SerialNumber': '0815',
            'DateTimeOriginal': '2020:01:01',
            'UserComment': 'AccountId=someone'})

    @mock.patch('helpers.download_image')
    def test_get_images(self, download_image):
        download_image.return_value = '/tmp_path/an_image.jpg'
        metadata = {
            'filename': 'an_image.jpg',
            'img_url': 'https://web.org/images/an_image.jpg',
            'imei': '0815', 'date_time_created': '2020-01-01',
            'account_id': 'someone'}
        camera = cameras.RidgetecCamera(examples.RIDGETEC_EMAIL)
        images = camera.get_images()
        self.assertEqual(list(images), ['/tmp_path/an_image.jpg'])
        download_image.assert_called_once()
        download_image.assert_called_with(
            'an_image.jpg', 'https://web.org/images/an_image.jpg')