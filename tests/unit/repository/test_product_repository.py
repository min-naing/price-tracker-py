from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pymongo import DESCENDING

from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.repository.product_repository import (
    get_latest_observation,
    insert_observation,
    upsert_product,
)


@pytest.mark.asyncio
async def test_upsert_product(scraped_product: ScrapedProduct) -> None:
    collection = AsyncMock()

    await upsert_product(collection, scraped_product)

    collection.update_one.assert_awaited_once()

    args, kwargs = collection.update_one.call_args

    query_filter = args[0]
    update_operation = args[1]

    assert query_filter == {"_id": scraped_product.full_url}

    set_fields = update_operation["$set"]
    assert set_fields["name"] == scraped_product.name
    assert set_fields["img_url"] == scraped_product.img_url
    assert set_fields["product_type"] == scraped_product.product_type

    updated_at = set_fields["updated_at"]
    created_at = update_operation["$setOnInsert"]["created_at"]

    assert isinstance(updated_at, datetime)
    assert updated_at.tzinfo == UTC
    assert created_at == updated_at

    assert kwargs["upsert"] is True


@pytest.mark.asyncio
async def test_get_latest_observation() -> None:
    collection = AsyncMock()

    full_url = "https://example.com/product"

    await get_latest_observation(
        collection,
        full_url=full_url,
    )

    collection.find_one.assert_awaited_once_with(
        {"full_url": full_url},
        sort=[("timestamp", DESCENDING)],
    )


@pytest.mark.asyncio
async def test_insert_observation(
    scraped_product: ScrapedProduct,
) -> None:
    collection = AsyncMock()

    await insert_observation(collection, scraped_product)

    collection.insert_one.assert_awaited_once()

    args, _ = collection.insert_one.call_args

    document = args[0]
    assert document["full_url"] == scraped_product.full_url
    assert document["price"] == scraped_product.price
    assert document["is_on_sale"] == scraped_product.is_on_sale
    assert document["stock_status"] == scraped_product.stock_status
    assert document["timestamp"] == scraped_product.scraped_at
