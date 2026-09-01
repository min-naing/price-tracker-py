import pytest

from price_tracker_py.config.settings import ScraperConfig


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
