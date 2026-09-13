from pymongo.asynchronous.collection import AsyncCollection

from price_tracker_py.db.document import ProductDocument, ProductObservationDocument
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.repository.product_repository import (
    get_latest_observation,
    insert_observation,
    upsert_product,
)


async def sync_product(
    product: ScrapedProduct,
    products: AsyncCollection[ProductDocument],
    product_observations: AsyncCollection[ProductObservationDocument],
) -> str | None:
    previous = await get_latest_observation(
        product_observations, full_url=product.full_url
    )

    alert_message = build_price_drop_alert(product, previous)

    await upsert_product(products, product)

    await insert_observation(product_observations, product)

    return alert_message


def build_price_drop_alert(
    product: ScrapedProduct,
    previous: ProductObservationDocument | None,
) -> str | None:
    if previous is None or product.price >= previous["price"]:
        return None

    return (
        f"🚨 Price drop! {product.name}\n"
        f"Was: ${previous['price']:.2f} → Now: ${product.price:.2f}\n"
        f"{product.full_url}"
    )
