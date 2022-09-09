#!/opt/bin/perl

import os
from re import L
import sys
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

s3 = boto3.client("s3")

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
    os.environ["PATH"] = "{}:{}/".format(os.environ["PATH"], EXIFTOOL_PATH)
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
            print(f"TyoeError: {err}")
        except ExifToolExecuteError as err:
            print(f"ExifToolExecutionError: {err}")
        except:
            print("An error occured setting tags")


def download_img(filename, img_url):
    print(f"Downloading {filename}")
    tmp_path = f"/tmp/{uuid.uuid4()}_{filename}"
    print(f"tmp_path: {tmp_path}")
    with open(tmp_path, 'wb') as handle:
        response = requests.get(img_url, stream=True)
        if not response.ok:
            print(response)
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
    print(f"make: {make}")
    return make

def getConfig(context, ssm_names=SSM_NAMES):
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
    config = getConfig(context)
    for record in event["Records"]:

        email_bucket = record["s3"]["bucket"]["name"]
        email_key = unquote_plus(record["s3"]["object"]["key"])
        print(f"New file detected in {email_bucket}: {email_bucket}")

        # get object from S3, decode, and parse
        email_data = s3.get_object(Bucket=email_bucket, Key=email_key)
        email_data = email_data["Body"].read()
        email_data = codecs.decode(email_data, "quopri")
        email_parsed = email.message_from_bytes(email_data, policy=policy.default)
        # TODO: headers still appear to be in quoted-printable encoding! fix!
        # https://stackoverflow.com/questions/63110730/strange-formatting-of-html-in-ses-mail
        # print("email parsed from bytes and printed as string: ")
        # print(email_parsed.as_string())
        print(f"keys: {email_parsed.keys()}")

        # determine make
        make = get_make(email_parsed)
        # TODO: if make is 'other', end gracefully

        # extract data attributes
        rt = ParseRidgeTec()
        rt.feed(email_parsed.as_string())
        print(f"img_url: {rt.img_url}")
        print(f"filename: {rt.filename}")
        print(f"date_time_created: {rt.date_time_created}")
        print(f"imei: {rt.imei}")
        print(f"account_id: {rt.account_id}")

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

        # TODO: transfer image to ingestion bucket
        print(f"uploading {rt.filename} to {config['INGESTION_BUCKET']}")
        s3.upload_file(img_path, config["INGESTION_BUCKET"], rt.filename)

        # TODO: delete img from /tmp?