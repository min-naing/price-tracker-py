from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from tests.smoke.utils import truncate_to_milliseconds

from price_tracker_py.db.mongodb import MongoDB
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.service.product_service import sync_product


@pytest.mark.asyncio
async def test_sync_product_with_no_previous_observation(
    scraped_product: ScrapedProduct,
    db: MongoDB,
) -> None:

    try:
        product = replace(scraped_product, full_url="https://example.com/sync/1")

        alert = await sync_product(product, db.products, db.product_observations)

        assert alert is None

        result = await db.products.find_one({"_id": product.full_url})

        assert result is not None
        assert result["name"] == product.name
        assert result["img_url"] == product.img_url
        assert result["product_type"] == product.product_type

        observation = await db.product_observations.find_one(
            {"full_url": product.full_url}
        )

        assert observation is not None
        assert observation["timestamp"] == truncate_to_milliseconds(product.scraped_at)
        assert observation["price"] == product.price
        assert observation["is_on_sale"] == product.is_on_sale
        assert observation["stock_status"] == product.stock_status

    finally:
        await db.products.delete_one({"_id": product.full_url})
        await db.product_observations.delete_one({"full_url": product.full_url})


@pytest.mark.asyncio
async def test_sync_product_with_price_drop(
    scraped_product: ScrapedProduct,
    db: MongoDB,
) -> None:

    previous_product = replace(
        scraped_product,
        full_url="https://example.com/sync/1",
        price=12.99,
        is_on_sale=False,
        scraped_at=datetime.now(UTC) - timedelta(hours=1),
    )

    product = replace(
        scraped_product,
        full_url="https://example.com/sync/1",
        price=10.99,
        is_on_sale=True,
        scraped_at=datetime.now(UTC),
    )

    try:
        previous_alert = await sync_product(
            previous_product, db.products, db.product_observations
        )

        assert previous_alert is None

        last_alert = await sync_product(product, db.products, db.product_observations)

        assert last_alert is not None
        assert f"{product.price:.2f}" in last_alert
        assert f"{previous_product.price:.2f}" in last_alert

        result = await db.products.find_one({"_id": product.full_url})

        assert result is not None
        assert result["name"] == product.name
        assert result["img_url"] == product.img_url
        assert result["product_type"] == product.product_type

        previous_observation = await db.product_observations.find_one(
            {
                "full_url": previous_product.full_url,
                "timestamp": previous_product.scraped_at,
            }
        )

        last_observation = await db.product_observations.find_one(
            {
                "full_url": product.full_url,
                "timestamp": product.scraped_at,
            }
        )

        assert previous_observation is not None
        assert previous_observation["price"] == previous_product.price
        assert previous_observation["is_on_sale"] == previous_product.is_on_sale
        assert previous_observation["timestamp"] == truncate_to_milliseconds(
            previous_product.scraped_at
        )

        assert last_observation is not None
        assert last_observation["price"] == product.price
        assert last_observation["is_on_sale"] == product.is_on_sale
        assert last_observation["timestamp"] == truncate_to_milliseconds(
            product.scraped_at
        )

    finally:
        await db.products.delete_one({"_id": product.full_url})
        await db.product_observations.delete_many({"full_url": product.full_url})
