from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from price_tracker_py.config.settings import load_mongo_config
from price_tracker_py.db.mongodb import MongoDB
from price_tracker_py.model.product_type import ProductType
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.model.stock_status import StockStatus
from price_tracker_py.repository.product_repository import (
    get_latest_observation,
    insert_observation,
    upsert_product,
)


def create_test_product() -> ScrapedProduct:
    return ScrapedProduct(
        name="Product 1",
        price=13.99,
        full_url="https://example.com/product/1",
        img_url="https://example.com/image.jpg",
        is_on_sale=False,
        product_type=ProductType.SIMPLE,
        stock_status=StockStatus.IN_STOCK,
        scraped_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_upsert_product() -> None:
    mongo_config = load_mongo_config()
    mongodb = MongoDB(mongo_config)
    product = create_test_product()
    try:
        collection = mongodb.products
        await upsert_product(collection, product)

        result = await collection.find_one(
            {"_id": product.full_url},
        )

        assert result
        assert result["name"] == product.name
        assert result["img_url"] == product.img_url
        assert result["product_type"] == product.product_type
    finally:
        await mongodb.close()


@pytest.mark.asyncio
async def test_insert_observation() -> None:
    mongo_config = load_mongo_config()
    mongodb = MongoDB(mongo_config)
    product = create_test_product()
    try:
        collection = mongodb.product_observations
        await insert_observation(collection, product)

        result = await collection.find_one(
            {
                "full_url": product.full_url,
                "timestamp": product.scraped_at,
            }
        )

        assert result
        assert result["price"] == product.price
        assert result["is_on_sale"] == product.is_on_sale
        assert result["stock_status"] == product.stock_status
    finally:
        await mongodb.close()


@pytest.mark.asyncio
async def test_get_latest_observation() -> None:
    mongo_config = load_mongo_config()
    mongodb = MongoDB(mongo_config)
    try:
        collection = mongodb.product_observations
        product = create_test_product()

        old_product = replace(
            product,
            scraped_at=datetime.now(UTC) - timedelta(hours=1),
        )

        latest_product = replace(
            product,
            scraped_at=datetime.now(UTC),
        )

        await insert_observation(collection, old_product)
        await insert_observation(collection, latest_product)

        result = await get_latest_observation(
            collection,
            full_url=product.full_url,
        )

        assert result
        assert result["timestamp"] == truncate_to_milliseconds(
            latest_product.scraped_at
        )
    finally:
        await mongodb.close()


def truncate_to_milliseconds(value: datetime) -> datetime:
    return value.replace(
        microsecond=(value.microsecond // 1000) * 1000,
    )
