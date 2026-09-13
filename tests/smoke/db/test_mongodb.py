from price_tracker_py.db.mongodb import MongoDB


async def test_connect_creates_timeseries_collection(
    db: MongoDB,
) -> None:

    async with await db.database.list_collections(
        filter={"name": MongoDB.PRODUCT_OBSERVATIONS_COLLECTION_NAME}
    ) as cursor:
        collections = await cursor.to_list()

    assert collections

    assert collections[0]["type"] == "timeseries"
