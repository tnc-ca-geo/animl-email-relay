"""
A Lambda function retrieving camera images and metadata from incoming
emails.
"""
# pylint:disable=E0401,W0718
# standard library
import os
from urllib.parse import unquote_plus
# third party
import boto3
from lambda_cache import ssm
# project
import cameras
import helpers


# Use .get so that test don't fail if environment is not set
LAMBDA_TASK_ROOT = os.environ.get('LAMBDA_TASK_ROOT', '')
EXIFTOOL_PATH = f'{LAMBDA_TASK_ROOT}/exiftool'
STAGE = os.environ.get('STAGE', '')
SSM_NAMES = {
    'INGESTION_BUCKET': f'/images/ingestion-bucket-{STAGE}',
    'DEAD_LETTER_BUCKET': f'/images/email-dead-letter-bucket-{STAGE}',
}


# register camera classes, BaseCamera must be the last in the list
SUPPORTED_CAMERAS = [
    cameras.RidgetecCamera, cameras.CuddebackCamera, cameras.SpartanCamera,
    cameras.SwiftCamera, cameras.UOVisionCamera, cameras.BaseCamera]


s3 = boto3.client('s3')
os.environ['PATH'] = f'{os.environ["PATH"]}:{EXIFTOOL_PATH}/'


def get_config(context, ssm_names=None):
    """
    Get configuration values from SSM.

    Args:
        context(object): AWS Lambda context
        ssm_names(dict): SSM lookup
    Returns:
        dict
    """
    # Do not pass dicts as default arguments since dict vars are pointers and
    # can change during execution.
    ssm_names = ssm_names if ssm_names else SSM_NAMES
    ret = {}
    for key, value in ssm_names.items():
        try:
            param_name = value.split('/')[-1]
            config = getattr(context, 'config')
            ret[key] = config.get(param_name)
            if ret[key] is None:
                raise ValueError(value)
        except ValueError as err:
            print(f'SSM name \'{err}\' was not found')
        except Exception:
            print('An error occured fetching remote config')
    return ret


@ssm.cache(
  parameter=[value for _, value in SSM_NAMES.items()], entry_name='config',
  max_age_in_seconds=300
)
def handler(event, context):
    """
    A Lambda handler that parses an email, gets the image data, enriches EXIF,
    and places enriched file in Animl ingestion bucket.

    Args Args:
        event(AWS lambda trigger event)
        context(AWS lambda context)
    Returns:
        None
    """
    config = get_config(context)
    dlq_bucket = config.get('DEAD_LETTER_BUCKET')
    for record in event['Records']:
        email_bucket = record['s3']['bucket']['name']
        email_key = unquote_plus(record['s3']['object']['key'])
        event_time = record.get('eventTime')
        print(f'New file detected in {email_bucket}/{email_key}.')
        msg = None
        reason = 'UNKNOWN_ERROR'
        try:
            msg = helpers.get_email_from_s3(email_bucket, email_key)
            # test whether email format is supported, if so proceed with the
            # initialize camera class
            camera = None
            for camera_class in SUPPORTED_CAMERAS:
                candidate = camera_class(msg)
                if candidate.evaluate_make():
                    camera = candidate
                    print(f'Camera make {camera.name} detected.')
                    break
            image_count = 0
            try:
                for image in camera.images():
                    image_count += 1
                    _, filename = os.path.split(image)
                    print(
                        f'Uploading {image} as {filename} '
                        f'to {config["INGESTION_BUCKET"]}.')
                    try:
                        s3.upload_file(
                            image, config['INGESTION_BUCKET'], filename)
                    except Exception:
                        reason = 'UPLOAD_ERROR'
                        raise
                    finally:
                        if os.path.exists(image):
                            os.remove(image)
            except NotImplementedError:
                reason = 'UNSUPPORTED_CAMERA'
                raise
            except helpers.ImageDownloadError:
                reason = 'IMAGE_FETCH_ERROR'
                raise
            except Exception:
                if reason == 'UNKNOWN_ERROR':
                    reason = 'IMAGE_FETCH_ERROR'
                raise
            if image_count == 0:
                reason = 'UNSUPPORTED_CAMERA'
                raise RuntimeError(
                    f'No images extracted from {email_bucket}/{email_key}')
        except Exception as err:
            print(
                f'Handler failure ({reason}) for '
                f'{email_bucket}/{email_key}: {err.__class__.__name__}: {err}')
            if not dlq_bucket:
                print(
                    'DEAD_LETTER_BUCKET is not configured; '
                    're-raising to fail the invocation.')
                raise
            helpers.move_to_dead_letter(
                s3, email_bucket, email_key, msg, reason,
                dlq_bucket, event_time_iso=event_time)
