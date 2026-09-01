import re
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, call

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from price_tracker_py.config.settings import ScraperConfig
from price_tracker_py.model.product_type import ProductType
from price_tracker_py.model.scraped_product import ScrapedProduct
from price_tracker_py.model.stock_status import StockStatus
from price_tracker_py.scraper.ecommerce import (
    URL,
    PriceInfo,
    _get_next_page_url,
    _parse_price_info,
    _raise_if_rate_limited,
    _scrape_page,
    _scrape_product,
    _should_stop_after_scrape_failure,
)
from price_tracker_py.scraper.exception import (
    RateLimitedError,
    ScraperStructureError,
    TooManyItemFailuresError,
)


@pytest.mark.parametrize(
    ("consecutive_failures", "expected"),
    [(0, False), (1, False), (3, True), (4, True)],
)
def test_should_stop_after_scrape_failure(
    consecutive_failures: int,
    expected: bool,
) -> None:
    result = _should_stop_after_scrape_failure(
        consecutive_failures=consecutive_failures,
        max_consecutive_page_failures=3,
    )

    assert result == expected


def test_raise_if_rate_limited() -> None:
    response = Mock()
    response.status = 429
    response.url = "https://example.com"

    with pytest.raises(RateLimitedError):
        _raise_if_rate_limited(response)


def test_does_not_rate_when_response_is_none() -> None:
    _raise_if_rate_limited(None)


@pytest.mark.parametrize(
    "status",
    [200, 400, 404, 500],
)
def test_does_not_rate_when_response_is_not_rate_limited(status: int) -> None:
    response = Mock()
    response.status = status
    response.url = "https://example.com"

    _raise_if_rate_limited(response)


@pytest.mark.asyncio
async def test_get_next_page_url_with_no_next_link() -> None:
    page = Mock()

    locator = page.get_by_role.return_value.first

    locator.count = AsyncMock(return_value=0)

    result = await _get_next_page_url(page)

    assert result is None

    page.get_by_role.assert_called_once_with("link", name="→")

    locator.count.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_next_page_url_returns_href_when_next_link_exists() -> None:
    page = Mock()

    locator = page.get_by_role.return_value.first

    locator.count = AsyncMock(return_value=1)

    locator.get_attribute = AsyncMock(return_value="/page/2")

    result = await _get_next_page_url(page)

    assert result == "/page/2"

    page.get_by_role.assert_called_once_with("link", name="→")

    locator.count.assert_awaited_once()
    locator.get_attribute.assert_awaited_once_with("href")


@pytest.mark.asyncio
async def test_get_next_page_url_raises_when_href_is_missing() -> None:
    page = Mock()

    locator = page.get_by_role.return_value.first

    locator.count = AsyncMock(return_value=1)

    locator.get_attribute = AsyncMock(return_value=None)

    with pytest.raises(ScraperStructureError):
        await _get_next_page_url(page)

    page.get_by_role.assert_called_once_with("link", name="→")

    locator.count.assert_awaited_once()
    locator.get_attribute.assert_awaited_once_with("href")


@pytest.mark.asyncio
async def test_parse_price_info_returns_sale_price_when_sale_price_is_visible() -> None:
    price_wrapper_locator = Mock()

    ins_locator = price_wrapper_locator.locator.return_value

    ins_locator.is_visible = AsyncMock(return_value=True)

    ins_locator.inner_text = AsyncMock(return_value="$10.12")

    result = await _parse_price_info(price_wrapper=price_wrapper_locator)

    assert result == PriceInfo(price=10.12, is_on_sale=True)

    price_wrapper_locator.locator.assert_called_once_with(
        "ins .woocommerce-Price-amount"
    )

    ins_locator.is_visible.assert_awaited_once()
    ins_locator.inner_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_parse_price_info_has_only_regular_product() -> None:
    price_wrapper_locator = Mock()
    ins_locator = Mock()
    regular_price_wrapper = Mock()

    price_wrapper_locator.locator.side_effect = [
        ins_locator,
        regular_price_wrapper,
    ]

    ins_locator.is_visible = AsyncMock(return_value=False)

    price_locator = regular_price_wrapper.first

    price_locator.inner_text = AsyncMock(return_value="$30.12")

    result = await _parse_price_info(price_wrapper=price_wrapper_locator)

    assert result == PriceInfo(price=30.12, is_on_sale=False)

    price_wrapper_locator_calls = [
        call("ins .woocommerce-Price-amount"),
        call(".woocommerce-Price-amount"),
    ]

    price_wrapper_locator.locator.assert_has_calls(price_wrapper_locator_calls)

    ins_locator.is_visible.assert_awaited_once()
    price_locator.inner_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_parse_price_info_raises_when_price_is_invalid() -> None:
    price_wrapper_locator = Mock()
    ins_locator = Mock()
    regular_price_wrapper = Mock()

    price_wrapper_locator.locator.side_effect = [
        ins_locator,
        regular_price_wrapper,
    ]

    ins_locator.is_visible = AsyncMock(return_value=False)

    price_locator = regular_price_wrapper.first

    price_locator.inner_text = AsyncMock(return_value="invalid price")

    with pytest.raises(ValueError):
        await _parse_price_info(price_wrapper=price_wrapper_locator)


