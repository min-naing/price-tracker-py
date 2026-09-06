from price_tracker_py.config.settings import load_mongo_config
from price_tracker_py.db.mongodb import MongoDB


async def test_connect_creates_timeseries_collection() -> None:
    mongo_config = load_mongo_config()
    mongodb = MongoDB(mongo_config)

    try:
        await mongodb.connect()

        async with await mongodb.database.list_collections(
            filter={"name": MongoDB.PRODUCT_OBSERVATIONS_COLLECTION_NAME}
        ) as cursor:
            collections = await cursor.to_list()

        assert collections

        assert collections[0]["type"] == "timeseries"

    finally:
        await mongodb.close()
