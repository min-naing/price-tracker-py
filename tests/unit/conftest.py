from datetime import UTC, datetime

import pytest

from price_tracker_py.db.document import ProductObservationDocument
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.model.stock_status import StockStatus


@pytest.fixture
def product_observation_document(
    scraped_product: ScrapedProduct,
) -> ProductObservationDocument:
    return {
        "timestamp": datetime.now(UTC),
        "full_url": scraped_product.full_url,
        "is_on_sale": False,
        "price": 10.99,
        "stock_status": StockStatus.IN_STOCK,
    }