@pytest.mark.asyncio
async def test_scrape_product_returns_in_stock_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_locator = Mock()

    link_result = Mock()
    select_options_link_locator = Mock()
    add_to_cart_link_locator = Mock()

    product_locator.get_by_role.side_effect = [
        link_result,
        select_options_link_locator,
        add_to_cart_link_locator,
    ]

    link_locator = link_result.first
    link_locator.get_attribute = AsyncMock(return_value="/product/2")

    normalize_url_mock = Mock(return_value="https://example.com/product/2")
    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce.normalize_url",
        normalize_url_mock,
    )

    name_locator = link_locator.get_by_role.return_value
    name_locator.inner_text = AsyncMock(return_value="Raw Product Name")

    img_locator = link_locator.locator.return_value.first
    img_locator.get_attribute = AsyncMock(
        return_value="https://example.com/product-image.jpg"
    )

    product_price_wrapper = product_locator.get_by_test_id.return_value
    parse_price_info = AsyncMock(return_value=PriceInfo(price=12.09, is_on_sale=True))

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._parse_price_info",
        parse_price_info,
    )

    select_options_link_locator.is_visible = AsyncMock(return_value=False)
    add_to_cart_link_locator.is_visible = AsyncMock(return_value=True)

    result = await _scrape_product(product_locator)

    assert result.name == "Raw Product Name"
    assert result.price == 12.09
    assert result.is_on_sale is True
    assert result.product_type == ProductType.SIMPLE
    assert result.stock_status == StockStatus.IN_STOCK
    assert result.full_url == "https://example.com/product/2"
    assert result.img_url == "https://example.com/product-image.jpg"
    assert result.scraped_at.tzinfo == UTC

    assert product_locator.get_by_role.call_args_list == [
        call("link"),
        call(
            "link",
            name=re.compile(
                "select options",
                flags=re.IGNORECASE,
            ),
        ),
        call(
            "link",
            name=re.compile(
                "add to cart",
                flags=re.IGNORECASE,
            ),
        ),
    ]

    link_locator.get_attribute.assert_awaited_once_with("href")
    normalize_url_mock.assert_called_once_with(
        URL,
        "/product/2",
    )
    link_locator.get_by_role.assert_called_once_with(
        "heading",
        level=2,
    )
    name_locator.inner_text.assert_awaited_once()
    link_locator.locator.assert_called_once_with("img")
    img_locator.get_attribute.assert_awaited_once_with("src")
    product_locator.get_by_test_id.assert_called_once_with("product-price")
    parse_price_info.assert_awaited_once_with(product_price_wrapper)

    select_options_link_locator.is_visible.assert_awaited_once()
    add_to_cart_link_locator.is_visible.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_product_returns_out_of_stock_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_locator = Mock()

    link_result = Mock()
    select_options_link_locator = Mock()
    add_to_cart_link_locator = Mock()

    product_locator.get_by_role.side_effect = [
        link_result,
        select_options_link_locator,
        add_to_cart_link_locator,
    ]

    link_locator = link_result.first
    link_locator.get_attribute = AsyncMock(return_value="/product/2")

    normalize_url_mock = Mock(return_value="https://example.com/product/2")
    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce.normalize_url",
        normalize_url_mock,
    )

    name_locator = link_locator.get_by_role.return_value
    name_locator.inner_text = AsyncMock(return_value="Raw Product Name")

    img_locator = link_locator.locator.return_value.first
    img_locator.get_attribute = AsyncMock(
        return_value="https://example.com/product-image.jpg"
    )

    product_price_wrapper = product_locator.get_by_test_id.return_value
    parse_price_info = AsyncMock(return_value=PriceInfo(price=30.99, is_on_sale=False))

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._parse_price_info",
        parse_price_info,
    )

    select_options_link_locator.is_visible = AsyncMock(return_value=False)
    add_to_cart_link_locator.is_visible = AsyncMock(return_value=False)

    result = await _scrape_product(product_locator)

    assert result.name == "Raw Product Name"
    assert result.price == 30.99
    assert result.is_on_sale is False
    assert result.product_type == ProductType.SIMPLE
    assert result.stock_status == StockStatus.OUT_OF_STOCK
    assert result.full_url == "https://example.com/product/2"
    assert result.img_url == "https://example.com/product-image.jpg"
    assert result.scraped_at.tzinfo == UTC

    assert product_locator.get_by_role.call_args_list == [
        call("link"),
        call(
            "link",
            name=re.compile(
                "select options",
                flags=re.IGNORECASE,
            ),
        ),
        call(
            "link",
            name=re.compile(
                "add to cart",
                flags=re.IGNORECASE,
            ),
        ),
    ]

    link_locator.get_attribute.assert_awaited_once_with("href")
    normalize_url_mock.assert_called_once_with(URL, "/product/2")
    link_locator.get_by_role.assert_called_once_with(
        "heading",
        level=2,
    )
    name_locator.inner_text.assert_awaited_once()
    link_locator.locator.assert_called_once_with("img")
    img_locator.get_attribute.assert_awaited_once_with("src")
    product_locator.get_by_test_id.assert_called_once_with("product-price")
    parse_price_info.assert_awaited_once_with(product_price_wrapper)

    select_options_link_locator.is_visible.assert_awaited_once()
    add_to_cart_link_locator.is_visible.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_product_returns_variable_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product_locator = Mock()

    link_result = Mock()
    select_options_link_locator = Mock()
    add_to_cart_link_locator = Mock()

    product_locator.get_by_role.side_effect = [
        link_result,
        select_options_link_locator,
        add_to_cart_link_locator,
    ]

    link_locator = link_result.first
    link_locator.get_attribute = AsyncMock(return_value="/product/2")

    normalize_url_mock = Mock(return_value="https://example.com/product/2")
    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce.normalize_url", normalize_url_mock
    )

    name_locator = link_locator.get_by_role.return_value
    name_locator.inner_text = AsyncMock(return_value="Raw Product Name")

    img_locator = link_locator.locator.return_value.first
    img_locator.get_attribute = AsyncMock(
        return_value="https://example.com/product-image.jpg"
    )

    product_price_wrapper = product_locator.get_by_test_id.return_value
    parse_price_info = AsyncMock(return_value=PriceInfo(price=30.99, is_on_sale=False))

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._parse_price_info",
        parse_price_info,
    )

    select_options_link_locator.is_visible = AsyncMock(return_value=True)
    add_to_cart_link_locator.is_visible = AsyncMock(return_value=False)

    result = await _scrape_product(product_locator)

    assert result.name == "Raw Product Name"
    assert result.price == 30.99
    assert result.is_on_sale is False
    assert result.product_type == ProductType.VARIABLE
    assert result.stock_status == StockStatus.UNKNOWN
    assert result.full_url == "https://example.com/product/2"
    assert result.img_url == "https://example.com/product-image.jpg"
    assert result.scraped_at.tzinfo == UTC

    assert product_locator.get_by_role.call_args_list == [
        call("link"),
        call(
            "link",
            name=re.compile(
                "select options",
                flags=re.IGNORECASE,
            ),
        ),
        call(
            "link",
            name=re.compile(
                "add to cart",
                flags=re.IGNORECASE,
            ),
        ),
    ]

    link_locator.get_attribute.assert_awaited_once_with("href")
    normalize_url_mock.assert_called_once_with(URL, "/product/2")
    link_locator.get_by_role.assert_called_once_with(
        "heading",
        level=2,
    )
    name_locator.inner_text.assert_awaited_once()
    link_locator.locator.assert_called_once_with("img")
    img_locator.get_attribute.assert_awaited_once_with("src")
    product_locator.get_by_test_id.assert_called_once_with("product-price")
    parse_price_info.assert_awaited_once_with(product_price_wrapper)

    select_options_link_locator.is_visible.assert_awaited_once()
    add_to_cart_link_locator.is_visible.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_product_raises_when_no_product_url() -> None:
    product_locator = Mock()

    link_locator = product_locator.get_by_role.return_value.first
    link_locator.get_attribute = AsyncMock(return_value=None)

    with pytest.raises(ValueError):
        await _scrape_product(product_locator)

    product_locator.get_by_role.assert_called_once_with("link")
    link_locator.get_attribute.assert_awaited_once_with("href")


