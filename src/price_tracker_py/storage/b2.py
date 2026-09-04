import io
import logging

import boto3
from mypy_boto3_s3.client import S3Client
from mypy_boto3_s3.type_defs import PutObjectOutputTypeDef

from price_tracker_py.config.settings import load_backblaze_b2_config

logger = logging.getLogger(__name__)


def create_b2_client() -> S3Client:
    config = load_backblaze_b2_config()

    return boto3.client(
        "s3",
        endpoint_url=config.end_point,
        aws_access_key_id=config.key_id,
        aws_secret_access_key=config.app_key,
    )


def upload_csv(
    client: S3Client,
    bucket_name: str,
    object_key: str,
    csv_data: bytes,
) -> PutObjectOutputTypeDef:

    # byte_stream = io.BytesIO(csv_data)
    # byte_stream.seek(0)
    # client.upload_fileobj(
    #     Fileobj=byte_stream,
    #     Bucket=bucket_name,
    #     Key=object_key,
    #     ExtraArgs={"ContentType": "text/csv"},
    # )

    result = client.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=csv_data,
        ContentType="text/csv",
    )

    logger.info(
        "Uploaded CSV to bucket %s with key %s",
        bucket_name,
        object_key,
    )

    return result
