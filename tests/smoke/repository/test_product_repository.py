from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from tests.smoke.utils import truncate_to_milliseconds

from price_tracker_py.db.mongodb import MongoDB
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.repository.product_repository import (
    get_latest_observation,
    insert_observation,
    upsert_product,
)


@pytest.mark.asyncio
async def test_upsert_product(
    scraped_product: ScrapedProduct,
    db: MongoDB,
) -> None:
    try:
        collection = db.products
        await upsert_product(collection, scraped_product)

        result = await collection.find_one(
            {"_id": scraped_product.full_url},
        )

        assert result
        assert result["name"] == scraped_product.name
        assert result["img_url"] == scraped_product.img_url
        assert result["product_type"] == scraped_product.product_type
    finally:
        await db.products.delete_one({"_id": scraped_product.full_url})


@pytest.mark.asyncio
async def test_insert_observation(
    scraped_product: ScrapedProduct,
    db: MongoDB,
) -> None:
    try:
        collection = db.product_observations
        await insert_observation(collection, scraped_product)

        result = await collection.find_one(
            {
                "full_url": scraped_product.full_url,
                "timestamp": scraped_product.scraped_at,
            }
        )

        assert result
        assert result["price"] == scraped_product.price
        assert result["is_on_sale"] == scraped_product.is_on_sale
        assert result["stock_status"] == scraped_product.stock_status
    finally:
        await db.product_observations.delete_one({"full_url": scraped_product.full_url})


@pytest.mark.asyncio
async def test_get_latest_observation(
    scraped_product: ScrapedProduct,
    db: MongoDB,
) -> None:
    old_product = replace(
        scraped_product,
        scraped_at=datetime.now(UTC) - timedelta(hours=1),
    )

    latest_product = replace(
        scraped_product,
        scraped_at=datetime.now(UTC),
    )
    try:
        collection = db.product_observations

        await insert_observation(collection, old_product)
        await insert_observation(collection, latest_product)

        result = await get_latest_observation(
            collection,
            full_url=scraped_product.full_url,
        )

        assert result
        assert result["timestamp"] == truncate_to_milliseconds(
            latest_product.scraped_at
        )
    finally:
        await db.product_observations.delete_many(
            {"full_url": scraped_product.full_url}
        )
