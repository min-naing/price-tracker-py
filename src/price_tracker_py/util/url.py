from urllib.parse import urldefrag, urljoin


def normalize_url(base_url: str, raw_url: str) -> str:
    """
    Converts a possibly-relative URL (from href or src) into an absolute
    URL using the page's base URL. Strips stray whitespace, trailing
    slashes, and fragment identifiers (#section), since those don't
    change which page/resource the URL points to.

    Examples:
        normalize_url("https://example.com", "/products/widget")
        -> "https://example.com/products/widget"

        normalize_url("https://example.com", "https://example.com/x/")
        -> "https://example.com/x"

        normalize_url("https://example.com", "/products/widget#reviews")
        -> "https://example.com/products/widget"
    """
    cleaned = raw_url.strip()
    absolute = urljoin(base_url, cleaned)
    without_fragment, _fragment = urldefrag(absolute)
    return without_fragment.removesuffix("/")
