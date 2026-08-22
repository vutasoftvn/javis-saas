import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "javis-vault")

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1"
    )

def ensure_bucket_exists():
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            raise

def put_object(key: str, content: bytes, content_type: str = "text/markdown"):
    s3 = get_s3_client()
    try:
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=content, ContentType=content_type)
    except ClientError as exc:
        # A test process and one-off CLI operation do not necessarily run the
        # FastAPI lifespan.  Recover the only safe bootstrap failure and retry
        # once; all other storage errors remain visible to the caller.
        if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchBucket"}:
            raise
        ensure_bucket_exists()
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=content, ContentType=content_type)

def get_object(key: str) -> bytes:
    s3 = get_s3_client()
    response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
    return response['Body'].read()

def generate_presigned_upload_url(key: str, expires_in: int = 3600) -> str:
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=expires_in
    )
    return url

def generate_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    s3 = get_s3_client()
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=expires_in
    )
    return url
