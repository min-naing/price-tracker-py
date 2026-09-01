import csv
import io

from price_tracker_py.model.scraped_product import ScrapedProduct

CSV_HEADERS = [
    "name",
    "price",
    "is_on_sale",
    "product_type",
    "stock_status",
    "img_url",
    "full_url",
    "scraped_at",
]


def export_to_csv(products: list[ScrapedProduct]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)

    writer.writerow(CSV_HEADERS)

    for product in products:
        writer.writerow(
            [
                product.name,
                product.price,
                product.is_on_sale,
                product.product_type.value,
                product.stock_status.value,
                product.img_url or "",
                product.full_url,
                product.scraped_at.isoformat(),
            ]
        )

    return buffer.getvalue().encode("utf-8")
