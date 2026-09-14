import pytest

from price_tracker_py.scraper.ecommerce import scrape_product_list
from price_tracker_py.util.url import normalize_url


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scrape_product_list() -> None:
    products = await scrape_product_list(max_pages=1)

    assert products

    product_urls = [product.full_url for product in products]

    assert len(products) == len(set(product_urls))

    for product in products:
        assert product.name
        assert product.price > 0
        assert product.full_url.startswith("https://")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scrape_product_list_follows_pagination() -> None:
    products = await scrape_product_list(max_pages=2)

    assert products

    product_urls = {product.full_url for product in products}

    EXPECTED_PAGE_1_PRODUCT_URL = normalize_url(
        "https://www.scrapingcourse.com/ecommerce",
        "https://www.scrapingcourse.com/ecommerce/product/affirm-water-bottle/",
    )

    EXPECTED_PAGE_2_PRODUCT_URL = normalize_url(
        "https://www.scrapingcourse.com/ecommerce",
        "https://www.scrapingcourse.com/ecommerce/product/bolo-sport-watch/",
    )

    assert EXPECTED_PAGE_1_PRODUCT_URL in product_urls
    assert EXPECTED_PAGE_2_PRODUCT_URL in product_urls
