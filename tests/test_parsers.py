# pylint:disable=C0114,C0115,C0116,C0413,E0401
# standard library
import os
import sys
from unittest import TestCase
# add path so that imports work in tests the same way as in handler.py
sys.path.append(os.path.abspath('src'))
# testing
from tests import examples
# project
import parsers


class TestRidgetecParser(TestCase):

    def test_parse_ridgetec(self):
        parser = parsers.RidgetecParser()
        parser.feed(examples.RIDGETEC_EMAIL_BODY)
        self.assertEqual(parser.filename, 'an_image.jpg')
        self.assertEqual(parser.date_time_created, '2020-01-01')
        self.assertEqual(parser.timezone, 'US/Los Angeles')
        self.assertEqual(parser.imei, '0815')
        self.assertEqual(parser.account_id, 'someone')


class TestSwiftParser(TestCase):

    def test_parse_swift(self):
        parser = parsers.SwiftParser()
        parser.feed(examples.SWIFT_EMAIL_BODY)
        self.assertEqual(parser.camera_id, 'TEST CAM')
        self.assertEqual(parser.date_time_created, '2026:07:10 11:15:46')

    def test_parse_swift_missing_fields(self):
        parser = parsers.SwiftParser()
        parser.feed('unrelated body content')
        self.assertIsNone(parser.camera_id)
        self.assertIsNone(parser.date_time_created)


class TestUOVisionParser(TestCase):

    def test_parse_uovision_html_body(self):
        p = parsers.UOVisionParser()
        p.feed(examples.UOVISION_EMAIL_BODY)
        self.assertEqual(
            p.img_url,
            'https://msp-thumbnail.oss-eu-central-1.aliyuncs.com'
            '/35318_59471_20260720_080813575.jpg')
        self.assertEqual(p.filename, '35318_59471_20260720_080813575.jpg')
        self.assertEqual(p.date_time_created, '2026:07:20 12:07:42')

    def test_parse_uovision_missing_fields(self):
        p = parsers.UOVisionParser()
        p.feed('<html><body>No image here</body></html>')
        self.assertIsNone(p.img_url)
        self.assertIsNone(p.date_time_created)
        self.assertEqual(p.filename, 'UNKNOWN_FILENAME.JPG')
