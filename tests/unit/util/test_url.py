import pytest

from price_tracker_py.util.url import normalize_url


@pytest.mark.parametrize(
    ("base_url", "raw_url", "expected"),
    [
        (
            "https://example.com",
            "/product/1",
            "https://example.com/product/1",
        ),
        (
            "https://example.com",
            "  /product/2  ",
            "https://example.com/product/2",
        ),
        (
            "https://example.com",
            "/product/3#reviews",
            "https://example.com/product/3",
        ),
        (
            "https://example.com",
            "/product/4/",
            "https://example.com/product/4",
        ),
        (
            "https://example.com",
            "https://other.com/product",
            "https://other.com/product",
        ),
    ],
)
def test_normalize_url(
    base_url: str,
    raw_url: str,
    expected: str,
) -> None:
    result = normalize_url(base_url, raw_url)

    assert result == expected
