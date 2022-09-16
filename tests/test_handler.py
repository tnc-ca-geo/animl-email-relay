"""
Tests for src/handler.py
"""
# standard library
import io
from unittest import mock, TestCase
# third party
import boto3
# module to test
from src import handler


# just stuff I am testing below
class UselessException(Exception):
    pass

# this is just an example to test, it would fail in real life since the bucket
# does not exist, but mocking is the point here
def get_s3_object():
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket='not_reachable', Key='foo')
    return response.get('Body').read()


def i_will_raise_an_exception():
    raise UselessException('I am a failure')
# ----------------------------------------------

# Testcase class need to have the word Test in them
class ExampleTestCase(TestCase):

    def __setUp__(self):
        # run some code before all the test methods in that class
        pass

    def __tearDown__(self):
        # run some code to clean up after all test methods in the class
        pass

    # test methods have to have the word test in them to be picked up by the
    # test runner
    def test_example(self):
        test_data = 1.1
        expected = 1
        # see here for all assertion methods in the unitest module
        # https://docs.python.org/3/library/unittest.html
        self.assertEqual(int(test_data), expected)


class ExampleMockTestCase(TestCase):

    @mock.patch('boto3.client')
    def test_s3(self, client):
        # This initializes a mocked class, that will not call out to s3
        s3 = client.return_value
        # This mocks a method on that class
        # remove all attribute that are not required in your test
        s3.get_object.return_value = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': {}
            },
            'Metadata': {},
            # io.Bytes creates a stream object with a .read() method
            # if your really need an image you can use pillow to create one
            'Body': io.BytesIO(b'some binary data')
        }
        self.assertEqual(get_s3_object(), b'some binary data')
        s3.get_object.assert_called_with(Bucket='not_reachable', Key='foo')


class ExampleExceptionTestCase(TestCase):

    def test_fail(self):
        with self.assertRaises(UselessException):
            i_will_raise_an_exception()
