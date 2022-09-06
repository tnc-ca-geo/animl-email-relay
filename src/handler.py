#!/opt/bin/perl

import os
# import uuid
from urllib.parse import unquote_plus
from email.parser import BytesParser
# from PIL import Image, ImageFile
# ImageFile.LOAD_TRUNCATED_IMAGES = True
import boto3
from exiftool import ExifTool


EXIFTOOL_PATH = "{}/exiftool".format(os.environ["LAMBDA_TASK_ROOT"])

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

def handler(event, context):
    print("event: {}".format(event))
    for record in event["Records"]:

        email_bucket = record["s3"]["bucket"]["name"]
        email_key = unquote_plus(record["s3"]["object"]["key"])
        print("New file detected in {}: {}".format(email_bucket, email_key))

        # test exiftool
        os.environ["PATH"] = "{}:{}/".format(os.environ["PATH"], EXIFTOOL_PATH)
        with ExifTool() as et:
            print("exiftool version:")
            print(et.version)

        # get object from S3
        email_data = s3.get_object(Bucket = email_bucket, Key = email_key)
        email_data = email_data["Body"].read()

        # parse email 
        parser = BytesParser()
        email_parsed = parser.parsebytes(email_data)
        print("email parsed by parser.parsebytes: ")
        print(email_parsed)

        # TODO: determine make 

        # TODO: process

        # TODO: transfer to animl-images-ingestion bucket