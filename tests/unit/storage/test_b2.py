from unittest.mock import Mock, patch

from price_tracker_py.config.settings import BackblazeB2Config
from price_tracker_py.storage.b2 import create_b2_client, upload_csv


# patch decorators are applied from the bottom upward
@patch("price_tracker_py.storage.b2.load_backblaze_b2_config")
@patch("price_tracker_py.storage.b2.boto3.client")
@patch("price_tracker_py.storage.b2.BotoConfig")
def test_create_b2_client(
    mock_boto_config: Mock,
    mock_boto_client: Mock,
    mock_load_config: Mock,
) -> None:

    config = BackblazeB2Config(
        end_point="https://",
        key_id="key_id",
        app_key="app_key",
        bucket_name="test-bucket",
    )

    mock_load_config.return_value = config

    create_b2_client()

    mock_load_config.assert_called_once_with()

    mock_boto_config.assert_called_once_with(
        retries={
            "mode": "standard",
        },
    )

    mock_boto_client.assert_called_once_with(
        "s3",
        endpoint_url=config.end_point,
        aws_access_key_id=config.key_id,
        aws_secret_access_key=config.app_key,
        config=mock_boto_config.return_value,
    )


def test_csv_upload() -> None:
    client = Mock()
    csv_data = b"name,price\nProduct,10.99\n"
    expected_result = {"ETag": "test-etag"}

    client.put_object.return_value = expected_result

    result = upload_csv(
        client=client,
        object_key="products/test.csv",
        bucket_name="test-bucket",
        csv_data=csv_data,
    )

    assert result == expected_result

    client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="products/test.csv",
        Body=csv_data,
        ContentType="text/csv",
    )