@pytest.mark.asyncio
async def test_scrape_page_returns_list_of_scraped_products(
    scraper_config: ScraperConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    product = ScrapedProduct(
        name="product",
        full_url="https://example.com/product/1",
        img_url="https://example.com/product-image.jpg",
        price=30.34,
        is_on_sale=False,
        product_type=ProductType.SIMPLE,
        stock_status=StockStatus.IN_STOCK,
        scraped_at=datetime.now(UTC),
    )

    page = Mock()

    product_list_wrapper = page.get_by_test_id.return_value
    product_list_locator = product_list_wrapper.get_by_role.return_value

    product_list_locator.first.wait_for = AsyncMock()
    product_list_locator.all = AsyncMock(return_value=[product_list_locator])

    scrape_product = AsyncMock(return_value=product)

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._scrape_product",
        scrape_product,
    )

    result = await _scrape_page(
        page=page,
        page_number=1,
        config=scraper_config,
    )

    assert result == [product]

    page.get_by_test_id.assert_called_once_with("product-list")
    product_list_wrapper.get_by_role.assert_called_once_with("listitem")

    product_list_locator.first.wait_for.assert_awaited_once()
    product_list_locator.all.assert_awaited_once()

    scrape_product.assert_awaited_once_with(product_list_locator)


