import csv
import io
from dataclasses import replace

import pytest

from price_tracker_py.export.csv_exporter import CSV_HEADERS, export_to_csv
from price_tracker_py.model.scraped_product import ScrapedProduct


def test_export_to_csv_returns_headers() -> None:
    result = export_to_csv([])

    buffer = io.StringIO(result.decode("utf-8"), newline="")
    reader = csv.reader(buffer)

    assert list(reader) == [CSV_HEADERS]


@pytest.mark.parametrize("product_count", [1, 2])
def test_export_to_csv_exports_products(
    scraped_product: ScrapedProduct,
    product_count: int,
) -> None:
    product_1 = replace(
        scraped_product,
        name="Coffee",
        price=30.34,
        full_url="https://example.com/1",
    )
    product_2 = replace(
        scraped_product,
        name="Tea",
        price=20.50,
        full_url="https://example.com/2",
    )

    products = [product_1, product_2][:product_count]

    result = export_to_csv(products)

    buffer = io.StringIO(result.decode("utf-8"), newline="")
    reader = csv.reader(buffer)
    rows = list(reader)

    assert len(rows) == product_count + 1

    for row, product in zip(rows[1:], products, strict=True):
        expected_row = [
            product.name,
            str(product.price),
            str(product.is_on_sale),
            product.product_type.value,
            product.stock_status.value,
            product.img_url or "",
            product.full_url,
            product.scraped_at.isoformat(),
        ]

        assert row == expected_row


def test_export_to_csv_handles_missing_img_url(
    scraped_product: ScrapedProduct,
) -> None:

    product = replace(
        scraped_product,
        name="ကော်ဖီ",
        price=30.34,
        img_url=None,
        full_url="https://example.com/product/1",
    )

    result = export_to_csv([product])

    buffer = io.StringIO(result.decode("utf-8"), newline="")
    reader = csv.reader(buffer)

    rows = list(reader)

    assert rows[1][CSV_HEADERS.index("img_url")] == ""


def test_export_to_csv_preserves_unicode(
    scraped_product: ScrapedProduct,
) -> None:
    product = replace(
        scraped_product,
        name="ကော်ဖီ",
        price=30.34,
        full_url="https://example.com/product/1",
    )

    result = export_to_csv([product])
    decoded_value = result.decode("utf-8")
    buffer = io.StringIO(decoded_value, newline="")
    reader = csv.reader(buffer)
    rows = list(reader)

    assert rows[1][CSV_HEADERS.index("name")] == "ကော်ဖီ"


def test_export_to_csv_handles_special_characters(
    scraped_product: ScrapedProduct,
) -> None:
    product = replace(
        scraped_product,
        name="Coffee, Dark Roast",
        price=30.34,
        full_url="https://example.com/product/1",
    )

    result = export_to_csv([product])
    buffer = io.StringIO(result.decode("utf-8"), newline="")
    reader = csv.reader(buffer)

    rows = list(reader)

    assert rows[1][CSV_HEADERS.index("name")] == "Coffee, Dark Roast"
