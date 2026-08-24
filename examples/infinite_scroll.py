import asyncio
import logging
import pprint
from dataclasses import dataclass

from playwright.async_api import async_playwright, expect
from src.price_tracker_py.util.delay import polite_delay
from src.price_tracker_py.util.url import normalize_url

from price_tracker_py.scraper.exception import TooManyItemFailuresError
from price_tracker_py.util.price import parse_price

logger = logging.getLogger(__name__)

MAX_SCROLL_ATTEMPTS = 50
SCROLL_DELAY_SECONDS = 1.0
SCROLL_WAIT_TIMEOUT_MS = 5000
ITEM_FAIL_RATE_THRESHOLD = 0.3
MIN_ITEMS_BEFORE_RATE_CHECK = 5


@dataclass(frozen=True)
class ScrapedProduct:
    name: str
    price: float
    full_url: str
    img_url: str | None


BASE_URL = "https://www.scrapingcourse.com/infinite-scrolling"


async def scrape_product_list() -> list[ScrapedProduct]:
    async with (
        async_playwright() as p,
        await p.chromium.launch(headless=True) as browser,
    ):
        page = await browser.new_page()

        await page.goto(BASE_URL, wait_until="domcontentloaded")

        product_items_selector = ".product-item"
        product_items = page.locator(product_items_selector)
        await expect(product_items.first).to_be_visible()

        item_count = len(await product_items.all())
        logger.info(f"Initial product item count: {item_count}")

        scroll_attempts = 0

        while scroll_attempts < MAX_SCROLL_ATTEMPTS:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            scroll_attempts += 1

            try:
                await expect(product_items.nth(item_count)).to_be_visible(
                    timeout=SCROLL_WAIT_TIMEOUT_MS
                )
            except AssertionError:
                logger.info("No new items loaded after scrolling, reached the end.")
                break

            product_items = page.locator(product_items_selector)
            new_item_count = len(await product_items.all())

            logging.info(f"Product item count after scroll: {new_item_count}")

            item_count = new_item_count

            await polite_delay(SCROLL_DELAY_SECONDS)

        if scroll_attempts >= MAX_SCROLL_ATTEMPTS:
            logger.warning(
                "Stopped after %s scroll attempts, "
                "page may have endless or looping content",
                MAX_SCROLL_ATTEMPTS,
            )

        # extract content
        products: list[ScrapedProduct] = []

        product_items = page.locator(product_items_selector)
        all_items = await product_items.all()
        item_total_count = len(all_items)

        item_fail_count = 0

        for product in all_items:
            try:
                hyper_link = product.get_by_role("link").first
                raw_url = await hyper_link.get_attribute("href")

                if raw_url is None:
                    logger.warning("skipping product item: missing herf")
                    item_fail_count += 1
                    continue

                name = (
                    await hyper_link.locator(".product-name").first.inner_text()
                ).strip()
                img_url = await hyper_link.locator("img").first.get_attribute("src")

                if img_url is not None:
                    img_url = normalize_url(BASE_URL, img_url)

                raw_price = await hyper_link.locator(
                    ".product-price"
                ).first.inner_text()
                price = parse_price(raw_price.strip())

                full_url = normalize_url(BASE_URL, raw_url)

                products.append(
                    ScrapedProduct(
                        name=name,
                        price=price,
                        full_url=full_url,
                        img_url=img_url,
                    )
                )
            except Exception as item_ex:
                item_fail_count += 1
                logger.exception("Failed to extract product, skipping")

                fail_rate = item_fail_count / item_total_count
                if (
                    item_total_count >= MIN_ITEMS_BEFORE_RATE_CHECK
                    and fail_rate > ITEM_FAIL_RATE_THRESHOLD
                ):
                    raise TooManyItemFailuresError(
                        f"Too many extraction failures: "
                        f"{item_fail_count}/{item_total_count} items failed "
                        f"— site structure may have changed"
                    ) from item_ex

        logger.info("Printing products: \n%s", pprint.pformat(products, width=1))
        return products


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_product_list())


if __name__ == "__main__":
    main()
