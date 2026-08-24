import asyncio
import logging
import pprint
import re
from pathlib import Path

from playwright.async_api import (
    BrowserContext,
    Locator,
    Page,
    TimeoutError as PlaywrightTimeOutError,
    async_playwright,
)

from price_tracker_py.config.paths import PROJECT_ROOT
from price_tracker_py.scraper.exception import TooManyItemFailuresError
from price_tracker_py.util.url import normalize_url

logger = logging.getLogger(__name__)

BASE_URL = "https://www.scrapingcourse.com"
AUTH_STORAGE_PATH = PROJECT_ROOT / "playwright" / ".auth" / "user.json"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
LOCATOR_TIME_OUT_MS = 5000


async def _login(context: BrowserContext, page: Page) -> None:
    await page.goto(f"{BASE_URL}/login/csrf", wait_until="domcontentloaded")

    await page.get_by_label("Email Address").fill("admin@example.com")
    await page.get_by_label("Password").fill("password")

    await page.get_by_role("button", name="Login").click()

    logout_link = page.get_by_role(
        "link", name=re.compile("logout", flags=re.IGNORECASE)
    )
    await logout_link.wait_for(timeout=LOCATOR_TIME_OUT_MS)

    await context.storage_state(path=AUTH_STORAGE_PATH)

    logger.info(f"After authentication the page url: {page.url}")


async def scrape_protected_data(
    protected_url: str = DASHBOARD_URL,
) -> list[dict[str, str]]:
    async with (
        async_playwright() as p,
        await p.chromium.launch(headless=True) as browser,
    ):
        auth_file = Path(AUTH_STORAGE_PATH)

        if not auth_file.exists():
            auth_file.parent.mkdir(parents=True, exist_ok=True)
            context = await browser.new_context()
        else:
            context = await browser.new_context(storage_state=AUTH_STORAGE_PATH)

        page = await context.new_page()
        page.set_default_timeout(LOCATOR_TIME_OUT_MS)

        await page.goto(protected_url, wait_until="domcontentloaded")

        logout_link = page.get_by_role(
            "link", name=re.compile("logout", flags=re.IGNORECASE)
        )

        try:
            await logout_link.wait_for(timeout=LOCATOR_TIME_OUT_MS)
        except PlaywrightTimeOutError:
            is_authenticated = False
        else:
            is_authenticated = True

        if not is_authenticated:
            await _login(context, page)
            await page.goto(protected_url, wait_until="domcontentloaded")

        # scrape protected data
        items = page.locator("#product-grid .product-item")
        await items.first.wait_for()

        return await extract_content(items)


async def extract_content(items: Locator) -> list[dict[str, str]]:
    products: list[dict[str, str]] = []
    all_items = await items.all()
    item_total_count = len(all_items)
    item_fail_count = 0

    for item in all_items:
        try:
            product_link = item.get_by_role("link").first
            raw_url = await product_link.get_attribute("href")

            if raw_url is None:
                logger.warning("skipping product item - missing product url")
                item_fail_count += 1
                continue

            img_url = await product_link.locator("img").first.get_attribute("src")
            name = await product_link.locator(".product-name").inner_text()
            price = await product_link.locator(".product-price").inner_text()

            products.append(
                {
                    "name": name.strip(),
                    "price": price.strip(),
                    "img_url": "N/A" if img_url is None else img_url,
                    "full_url": normalize_url(BASE_URL, raw_url),
                }
            )

        except Exception as item_ex:
            item_fail_count += 1
            logger.error(f"Failed to extract product, skipping: {item_ex}")

            if item_total_count >= 5 and item_fail_count / item_total_count > 0.3:
                raise TooManyItemFailuresError(
                    f"Too many extraction failures: "
                    f"{item_fail_count}/{item_total_count} items failed "
                    f"— site structure may have changed"
                ) from item_ex

    logger.info("Printing products:\n%s", pprint.pformat(products, indent=2))

    return products


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(scrape_protected_data())


if __name__ == "__main__":
    main()
