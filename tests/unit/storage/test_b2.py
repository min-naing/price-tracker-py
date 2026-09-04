from unittest.mock import Mock, patch

from price_tracker_py.config.settings import BackblazeB2Config
from price_tracker_py.storage.b2 import create_b2_client, upload_csv


def test_create_b2_client() -> None:

    config = BackblazeB2Config(
        region="us",
        end_point="https://",
        key_id="key_id",
        app_key="app_key",
        bucket_name="test-bucket",
    )

    with (
        patch(
            "price_tracker_py.storage.b2.load_backblaze_b2_config",
            return_value=config,
        ) as mock_load_config,
        patch(
            "price_tracker_py.storage.b2.boto3.client",
        ) as mock_boto_client,
    ):
        create_b2_client()

    mock_load_config.assert_called_once_with()

    mock_boto_client.assert_called_once_with(
        "s3",
        endpoint_url=config.end_point,
        aws_access_key_id=config.key_id,
        aws_secret_access_key=config.app_key,
    )


def test_csv_upload() -> None:
    client = Mock()
    csv_data = b"name,price\nProduct,10.99\n"

    upload_csv(
        client=client,
        object_key="products/test.csv",
        bucket_name="test-bucket",
        csv_data=csv_data,
    )

    client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="products/test.csv",
        Body=csv_data,
        ContentType="text/csv",
    )
