from datetime import UTC, datetime

import pytest

from price_tracker_py.model.product_type import ProductType
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.model.stock_status import StockStatus


@pytest.fixture
def scraped_product() -> ScrapedProduct:
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
