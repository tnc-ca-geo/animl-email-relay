# pylint:disable=E0401,C0115,C0116,C0413,R1732,W0613
"""
Tests for src/handler.py. Even though unit tests should generally not depend on
a specific environment, we are relying here on exiftools being installed. I
think that is sensitive since this module heavily relies on it.
"""
# standard library
import codecs
import email
from functools import wraps
import os
import sys
from types import SimpleNamespace
from unittest import mock, TestCase
# add path so that imports work in tests the same way as in handler.py
sys.path.append(os.path.abspath('src'))
sys.modules['boto3'] = mock.MagicMock()
# this is a huge disadvantage of using third party decorators with side effects
# they need to be patched away for the tests to work. The below mock_decorator
# just does nothing. Alternatively we could also return the desired context.
# see https://dev.to/stack-labs/how-to-mock-a-decorator-in-python-55jc
def mock_decorator(*args, **kwargs):
    """
    Decorate by doing nothing.
    """
    def decorator(function):
        @wraps(function)
        def decorated_function(*args, **kwargs):
            return function(*args, **kwargs)
        return decorated_function
    return decorator
# patch decorators
mock.patch('lambda_cache.ssm.cache', mock_decorator).start()
# testdata
from tests import examples
# module to test
import handler


@mock.patch('handler.STAGE', new='test')
@mock.patch('helpers.get_email_from_s3')
@mock.patch('helpers.requests')
@mock.patch('handler.s3.upload_file')
class TestFullHandler(TestCase):

    def test_handler_ridgetec(self, upload_file, download_img, get_email):
        fake_message = email.message.EmailMessage()
        fake_message['From'] = 'A message from ridgetec'
        fake_message['Body'] = examples.RIDGETEC_EMAIL_BODY
        get_email.return_value = fake_message
        context = SimpleNamespace(
            config={'ingestion-bucket-': 's3://test_bucket'})
        handler.handler(examples.EVENT, context)
        upload_file.assert_called_with(
            mock.ANY, 's3://test_bucket', 'an_image.jpg')

    def test_handler_unsupported(self, upload_file, download_img, get_email):
        fake_message = email.message.EmailMessage()
        fake_message['From'] = 'Nothing here'
        get_email.return_value = fake_message
        with self.assertRaises(NotImplementedError):
            handler.handler(examples.EVENT, SimpleNamespace())

    def test_handler_cuddeback_real_data(
                self, upload_file, download_img, get_email
        ):
        with open('tests/example_cuddelink.eml', 'rb') as message_bytes:
            eml = codecs.decode(message_bytes.read(), 'quopri')
            get_email.return_value = email.message_from_bytes(
                eml, policy=email.policy.default)
        context = SimpleNamespace(
            config={'ingestion-bucket-': 's3://test_bucket'})
        handler.handler(examples.EVENT, context)
        upload_file.assert_called_with(
            mock.ANY, 's3://test_bucket', 'T_00001.JPG')
        # path = upload_file.call_args.args[0]
        # add additional assertions?


class TestFullHandlerRealDataWithDownload(TestCase):

    @mock.patch('handler.STAGE', new='test')
    @mock.patch('helpers.get_email_from_s3')
    @mock.patch('helpers.requests')
    @mock.patch('handler.s3.upload_file')
    def test_handler_ridgetec_real_data(self, upload_file, requests, get_email):
        # mocking the chunked response
        requests.get.return_value.iter_content.return_value = (
            examples.create_chunked_image_response())
        requests.get.return_value.ok = True
        with open('tests/example_ridgetec.eml', 'rb') as message_bytes:
            eml = codecs.decode(message_bytes.read(), 'quopri')
            get_email.return_value = email.message_from_bytes(
                eml, policy=email.policy.default)
        context = SimpleNamespace(
            config={'ingestion-bucket-': 's3://test_bucket'})
        handler.handler(examples.EVENT, context)
        upload_file.assert_called_with(
           mock.ANY, 's3://test_bucket', '53852545.JPG')
        # finish this test by adding assertions
