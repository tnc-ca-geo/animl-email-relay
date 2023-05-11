"""
A Lambda function retrieving camera images and metadata from incoming
emails.
"""
#!/opt/bin/perl
# the above is odd; TODO: remove
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
SSM_NAMES = {'INGESTION_BUCKET': f'/images/ingestion-bucket-{STAGE}'}


# register camera classes, BaseCamera must be the last in the list
SUPPORTED_CAMERAS = [
    cameras.RidgetecCamera, cameras.CuddebackCamera, cameras.BaseCamera]


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
        context(AWS lamba context)
    Returns:
        None
    """
    config = get_config(context)
    for record in event['Records']:
        email_bucket = record['s3']['bucket']['name']
        email_key = unquote_plus(record['s3']['object']['key'])
        print(f'New file detected in {email_bucket}/{email_key}.')
        msg = helpers.get_email_from_s3(email_bucket, email_key)
        # test whether email format is supported, if so proceed with the
        # initialize camera class
        for camera_class in SUPPORTED_CAMERAS:
            camera = camera_class(msg)
            if camera.evaluate_make():
                break
        for image in camera.images():
            _, filename = os.path.split(image)
            print(
                f'Uploading {image} as {filename} '
                f'to {config["INGESTION_BUCKET"]}.')
            s3.upload_file(image, config['INGESTION_BUCKET'], filename)
            os.remove(image)
