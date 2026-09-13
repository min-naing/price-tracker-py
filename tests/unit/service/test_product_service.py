from dataclasses import replace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from price_tracker_py.db.document import ProductObservationDocument
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.service.product_service import (
    build_price_drop_alert,
    sync_product,
)


def test_build_price_drop_alert_when_no_previous_observation(
    scraped_product: ScrapedProduct,
) -> None:
    result = build_price_drop_alert(scraped_product, None)
    assert result is None


def test_build_price_drop_alert_when_price_dropped(
    scraped_product: ScrapedProduct,
    product_observation_document: ProductObservationDocument,
) -> None:
    product = replace(scraped_product, price=10.99)

    previous: ProductObservationDocument = {
        **product_observation_document,
        "price": 12.99,
    }

    result = build_price_drop_alert(product, previous)

    assert result is not None
    assert product.name in result
    assert f"${previous['price']:.2f}" in result
    assert f"${product.price:.2f}" in result
    assert product.full_url in result


@pytest.mark.parametrize(
    ("current_price", "previous_price"),
    [
        (12.99, 12.99),  # unchanged
        (13.99, 12.99),  # increased
    ],
)
def test_build_price_drop_alert_returns_none_when_price_not_dropped(
    scraped_product: ScrapedProduct,
    product_observation_document: ProductObservationDocument,
    current_price: float,
    previous_price: float,
) -> None:
    product = replace(
        scraped_product,
        price=current_price,
    )

    previous: ProductObservationDocument = {
        **product_observation_document,
        "price": previous_price,
    }

    result = build_price_drop_alert(product, previous)

    assert result is None


@patch("price_tracker_py.service.product_service.build_price_drop_alert")
@patch("price_tracker_py.service.product_service.insert_observation")
@patch("price_tracker_py.service.product_service.upsert_product")
@patch("price_tracker_py.service.product_service.get_latest_observation")
@pytest.mark.asyncio
async def test_sync_product_when_no_price_dropped(
    mock_get_latest_observation: AsyncMock,
    mock_upsert_product: AsyncMock,
    mock_insert_observation: AsyncMock,
    mock_build_alert: Mock,
    scraped_product: ScrapedProduct,
    product_observation_document: ProductObservationDocument,
) -> None:
    product = replace(scraped_product, price=12.99)

    previous: ProductObservationDocument = {
        **product_observation_document,
        "price": 10.99,
    }

    products = Mock()
    product_observations = Mock()

    mock_get_latest_observation.return_value = previous

    mock_build_alert.return_value = None

    result = await sync_product(
        product,
        products,
        product_observations,
    )

    mock_get_latest_observation.assert_awaited_once_with(
        product_observations,
        full_url=product.full_url,
    )
    mock_build_alert.assert_called_once_with(product, previous)
    mock_upsert_product.assert_awaited_once_with(products, product)
    mock_insert_observation.assert_awaited_once_with(
        product_observations,
        product,
    )

    assert result is None


@patch("price_tracker_py.service.product_service.build_price_drop_alert")
@patch("price_tracker_py.service.product_service.insert_observation")
@patch("price_tracker_py.service.product_service.upsert_product")
@patch("price_tracker_py.service.product_service.get_latest_observation")
@pytest.mark.asyncio
async def test_sync_product_when_price_dropped(
    mock_get_latest_observation: AsyncMock,
    mock_upsert_product: AsyncMock,
    mock_insert_observation: AsyncMock,
    mock_build_alert: Mock,
    scraped_product: ScrapedProduct,
    product_observation_document: ProductObservationDocument,
) -> None:
    product = replace(scraped_product, price=10.99)

    previous: ProductObservationDocument = {
        **product_observation_document,
        "price": 12.99,
    }

    products = Mock()
    product_observations = Mock()
    expected_alert_message = "price dropped alert"

    mock_get_latest_observation.return_value = previous

    mock_build_alert.return_value = expected_alert_message

    result = await sync_product(
        product,
        products,
        product_observations,
    )

    mock_get_latest_observation.assert_awaited_once_with(
        product_observations,
        full_url=product.full_url,
    )
    mock_build_alert.assert_called_once_with(product, previous)
    mock_upsert_product.assert_awaited_once_with(products, product)
    mock_insert_observation.assert_awaited_once_with(
        product_observations,
        product,
    )

    assert result is not None
    assert result == expected_alert_message
