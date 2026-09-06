from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pymongo import DESCENDING

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
        name="product",
        price=12.99,
        full_url="https://example.com/product",
        img_url="https://example.com/image.jpeg",
        is_on_sale=False,
        product_type=ProductType.SIMPLE,
        stock_status=StockStatus.IN_STOCK,
        scraped_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_upsert_product() -> None:
    collection = AsyncMock()
    product = create_test_product()

    await upsert_product(collection, product)

    collection.update_one.assert_awaited_once()

    args, kwargs = collection.update_one.call_args

    query_filter = args[0]
    update_operation = args[1]

    assert query_filter == {"_id": product.full_url}

    set_fields = update_operation["$set"]
    assert set_fields["name"] == product.name
    assert set_fields["img_url"] == product.img_url
    assert set_fields["product_type"] == product.product_type

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
async def test_insert_observation() -> None:
    collection = AsyncMock()
    product = create_test_product()

    await insert_observation(collection, product)

    collection.insert_one.assert_awaited_once()

    args, _ = collection.insert_one.call_args

    document = args[0]
    assert document["full_url"] == product.full_url
    assert document["price"] == product.price
    assert document["is_on_sale"] == product.is_on_sale
    assert document["stock_status"] == product.stock_status
    assert document["timestamp"] == product.scraped_at
