import pytest

from price_tracker_py.scraper.exception import (
    TooManyItemFailuresError,
)
from price_tracker_py.scraper.failure import (
    check_item_failure_rate,
)


def test_does_not_check_failure_rate_when_too_few_items() -> None:
    check_item_failure_rate(
        page_number=1,
        item_fail_count=4,
        item_total_count=4,
        minimum_items=5,
        threshold=0.3,
    )


def test_does_not_raise_when_failure_rate_is_at_threshold() -> None:
    check_item_failure_rate(
        page_number=1,
        item_fail_count=3,
        item_total_count=10,
        minimum_items=5,
        threshold=0.3,
    )


def test_raises_when_failure_rate_is_above_threshold() -> None:
    with pytest.raises(TooManyItemFailuresError):
        check_item_failure_rate(
            page_number=1,
            item_fail_count=4,
            item_total_count=10,
            minimum_items=5,
            threshold=0.3,
        )


def test_error_contains_page_and_failure_information() -> None:
    with pytest.raises(
        TooManyItemFailuresError,
        match=r"page 3: 4/10 items failed",
    ):
        check_item_failure_rate(
            page_number=3,
            item_fail_count=4,
            item_total_count=10,
            minimum_items=5,
            threshold=0.3,
        )
