from datetime import UTC, datetime

import pytest

from price_tracker_py.config.settings import ScraperConfig
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


@pytest.fixture
def scraper_config() -> ScraperConfig:
    return ScraperConfig(
        navigation_timeout_ms=30_000,
        element_timeout_ms=5000,
        max_rate_limit_retries=5,
        rate_limit_backoff_seconds=10,
        max_consecutive_scrape_failures=3,
        page_failure_backoff_seconds=3,
        fail_rate_threshold=0.3,
        min_items_before_rate_check=5,
    )
