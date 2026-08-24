import asyncio
import logging
from dataclasses import dataclass
from pprint import pformat

from playwright.async_api import Locator, async_playwright, expect

from price_tracker_py.scraper.exception import TooManyItemFailuresError
from price_tracker_py.util.price import parse_price

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapedProduct:
    product_id: str
    name: str
    category: str
    price: float
    in_stock: bool


async def scrape_product() -> list[ScrapedProduct]:
    async with (
        async_playwright() as p,
        await p.chromium.launch(headless=True) as browser,
    ):
        page = await browser.new_page()

        await page.goto(
            "https://www.scrapingcourse.com/table-parsing",
            wait_until="domcontentloaded",
        )

        table = page.locator("table#product-catalog").first
        await expect(table).to_be_visible()

        rows = await extract_table(table)

        products: list[ScrapedProduct] = []
        item_fail_count = 0
        item_total_count = len(rows)

        for row in rows:
            try:
                products.append(
                    ScrapedProduct(
                        product_id=row["product_id"],
                        name=row["name"],
                        category=row["category"],
                        price=parse_price(row["price"]),
                        in_stock=row["in_stock"].lower() == "yes",
                    )
                )
            except Exception as row_ex:
                item_fail_count += 1
                logger.error(f"Failed to parse row, skipping: {row_ex}")

                if item_total_count >= 5 and item_fail_count / item_total_count > 0.3:
                    raise TooManyItemFailuresError(
                        f"Too many row parse failures: "
                        f"{item_fail_count}/{item_total_count} rows failed "
                        f"— table structure may have changed"
                    ) from row_ex

        logger.info("Printing products: \n%s", pformat(products, width=1))
        return products


async def extract_table(table: Locator) -> list[dict[str, str]]:
    headers = await table.locator("thead > tr > th").all_inner_texts()
    headers = [h.strip().lower().replace(" ", "_") for h in headers]

    rows: list[dict[str, str]] = []
    cell_rows = table.locator("tbody > tr")

    for row in await cell_rows.all():
        cells = await row.locator("td").all_inner_texts()
        cells = [c.strip() for c in cells]

        if len(cells) != len(headers):
            logger.warning(
                f"Column mismatch: {len(cells)} cells vs {len(headers)} headers, skipping row"
            )
            continue

        rows.append(dict(zip(headers, cells, strict=True)))

    return rows


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    asyncio.run(scrape_product())


if __name__ == "__main__":
    main()
