from price_tracker_py.scraper.exception import (
    TooManyItemFailuresError,
)


def check_item_failure_rate(
    *,
    page_number: int,
    item_fail_count: int,
    item_total_count: int,
    minimum_items: int,
    threshold: float,
) -> None:
    if item_total_count < minimum_items:
        return

    fail_rate = item_fail_count / item_total_count

    if fail_rate > threshold:
        raise TooManyItemFailuresError(
            f"Too many scrape failures on page {page_number}: "
            f"{item_fail_count}/{item_total_count} items failed "
            f"(failure rate: {fail_rate:.1%})"
        )
