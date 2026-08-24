import re


def parse_price(raw: str) -> float:
    cleaned = re.sub(r"[^0-9.]", "", raw)

    try:
        return float(cleaned)
    except (ValueError, OverflowError) as ex:
        raise ValueError(f"Could not parse price from: {raw!r}") from ex
