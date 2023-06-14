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
