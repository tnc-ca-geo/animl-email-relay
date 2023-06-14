# pylint:disable=C0114,E0401
# standard library
from email.message import EmailMessage
import io
import os
import tempfile
# third party
from PIL import Image


EVENT= {'Records': [{
    's3': {
        'bucket': {'name': 'a_bucket'}, 'object': {'key': 'a_key'}}}]}
RIDGETEC_EMAIL_BODY = (
    '<html><body>'
    '    <img src="https://web.org/images/an_image.jpg"></img>'
    '    <whatever data-date-time-created="2020-01-01"></whatever>'
    '    <whatever data-timezone="US/Los Angeles"></whatever>'
    '    <whatever data-imei="0815"></whatever>'
    '    <whatever data-account-id="someone"></whatever>'
    '</body></html>'
)
RIDGETEC_EMAIL = EmailMessage()
RIDGETEC_EMAIL['From'] ='An email from ridgetec'
RIDGETEC_EMAIL['Body'] = RIDGETEC_EMAIL_BODY
CUDDEBACK_EMAIL = EmailMessage()
CUDDEBACK_EMAIL['From'] = 'An email from cuddelink'
OTHER_EMAIL = EmailMessage()
OTHER_EMAIL['From'] = 'Another message'


def create_chunked_image_response():
    """
    Create a chunked response body to mock request.response.iter_content.

    Returns:
        list(bytes)
    """
    image = Image.new('RGB', (100, 100), (0, 55, 0))
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='JPEG')
    bytes_arr = image_bytes.getvalue()
    # mocking the chunked response
    return [
        bytes_arr[i:i+1024] for i in range(0, len(bytes_arr), 1024)]


def create_test_image():
    """
    Helper function creating a temporary image file and returning the path.
    """
    image = Image.new('RGB', (2, 2), (0, 0, 0))
    tmp_directory = tempfile.mkdtemp()
    file_name = os.path.join(tmp_directory, 'test_image.jpg')
    with open(file_name, 'wb') as file_handle:
        image.save(file_handle, 'JPEG')
    return file_handle.name
