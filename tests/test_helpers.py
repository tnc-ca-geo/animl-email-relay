# pylint:disable=C0103,C0114,C0115,C0116,C0413,E0401
# standard library
import codecs
import email
import io
import os
import sys
from unittest import mock, TestCase
# third party
from exiftool import ExifToolHelper
from PIL import Image
# add path so that imports work in tests the same way as in handler.py
sys.path.append(os.path.abspath('src'))
# this prevents boto3 from being imported in the test
sys.modules['boto3'] = mock.MagicMock()
# module to test
import helpers
# testing
from tests import examples


EMAIL_QUOPRI_BODY = (
    b'From: Sch=C3=BCtzenmeister\nTo: Someone\nSubject: Important\n'
    b'Content-Type: text/plain; charset=UTF-8\n'
    b'\nbla bla')


class TestGetEmailFromS3(TestCase):

    @mock.patch('helpers.s3')
    def test_get_email_from_s3(self, s3):
        # setup
        s3.get_object.return_value = {'Body': io.BytesIO(EMAIL_QUOPRI_BODY)}
        # call module to test
        eml = helpers.get_email_from_s3('bucket', 'an_email')
        # assertions
        s3.get_object.assert_called_with(Bucket='bucket', Key='an_email')
        self.assertEqual(eml.get('from'), 'Schützenmeister')
        self.assertEqual(eml.get('to'), 'Someone')
        self.assertEqual(eml.get('subject'), 'Important')
        self.assertEqual(eml.get_content(), 'bla bla')


class TestEnrichExif(TestCase):

    def setUp(self):
        self.test_image_path = examples.create_test_image()

    def tearDown(self):
        os.remove(self.test_image_path)

    def test_enrich_exif(self):
        helpers.enrich_exif(self.test_image_path, {'Make': 'Frankenstein'})
        with ExifToolHelper() as exiftool:
            metadata = exiftool.get_metadata(self.test_image_path)
        self.assertEqual(metadata[0]['EXIF:Make'], 'Frankenstein')

    # add some tests for Exception behavior and error handling, TODO: unit
    # structure needs to be more suitable for exception testing.


@mock.patch('helpers.requests')
class TestDownloadImage(TestCase):

    def test_download_image(self, requests):
        # creating test data and mock requests
        image = Image.new('RGB', (1000, 1000), (0, 55, 0))
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='JPEG')
        bytes_arr = image_bytes.getvalue()
        # mocking the chunked response
        requests.get.return_value.iter_content.return_value = [
            bytes_arr[i:i+1024] for i in range(0, len(bytes_arr), 1024)]
        requests.get.return_value.ok = True
        # call the function
        res = helpers.download_image(
            'a_file.jpg', 'https://nowhere.org/image')
        # assertions
        requests.get.assert_called_with(
            'https://nowhere.org/image', stream=True)
        self.assertEqual(res[-10:], 'a_file.jpg')
        # check whether valid image, Image.verify() mighyt be sufficient here
        with Image.open(res) as image:
            image.verify()
            self.assertEqual(image.format, 'JPEG')

    def test_download_img_not_ok(self, requests):
        requests.get.return_value.ok = False
        with self.assertRaises(helpers.ImageDownloadError):
            helpers.download_image('a_file.jpg', 'https://nowhere.org/image')


class TestSaveAttachedImages(TestCase):

    def test_save_attached_images(self):
        with open('tests/example_cuddelink.eml', 'rb') as message_bytes:
            eml = codecs.decode(message_bytes.read(), 'quopri')
            msg = email.message_from_bytes(eml, policy=email.policy.default)
        res = helpers.save_attached_images(msg)
        self.assertEqual(len(res), 1)
        Image.open(res[0]).verify()


class TestGetExif(TestCase):

    def test_get_exif(self):
        image = examples.create_test_image()
        res = helpers.get_exif(image)
        print(res)
