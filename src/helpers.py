# pylint:disable=E0401,W0511,W0718
"""
This module contains generic helper functions with storage and cloud side
effects. Please use to build camera specific classes in makes.py.
"""
# standard library
import codecs
import email
import email.policy
import os
import tempfile
import mimetypes
# third party
from exiftool import ExifTool
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

def get_encoding(email_data):
    """
    Retrieve the email's content-transfer-encoding header (if present)
    Some emails we receive are quoted-printable encoded (e.g. RidgeTec);
    while others are not.
    """
    msg = email.message_from_bytes(email_data, policy=email.policy.default)
    return msg["Content-Transfer-Encoding"]


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
    encoding = get_encoding(email_data)
    if encoding == 'quoted-printable':
        print('quoted-printable encoding detected; decoding')
        email_data = codecs.decode(email_data, 'quopri')
    # TODO: also decode if entire email was encoded in base64?
    return email.message_from_bytes(email_data, policy=email.policy.default)


def get_exif(image_path):
    """
    Read Exif data from image file.

    Args:
        image_path(str): Path of an image file.
    Returns:
        list
    """
    with ExifToolHelper() as exiftool:
        try:
            return exiftool.get_metadata(image_path)
        except ExifToolExecuteError as err:
            print(f'ExifToolExecutionError: {err}')
            return []


def repair_exif(image_path):
    """
    Repair exif problems if they exist. Exiftool will not write to an image's
    exif if there are any existing issues with it, so it's important to fix
    them first.
    see: https://exiftool.org/faq.html#Q20
    """
    with ExifTool() as exif_tool:
        try:
            # This command deletes all metadata then copies all writable tags 
            # that can be extracted from the original image to the same 
            # locations in the updated image
            exif_tool.execute('-all=', '-tagsfromfile', '@', '-all:all', 
                              '-unsafe', '-icc_profile', image_path)
        except (ValueError, TypeError, ExifToolExecuteError) as err:
            print(f'{err.__class__.__name__}: {err}')
        except Exception as error:
            print('An error ocurred repairing exif:', error)


def enrich_exif(image_path, new_tags):
    """
    Enrich existing image file with additional data.

    Args:
        image_path(str): Path of an image file.
        new_tags(dict): A dictionary of tags and values.
    Returns:
        None
    """
    print(f'Setting new_tags on {image_path}: {new_tags}...')
    if not new_tags:
        return
    repair_exif(image_path)
    with ExifToolHelper() as exif_tool:
        try:
            exif_tool.set_tags(
                image_path, tags=new_tags,
                params=['-P', '-overwrite_original_in_place'])
        except (ValueError, TypeError, ExifToolExecuteError) as err:
            print(f'{err.__class__.__name__}: {err}')
        except Exception as error:
            print('An error ocurred setting tags:', error)


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
        print(f'Saving attached image to: {filename}')
        if filename:
            ext = os.path.splitext(filename)[1]
        else:
            ext = mimetypes.guess_extension(part.get_content_type())
        if ext.casefold() == '.JPG'.casefold() or ext.casefold() == '.jpeg':
            with open(filename, 'wb') as handle:
                handle.write(part.get_content())
                img_attachments.append(filename)
    if len(img_attachments) == 0:
        print('No image files found.')
    return img_attachments
