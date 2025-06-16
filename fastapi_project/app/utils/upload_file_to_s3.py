import boto3
import os
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_UPLOAD_PREFIX = os.getenv("S3_UPLOAD_PREFIX", "")


def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )


def upload_file_to_s3(file_obj, filename):
    s3_client = get_s3_client()

    s3_key = f"resume/{filename}"

    file_obj.seek(0)
    s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, s3_key)

    presigned_url = s3_client.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=3600,  # 1시간 유효
    )
    return presigned_url


# def upload_file_to_s3(file_obj, filename):
#     s3_client = boto3.client(
#         "s3",
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#         region_name=AWS_REGION,
#     )

#     s3_key = f"resume/{filename}"
#     print(f"bucket name : {S3_BUCKET_NAME}")
#     print(f"region name : {AWS_REGION}")
#     print(f"s3_key: {s3_key}")

#     # 업로드 (private)
#     s3_client.upload_fileobj(file_obj, S3_BUCKET_NAME, s3_key)

#     # Presigned URL 발급 (다운로드용)
#     # presigned_url = s3_client.generate_presigned_url(
#     #     ClientMethod="get_object",
#     #     Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
#     #     ExpiresIn=3600,  # 1시간 유효
#     # )
#     presigned_url = s3_client.generate_presigned_url(
#         ClientMethod="get_object",
#         Params={"Bucket": S3_BUCKET_NAME, "Key": s3_key},
#         ExpiresIn=3600,  # 1시간 유효
#     )

#     return presigned_url