@pytest.mark.asyncio
async def test_scrape_page_when_wait_for_first_product_raises_playwright_timeout_error(
    scraper_config: ScraperConfig,
) -> None:
    page = Mock()

    product_list_wrapper = page.get_by_test_id.return_value
    product_list_locator = product_list_wrapper.get_by_role.return_value

    product_list_locator.first.wait_for = AsyncMock(
        side_effect=PlaywrightTimeoutError("Product list did not appear")
    )

    with pytest.raises(ScraperStructureError):
        await _scrape_page(
            page=page,
            page_number=1,
            config=scraper_config,
        )

    page.get_by_test_id.assert_called_once_with("product-list")
    product_list_wrapper.get_by_role.assert_called_once_with("listitem")

    product_list_locator.first.wait_for.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_page_handles_playwright_timeout_for_individual_product(
    scraper_config: ScraperConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    product = ScrapedProduct(
        name="product",
        full_url="https://example.com/product/1",
        img_url="https://example.com/product-image.jpg",
        price=30.34,
        is_on_sale=False,
        product_type=ProductType.SIMPLE,
        stock_status=StockStatus.IN_STOCK,
        scraped_at=datetime.now(UTC),
    )

    page = Mock()

    product_list_wrapper = page.get_by_test_id.return_value
    product_list_locator = product_list_wrapper.get_by_role.return_value

    product_list_locator.first.wait_for = AsyncMock()
    product_list_locator.all = AsyncMock(
        return_value=[product_list_locator, product_list_locator]
    )

    scrape_product = AsyncMock(
        side_effect=[
            product,
            PlaywrightTimeoutError("Product time out"),
        ]
    )

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._scrape_product",
        scrape_product,
    )

    check_item_failure_rate = Mock()

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce.check_item_failure_rate",
        check_item_failure_rate,
    )

    result = await _scrape_page(
        page=page,
        page_number=1,
        config=scraper_config,
    )

    assert result == [product]

    page.get_by_test_id.assert_called_once_with("product-list")
    product_list_wrapper.get_by_role.assert_called_once_with("listitem")

    product_list_locator.first.wait_for.assert_awaited_once()
    product_list_locator.all.assert_awaited_once()

    # assert scrape_product.await_count == 2
    # or
    assert scrape_product.await_args_list == [
        call(product_list_locator),
        call(product_list_locator),
    ]

    check_item_failure_rate.assert_called_once_with(
        page_number=1,
        item_fail_count=1,
        item_total_count=2,
        minimum_items=scraper_config.min_items_before_rate_check,
        threshold=scraper_config.fail_rate_threshold,
    )


@pytest.mark.asyncio
async def test_scrape_page_raises_when_item_failure_rate_exceeds_threshold(
    scraper_config: ScraperConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    product = ScrapedProduct(
        name="product",
        full_url="https://example.com/product/1",
        img_url="https://example.com/image.jpg",
        price=30.34,
        is_on_sale=False,
        product_type=ProductType.SIMPLE,
        stock_status=StockStatus.IN_STOCK,
        scraped_at=datetime.now(UTC),
    )

    page = Mock()

    product_list_wrapper = page.get_by_test_id.return_value
    product_list_locator = product_list_wrapper.get_by_role.return_value

    product_list_locator.first.wait_for = AsyncMock()
    product_list_locator.all = AsyncMock(
        return_value=[
            product_list_locator,
            product_list_locator,
            product_list_locator,
            product_list_locator,
            product_list_locator,
        ]
    )

    scrape_product = AsyncMock(
        side_effect=[
            product,
            PlaywrightTimeoutError("Product time out"),
            PlaywrightTimeoutError("Product time out"),
        ]
    )

    monkeypatch.setattr(
        "price_tracker_py.scraper.ecommerce._scrape_product",
        scrape_product,
    )

    with pytest.raises(TooManyItemFailuresError):
        await _scrape_page(
            page=page,
            page_number=1,
            config=scraper_config,
        )

    page.get_by_test_id.assert_called_once_with("product-list")
    product_list_wrapper.get_by_role.assert_called_once_with("listitem")

    product_list_locator.first.wait_for.assert_awaited_once()
    product_list_locator.all.assert_awaited_once()

    assert scrape_product.await_count == 3
    # assert scrape_product.await_args_list == [
    #     call(product_list_locator),
    #     call(product_list_locator),
    #     call(product_list_locator),
    # ]
