import logging
import re
from datetime import UTC, datetime
from typing import NamedTuple

from playwright.async_api import (
    Locator,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from price_tracker_py.config.settings import ScraperConfig, get_config
from price_tracker_py.model.product_type import ProductType
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.model.stock_status import StockStatus
from price_tracker_py.scraper.exception import RateLimitedError, ScraperStructureError
from price_tracker_py.scraper.failure import check_item_failure_rate
from price_tracker_py.util.delay import calculate_exponential_backoff, polite_delay
from price_tracker_py.util.price import parse_price
from price_tracker_py.util.url import normalize_url

logger = logging.getLogger(__name__)

URL = "https://scrapingcourse.com/ecommerce"


class PriceInfo(NamedTuple):
    price: float
    is_on_sale: bool


async def scrape_product_list() -> list[ScrapedProduct]:
    products: list[ScrapedProduct] = []

    config = get_config().scraper

    current_url = URL
    page_number = 1

    consecutive_scrape_failures = 0
    consecutive_rate_limits = 0

    async with (
        async_playwright() as p,
        await p.chromium.launch(headless=True) as browser,
    ):
        page = await browser.new_page()
        page.set_default_navigation_timeout(config.navigation_timeout_ms)
        page.set_default_timeout(config.element_timeout_ms)

        while True:
            try:
                logger.info("📢 Scraping page %s", page_number)

                response = await page.goto(current_url, wait_until="domcontentloaded")
                _raise_if_rate_limited(response)

            except PlaywrightTimeoutError:
                consecutive_scrape_failures += 1

                logger.exception("⏳ Page navigation timed out on page %s", page_number)

                if _should_stop_after_scrape_failure(
                    consecutive_failures=consecutive_scrape_failures,
                    max_consecutive_page_failures=config.max_consecutive_scrape_failures,
                ):
                    break

                await polite_delay(
                    base_seconds=config.page_failure_backoff_seconds,
                )

                continue

            except RateLimitedError:
                consecutive_rate_limits += 1

                if consecutive_rate_limits > config.max_rate_limit_retries:
                    logger.error(
                        "🛑 Stopping after %s rate-limit retries",
                        config.max_rate_limit_retries,
                    )
                    break

                backoff_seconds = calculate_exponential_backoff(
                    attempt=consecutive_rate_limits,
                    base_seconds=config.rate_limit_backoff_seconds,
                )

                logger.warning(
                    "🚦 Rate limited on page %s. Retry %s/%s. Backing off %ss...",
                    page_number,
                    consecutive_rate_limits,
                    config.max_rate_limit_retries,
                    backoff_seconds,
                )

                await polite_delay(
                    base_seconds=backoff_seconds,
                    max_jitter_seconds=backoff_seconds * 0.1,
                )
                continue

            try:
                page_products = await _scrape_page(
                    page=page,
                    page_number=page_number,
                    config=config,
                )
            except ScraperStructureError:
                consecutive_scrape_failures += 1

                logger.exception("🧱 Page scraping failed on page %s", page_number)

                if _should_stop_after_scrape_failure(
                    consecutive_failures=consecutive_scrape_failures,
                    max_consecutive_page_failures=config.max_consecutive_scrape_failures,
                ):
                    break

                await polite_delay(
                    base_seconds=config.page_failure_backoff_seconds,
                )

                continue

            # The current page was successfully scraped.
            products.extend(page_products)

            try:
                next_url = await _get_next_page_url(page)

            except ScraperStructureError:
                logger.exception(
                    "❌ Pagination failed after successfully scraping page %s. "
                    "Stopping scraper.",
                    page_number,
                )
                break

            # Successful page resets both counters.
            consecutive_scrape_failures = 0
            consecutive_rate_limits = 0

            if next_url is None:
                logger.info("🏁 No more pages. Scraping finished.")
                break

            await polite_delay()

            current_url = next_url
            page_number += 1

    return products


async def _scrape_page(
    *, page: Page, page_number: int, config: ScraperConfig
) -> list[ScrapedProduct]:
    """Scrape all products from the current page."""

    product_list_wrapper = page.get_by_test_id("product-list")
    product_list = product_list_wrapper.get_by_role("listitem")

    try:
        await product_list.first.wait_for()
    except PlaywrightTimeoutError as ex:
        raise ScraperStructureError(
            f"Product list did not appear on page {page_number}"
        ) from ex

    all_products = await product_list.all()

    item_total_count = len(all_products)
    item_fail_count = 0

    page_products: list[ScrapedProduct] = []

    for product in all_products:
        try:
            scraped_product = await _scrape_product(product)

            page_products.append(scraped_product)

            logger.info(
                "  - name: %s, price: $%s",
                scraped_product.name,
                scraped_product.price,
            )

        except (
            PlaywrightTimeoutError,
            ValueError,
        ):
            item_fail_count += 1

            logger.exception(
                "⚠️ Failed to scrape item on page %s",
                page_number,
            )

            check_item_failure_rate(
                page_number=page_number,
                item_fail_count=item_fail_count,
                item_total_count=item_total_count,
                minimum_items=config.min_items_before_rate_check,
                threshold=config.fail_rate_threshold,
            )

    return page_products


async def _scrape_product(
    product: Locator,
) -> ScrapedProduct:
    """Extract and normalize one product from a product list item."""

    first_hyper_link = product.get_by_role("link").first

    product_url = await first_hyper_link.get_attribute("href")

    if product_url is None:
        raise ValueError("Missing product link")

    full_url = normalize_url(URL, product_url)

    raw_name = await first_hyper_link.get_by_role(
        "heading",
        level=2,
    ).inner_text()

    name = " ".join(raw_name.strip().split())

    img_url = await first_hyper_link.locator("img").first.get_attribute("src")

    product_price_wrapper = product.get_by_test_id("product-price")

    price, is_on_sale = await _parse_price_info(product_price_wrapper)

    has_variants = await product.get_by_role(
        "link",
        name=re.compile(
            "select options",
            flags=re.IGNORECASE,
        ),
    ).is_visible()

    add_to_cart_visible = await product.get_by_role(
        "link",
        name=re.compile(
            "add to cart",
            flags=re.IGNORECASE,
        ),
    ).is_visible()

    if has_variants:
        product_type = ProductType.VARIABLE
        stock_status = StockStatus.UNKNOWN
    else:
        product_type = ProductType.SIMPLE
        stock_status = (
            StockStatus.IN_STOCK if add_to_cart_visible else StockStatus.OUT_OF_STOCK
        )

    return ScrapedProduct(
        name=name,
        price=price,
        full_url=full_url,
        img_url=img_url,
        is_on_sale=is_on_sale,
        product_type=product_type,
        stock_status=stock_status,
        scraped_at=datetime.now(UTC),
    )


async def _get_next_page_url(page: Page) -> str | None:
    """Return the next page URL, or None when there is no next page."""

    next_link = page.get_by_role("link", name="→").first

    if await next_link.count() == 0:
        return None

    next_url = await next_link.get_attribute("href")

    if next_url is None:
        raise ScraperStructureError("Next page link exists but has no href")

    return next_url


async def _parse_price_info(
    price_wrapper: Locator,
) -> PriceInfo:
    ins_locator = price_wrapper.locator("ins .woocommerce-Price-amount")

    has_sale_price = await ins_locator.is_visible()

    if has_sale_price:
        price_text = await ins_locator.inner_text()
    else:
        price_text = await price_wrapper.locator(
            ".woocommerce-Price-amount"
        ).first.inner_text()

    price = parse_price(price_text)

    return PriceInfo(
        price=price,
        is_on_sale=has_sale_price,
    )


def _should_stop_after_scrape_failure(
    *,
    consecutive_failures: int,
    max_consecutive_page_failures: int,
) -> bool:

    if consecutive_failures >= max_consecutive_page_failures:
        logger.error(
            "🛑 Stopping after %s consecutive page failures",
            consecutive_failures,
        )
        return True

    return False


def _raise_if_rate_limited(
    response: Response | None,
) -> None:
    if response is not None and response.status == 429:
        raise RateLimitedError(f"Received 429 from {response.url}")
