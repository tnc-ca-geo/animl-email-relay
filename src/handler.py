#!/opt/bin/perl

import os
from re import L
import sys
# import uuid
from urllib.parse import unquote_plus
import email
from email import policy
from html.parser import HTMLParser
import codecs
# from email.parser import BytesParser
# from PIL import Image, ImageFile
# ImageFile.LOAD_TRUNCATED_IMAGES = True
import boto3
from exiftool import ExifTool

LAMBDA_TASK_ROOT = os.environ["LAMBDA_TASK_ROOT"]
EXIFTOOL_PATH = f"{LAMBDA_TASK_ROOT}/exiftool"

s3 = boto3.client("s3")

# def copy_to_dlb(errors, md, config):
#     dl_bkt = config["DEADLETTER_BUCKET"]
#     copy_source = { "Bucket": md["Bucket"], "Key": md["Key"] }
#     dest_dir = "UNKNOWN_ERROR"
#     for error in errors:
#         if "extensions" in error and "code" in error["extensions"]:
#             dest_dir = error["extensions"]["code"]
#     dlb_key = os.path.join(dest_dir, md["FileName"])
#     print("Transferring {} to {}".format(dlb_key, dl_bkt))
#     s3.copy(copy_source, dl_bkt, dlb_key)

# def copy_to_archive(md):
#     archive_bkt = md["ArchiveBucket"]
#     copy_source = { "Bucket": md["Bucket"], "Key": md["Key"] }
#     file_base, file_ext = os.path.splitext(md["FileName"])
#     archive_filename = file_base + "_" + md["Hash"] + file_ext
#     archive_key = os.path.join(md["SerialNumber"], archive_filename)
#     print("Transferring {} to {}".format(archive_key, archive_bkt))
#     s3.copy(copy_source, archive_bkt, archive_key)
#     return md

# def copy_to_prod(md, sizes=IMG_SIZES):
#     prod_bkt = md["ProdBucket"]
#     for size, dims in sizes.items():
#         # create filename and key
#         filename = "{}-{}.{}".format(md["Hash"], size, md["FileTypeExtension"])
#         prod_key = os.path.join(size, filename)
#         print("Transferring {} to {}".format(prod_key, prod_bkt))
#         if dims is not None:
#             # resize locally then upload to s3
#             tmp_path = resize(md, filename, dims)
#             s3.upload_file(tmp_path, prod_bkt, prod_key)
#         else:
#             # copy original image directly over from staging bucket 
#             copy_source = { "Bucket": md["Bucket"], "Key": md["Key"] }
#             s3.copy(copy_source, prod_bkt, prod_key)

# def get_exif_data(img_path):
#     os.environ["PATH"] = "{}:{}/".format(os.environ["PATH"], EXIFTOOL_PATH)
#     with exiftool.ExifTool() as et:
#         ret = {}
#         exif_data = et.get_metadata(img_path)
#         # remove "group names" from keys/exif-tags
#         for key, value in exif_data.items():
#             # print("exif key: {}, value: {}".format(key, value))
#             new_key = key if (":" not in key) else key.split(":")[1]
#             ret[new_key] = value
#         return ret

# def download(bucket, key):
#     print("Downloading {}".format(key))
#     tmpkey = key.replace("/", "")
#     tmpkey = tmpkey.replace(" ", "_")
#     tmp_path = "/tmp/{}{}".format(uuid.uuid4(), tmpkey)
#     s3.download_file(bucket, key, tmp_path)
#     return tmp_path

def get_make(email):
    make = 'other'
    sender = email.get("From")
    if ('ridgetec' in sender):
        make = 'RidgeTec'
    print(f"make: {make}")
    return make

class ParseRidgeTec(HTMLParser):
    def __init__(self):
        print("initializing parse filename class")
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
                self.filename = attr[1].split('/')[4]
            if attr[0] == "data-date-time-created":
                self.date_time_created = attr[1]
            if attr[0] == "data-timezone":
                self.timezone = attr[1]       
            if attr[0] == "data-imei":
                self.imei = attr[1]
            if attr[0] == "data-account-id":
                self.account_id = attr[1]
            if attr[0] == "data-account-id":
                self.timezone = attr[1]

def handler(event, context):
    print(f"event: {event}")
    for record in event["Records"]:

        email_bucket = record["s3"]["bucket"]["name"]
        email_key = unquote_plus(record["s3"]["object"]["key"])
        print(f"New file detected in {email_bucket}: {email_bucket}"

        # # test exiftool
        # os.environ["PATH"] = "{}:{}/".format(os.environ["PATH"], EXIFTOOL_PATH)
        # print("PATH: {}".format(os.environ["PATH"]))
        # with ExifTool() as et:
        #     print("exiftool version:")
        #     print(et.version)

        # get object from S3, decode, and parse
        email_data = s3.get_object(Bucket=email_bucket, Key=email_key)
        email_data = email_data["Body"].read()
        email_data = codecs.decode(email_data, "quopri")
        email_parsed = email.message_from_bytes(email_data, policy=policy.default)
        # NOTE: headers still appear to be in quoted-printable encoding!
        # https://stackoverflow.com/questions/63110730/strange-formatting-of-html-in-ses-mail
        # print("email parsed from bytes and printed as string: ")
        # print(email_parsed.as_string())
        print(f"keys: {email_parsed.keys()}")

        # determine make
        make = get_make(email_parsed)
        # TODO: if make is 'other', end gracefully

        # get filename
        ridgetec_parser = ParseRidgeTec()
        ridgetec_parser.feed(email_parsed.as_string())
        print(f"img_url: {ridgetec_parser.img_url}")
        print(f"filename: {ridgetec_parser.filename}")
        print(f"date_time_created: {ridgetec_parser.date_time_created}")
        print(f"imei: {ridgetec_parser.imei}")
        print(f"account_id: {ridgetec_parser.account_id}")

        # TODO extract data attributes

        # TODO download image to /tmp

        # TODO write data attributes to image's exif

        # TODO: transfer to animl-images-ingestion bucket