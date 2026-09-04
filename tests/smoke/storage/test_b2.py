import pytest

from price_tracker_py.config.settings import load_backblaze_b2_config
from price_tracker_py.storage.b2 import create_b2_client, upload_csv


@pytest.mark.smoke
def test_upload_csv():

    config = load_backblaze_b2_config()

    csv_data = b"name,price\nProduct,10.32\n"
    object_key = "test.csv"

    client = create_b2_client()

    result = upload_csv(
        client=client,
        bucket_name=config.bucket_name,
        object_key=object_key,
        csv_data=csv_data,
    )

    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200
