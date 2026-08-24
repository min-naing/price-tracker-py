from datetime import datetime
from typing import TypedDict

from price_tracker_py.model.scraped_product import ProductType, StockStatus


class ProductDocument(TypedDict):
    _id: str
    name: str
    img_url: str | None
    product_type: ProductType
    created_at: datetime
    updated_at: datetime


class ProductUpdateFields(TypedDict):
    name: str
    img_url: str | None
    product_type: ProductType
    updated_at: datetime


class ProductObservationDocument(TypedDict):
    timestamp: datetime
    full_url: str
    price: float
    is_on_sale: bool
    stock_status: StockStatus
