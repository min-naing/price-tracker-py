from datetime import UTC, datetime

from pymongo import DESCENDING
from pymongo.asynchronous.collection import AsyncCollection

from price_tracker_py.db.document import (
    ProductDocument,
    ProductObservationDocument,
    ProductUpdateFields,
)
from price_tracker_py.model.scraped_product import ScrapedProduct


async def upsert_product(
    collection: AsyncCollection[ProductDocument],
    product: ScrapedProduct,
) -> None:
    now = datetime.now(UTC)

    query_filter = {"_id": product.full_url}

    set_fields: ProductUpdateFields = {
        "name": product.name,
        "img_url": product.img_url,
        "product_type": product.product_type,
        "updated_at": now,
    }

    update_operation = {
        "$set": set_fields,
        "$setOnInsert": {
            "created_at": now,
        },
    }
    await collection.update_one(query_filter, update_operation, upsert=True)


async def get_latest_observation(
    collection: AsyncCollection[ProductObservationDocument],
    *,
    full_url: str,
) -> ProductObservationDocument | None:
    return await collection.find_one(
        {"full_url": full_url}, sort=[("timestamp", DESCENDING)]
    )


async def insert_observation(
    collection: AsyncCollection[ProductObservationDocument],
    product: ScrapedProduct,
) -> None:
    document: ProductObservationDocument = {
        "full_url": product.full_url,
        "price": product.price,
        "is_on_sale": product.is_on_sale,
        "stock_status": product.stock_status,
        "timestamp": product.scraped_at,
    }
    await collection.insert_one(document)
