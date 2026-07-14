# pylint:disable=E0401,W0511,W0718
"""
This module contains generic helper functions with storage and cloud side
effects. Please use to build camera specific classes in makes.py.
"""
# standard library
import codecs
import email
import email.policy
import email.utils
import os
import re
import tempfile
import mimetypes
from datetime import timezone
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


_SANITIZE_RE = re.compile(r'[^a-z0-9]+')


def _sanitize(value):
    """
    Lowercase and collapse any run of non-alphanumeric chars to a single '_'.
    Trim leading/trailing underscores. Returns '' if input is falsy.
    """
    if not value:
        return ''
    return _SANITIZE_RE.sub('_', value.lower()).strip('_')


def build_dead_letter_key(msg, source_key, event_time_iso=None):
    """
    Build a flat DLQ key of the form:
        YYYY-MM-DDTHH-MM-SSZ_<sender>_<original-key-basename>

    - Timestamp prefers the email's Date header (converted to UTC); falls back
      to event_time_iso (S3 event 'eventTime'), then to '19700101T00-00-00Z'.
    - Sender is the address part of From, sanitized. Empty -> 'unknown-sender'.
    - Original-key basename is sanitized. '.eml' suffix stripped so caller can
      add variant-specific suffixes (e.g. '.raw.eml', '.decoded.eml').

    Args:
        msg: email.message.Message (may be None if parsing failed).
        source_key(str): S3 key of the source email object.
        event_time_iso(str|None): S3 event 'eventTime' as fallback timestamp.
    Returns:
        str
    """
    ts = None
    if msg is not None:
        date_hdr = msg.get('Date') if hasattr(msg, 'get') else None
        if date_hdr:
            try:
                parsed = email.utils.parsedate_to_datetime(date_hdr)
                if parsed is not None:
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    ts = parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                ts = None
    if ts is None and event_time_iso:
        try:
            iso = event_time_iso.replace('Z', '+00:00')
            from datetime import datetime
            parsed = datetime.fromisoformat(iso)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            ts = parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            ts = None
    ts_str = (
        ts.strftime('%Y-%m-%dT%H-%M-%SZ') if ts is not None
        else '19700101T00-00-00Z')

    sender = ''
    if msg is not None:
        from_hdr = msg.get('From') if hasattr(msg, 'get') else None
        if from_hdr:
            _, addr = email.utils.parseaddr(str(from_hdr))
            sender = _sanitize(addr)
    if not sender:
        sender = 'unknown-sender'

    basename = os.path.basename(source_key or '') or 'no-key'
    # strip trailing .eml (case insensitive) before sanitizing
    if basename.lower().endswith('.eml'):
        basename = basename[:-4]
    basename = _sanitize(basename) or 'no-key'

    return f'{ts_str}_{sender}_{basename}'


def move_to_dead_letter(
        s3_client, source_bucket, source_key, msg, reason,
        dlq_bucket, event_time_iso=None):
    """
    Copy the raw S3 object AND the decoded message to the DLQ bucket, then
    delete the source. Two DLQ objects are written per failure:
      - <base>.raw.eml     : server-side copy of the original S3 object
      - <base>.decoded.eml : msg.as_bytes() (skipped if msg is None)
    Source is deleted only after all writes succeed. Any write failure raises.

    Args:
        s3_client: boto3 S3 client.
        source_bucket(str): staging bucket the object currently lives in.
        source_key(str): key of the source object.
        msg: parsed email.message.Message, or None if parsing failed.
        reason(str): short failure category tag stored in object metadata.
        dlq_bucket(str): destination DLQ bucket name.
        event_time_iso(str|None): S3 event 'eventTime' for timestamp fallback.
    Returns:
        dict with 'raw_key' and (optionally) 'decoded_key'.
    """
    base = build_dead_letter_key(msg, source_key, event_time_iso)
    raw_key = f'{base}.raw.eml'
    decoded_key = f'{base}.decoded.eml'
    common_meta = {
        'failure-reason': reason,
        'original-bucket': source_bucket,
        'original-key': source_key,
    }

    raw_meta = dict(common_meta, variant='raw')
    if msg is None:
        raw_meta['decoded-write'] = 'skipped'
    s3_client.copy_object(
        Bucket=dlq_bucket,
        Key=raw_key,
        CopySource={'Bucket': source_bucket, 'Key': source_key},
        MetadataDirective='REPLACE',
        Metadata=raw_meta,
    )

    result = {'raw_key': raw_key}

    if msg is not None:
        s3_client.put_object(
            Bucket=dlq_bucket,
            Key=decoded_key,
            Body=msg.as_bytes(),
            ContentType='message/rfc822',
            Metadata=dict(common_meta, variant='decoded'),
        )
        result['decoded_key'] = decoded_key

    s3_client.delete_object(Bucket=source_bucket, Key=source_key)
    print(
        f'DEAD_LETTER_MOVE reason={reason} '
        f'src=s3://{source_bucket}/{source_key} '
        f'dlq=s3://{dlq_bucket}/{raw_key}')
    return result
