"""
This module contains generic helper functions with storage and cloud side
effects. Please use to build camera specific classes in makes.py.
"""
# standard library
import codecs
import email
import email.policy
import os
import quopri
import tempfile
import uuid
# third party
from exiftool import ExifToolHelper
from exiftool.exceptions import ExifToolExecuteError
import boto3
import requests


# It is best practice to initialize the AWS clients on load since it will stay
# initialized while the lambda function is "warm". Makes testing a bit more
# challenging.
s3 = boto3.client('s3')


class ImageDownloadError(Exception):
    """
    Subclass Exception for more specific error handling and testing.
    """


def get_email_from_s3(bucket, key):
    """
    Retrieve an email that has been dumped in an S3 bucket by SES. Key is part
    of the payload of the event that triggers the Lambda function.

    Args:
        bucket(str): A S3 bucket
        key(str): A S3 object key pointing to the message
    Returns:
        dict
    """
    # TODO: add error handling
    s3_object = s3.get_object(Bucket=bucket, Key=key)
    email_data = s3_object['Body'].read()
    email_data = codecs.decode(email_data, 'quopri')
    return email.message_from_bytes(email_data, policy=email.policy.default)


def get_exif(image):
    with ExifToolHelper() as exif_tool:
        try:
            return exif_tool.get_metadata(image)
        except ExifToolExecuteError as err:
            print(f'ExifToolExecutionError: {err}')
            return []


def enrich_exif(img_path, new_tags):
    print(f'setting new_tags on {img_path}: {new_tags}...')
    with ExifToolHelper() as exif_tool:
        try:
            exif_tool.set_tags(
                img_path, tags=new_tags,
                params=['-P', '-overwrite_original_in_place'])
        except (ValueError, TypeError, ExifToolExecuteError) as err:
            print(f'{err.__class__.__name__}: {err}')
        except:
            print('An error occured setting tags')


def download_image(filename, img_url):
    """
    Download an image and return temporary path.

    Args:
        filename(str): A file name to store the image under.
        img_url(str): The source URL
        tmp_directory(str): The directory for temporary files
    Returns:
        str
    """
    print(f'Downloading {filename}.')
    tmp_directory = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_directory, filename)
    with open(tmp_path, 'wb') as handle:
        response = requests.get(img_url, stream=True)
        if not response.ok:
            raise ImageDownloadError(f'Error downloading image: {response}')
        for block in response.iter_content(1024):
            if not block:
                break
            handle.write(block)
    return tmp_path


def save_attached_images(email_msg):
    """
    Extract attached images and store in temporary files.

    Args:
        email_msg(email.EmailMessage)
    Returns:
        dict
    """
    img_attachments = []
    tmp_directory = tempfile.mkdtemp()
    for part in email_msg.iter_attachments():
        filename = os.path.join(tmp_directory, part.get_filename())
        with open(filename, 'wb') as handle:
            handle.write(part.get_content())
            img_attachments.append(filename)
    if len(img_attachments) == 0:
        print('No image files found.')
    return img_attachments