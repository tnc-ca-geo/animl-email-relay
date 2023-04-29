#!/opt/bin/perl

import os
import mimetypes
import tempfile
from re import L
import uuid
from urllib.parse import unquote_plus
from urllib.parse import urlparse
import email
from email import policy
from html.parser import HTMLParser
import codecs
import requests
import boto3
from exiftool import ExifToolHelper
from exiftool.exceptions import ExifToolExecuteError
from lambda_cache import ssm


LAMBDA_TASK_ROOT = os.environ["LAMBDA_TASK_ROOT"]
EXIFTOOL_PATH = f"{LAMBDA_TASK_ROOT}/exiftool"
SSM_NAMES = {
    "INGESTION_BUCKET": f"/images/ingestion-bucket-{os.environ['STAGE']}",
}
SUPPORTED_MAKES = ['RidgeTec', 'CUDDEBACK']


s3 = boto3.client("s3")
os.environ["PATH"] = "{}:{}/".format(os.environ["PATH"], EXIFTOOL_PATH)


class ParseRidgeTec(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.img_url = None
        self.filename = "UNKNOWN_FILENAME.JPG"
        self.date_time_created = None
        self.timezone = None
        self.imei = None
        self.account_id = None

    def handle_starttag(self, tag, attrs):
        for attr in attrs:
            if attr[0] == "src":
                self.img_url = attr[1]
                url_parts = urlparse(attr[1])
                self.filename = url_parts.path.split('/')[2]
            elif attr[0] == "data-date-time-created":
                self.date_time_created = attr[1]
            elif attr[0] == "data-timezone":
                self.timezone = attr[1]       
            elif attr[0] == "data-imei":
                self.imei = str(attr[1])
            elif attr[0] == "data-account-id":
                self.account_id = str(attr[1])

def enrich_exif(img_path, new_tags):
    print(f"setting mew_tags on {img_path}: {new_tags}...")
    with ExifToolHelper() as et:
        try:
            et.set_tags(
                img_path,
                tags=new_tags,
                params=["-P", "-overwrite_original_in_place"]
            )
        except ValueError as err:
            print(f"ValueError: {err}")
        except TypeError as err:
            print(f"TypeError: {err}")
        except ExifToolExecuteError as err:
            print(f"ExifToolExecutionError: {err}")
        except:
            print("An error occured setting tags")

def download_img(filename, img_url):
    print(f"downloading {filename}")
    tmp_path = f"/tmp/{uuid.uuid4()}_{filename}"
    with open(tmp_path, 'wb') as handle:
        response = requests.get(img_url, stream=True)
        if not response.ok:
            raise Exception(f"Error downloading image: {response}") 
        for block in response.iter_content(1024):
            if not block:
                break
            handle.write(block)
    return tmp_path

def get_make(email):
    make = 'other'
    sender = email.get("From")
    if ('ridgetec' in sender):
        make = 'RidgeTec'
    if ('cuddelink' in sender):
        make = 'CUDDEBACK'
    print(f"make: {make}")
    return make

def get_email(bucket, key):
    email_data = s3.get_object(Bucket=bucket, Key=key)
    email_data = email_data["Body"].read()
    email_data = codecs.decode(email_data, "quopri")
    email_parsed = email.message_from_bytes(email_data, policy=policy.default)
    # TODO: headers still appear to be in quoted-printable encoding! fix!
    # https://stackoverflow.com/questions/63110730/strange-formatting-of-html-in-ses-mail
    # print("email parsed from bytes and printed as string: ")
    # print(email_parsed.as_string())
    # print(f"keys: {email_parsed.keys()}")
    return email_parsed

def get_cuddeback_cam_id(file_path):
    with ExifToolHelper() as et:
        try: 
            cam_id = None
            user_comment = et.get_tags(file_path, ['UserComment'])
            print(f'user_comment: {user_comment}')
            user_comments = user_comment[0]['EXIF:UserComment'].split(',')
            for comment in user_comments:
                key, value = comment.split('=')
                # print(f'key: {key} - value: {value}')
                if key == 'ID': cam_id = value
        except ExifToolExecuteError as err:
            print(f"ExifToolExecutionError: {err}")
        return cam_id

def save_attached_images(email_msg):
    # find attached JPGs
    img_attachments = {}
    for part in email_msg.iter_attachments():
        fn = part.get_filename()
        if fn:
            ext = os.path.splitext(part.get_filename())[1]
        else:
            ext = mimetypes.guess_extension(part.get_content_type())
        if ext.casefold() == '.JPG'.casefold():
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                f.write(part.get_content())
                img_attachments[f.name] = fn
    if len(img_attachments) == 0:
        print('no image files found')
    return img_attachments

def get_config(context, ssm_names=SSM_NAMES):
    ret = {}
    for key, value in ssm_names.items():
        try:
            param_name = value.split("/")[-1]
            ret[key] = getattr(context,"config").get(param_name)
            if ret[key] is None:
                raise ValueError(value)
        except ValueError as err:
            print("SSM name '{}' was not found".format(err))
        except:
            print("An error occured fetching remote config")
    return ret

@ssm.cache(
  parameter=[value for _, value in SSM_NAMES.items()],
  entry_name="config",
  max_age_in_seconds=300
)
def handler(event, context):
    print("event: {}".format(event))
    config = get_config(context)
    for record in event["Records"]:

        email_bucket = record["s3"]["bucket"]["name"]
        email_key = unquote_plus(record["s3"]["object"]["key"])
        print(f"new file detected in {email_bucket}: {email_bucket}")

        # get email from S3, decode, and parse
        msg = get_email(email_bucket, email_key)

        # determine make
        make = get_make(msg)
        if make not in SUPPORTED_MAKES:
            raise ValueError(f"unsupported camera make: {make}")

        elif make == 'RidgeTec':
            # extract data attributes
            rt = ParseRidgeTec()
            rt.feed(msg.as_string())

            # download image to /tmp
            img_path = download_img(rt.filename, rt.img_url)

            # write data attributes to image's exif
            new_tags = {
              "Make": "RidgeTec",
              "SerialNumber": rt.imei,
              "DateTimeOriginal": rt.date_time_created.replace("-", ":"),
              "UserComment": f"AccountId={rt.account_id}"
            }
            enrich_exif(img_path, new_tags)

            # transfer image to ingestion bucket
            print(f"uploading {rt.filename} to {config['INGESTION_BUCKET']}")
            s3.upload_file(img_path, config["INGESTION_BUCKET"], rt.filename)
            os.remove(img_path)

        elif make == 'CUDDEBACK':
            img_attachments = save_attached_images(msg)
            for img_path, fn in img_attachments.items():
                # get camera ID
                cam_id = get_cuddeback_cam_id(img_path)
                print(f"CUDDEBACK cam_id: {cam_id}")
                # write camera ID to EXIF SerialNumber
                if cam_id is not None:
                    enrich_exif(img_path, {"SerialNumber": cam_id})
                # upload to S3
                print(f"uploading {fn} to {config['INGESTION_BUCKET']}")
                s3.upload_file(img_path, config["INGESTION_BUCKET"], fn)
                os.remove(img_path)