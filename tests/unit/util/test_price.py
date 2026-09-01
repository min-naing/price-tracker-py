import pytest

from price_tracker_py.util.price import parse_price


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        ("$12.34", 12.34),
        (" $15.94 ", 15.94),
        ("$0.99", 0.99),
        ("100", 100.0),
    ],
)
def test_price_returns_valid_price(price: str, expected: float) -> None:
    assert parse_price(price) == expected


@pytest.mark.parametrize(
    ("price"),
    [
        "drgd@#",
        " %$#@! ",
        "",
        "   ",
    ],
)
def test_price_raises_for_invalid_price(price: str) -> None:
    with pytest.raises(ValueError):
        parse_price(price)
