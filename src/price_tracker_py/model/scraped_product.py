from dataclasses import dataclass
from datetime import datetime

from price_tracker_py.model.product_type import ProductType
from price_tracker_py.model.stock_status import StockStatus


@dataclass(frozen=True)
class ScrapedProduct:
    name: str
    full_url: str
    img_url: str | None

    price: float
    is_on_sale: bool

    product_type: ProductType
    stock_status: StockStatus

    scraped_at: datetime
