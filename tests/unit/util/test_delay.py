from unittest.mock import AsyncMock, patch

import pytest

from price_tracker_py.util.delay import calculate_exponential_backoff, polite_delay


@pytest.mark.parametrize(
    ("base_seconds", "max_jitter_seconds", "jitter", "expected_delay"),
    [
        (1.5, 0.5, 0.0, 1.5),
        (1.5, 0.5, 0.2, 1.7),
        (1.5, 0.5, 0.5, 2.0),
        (2.0, 1.0, 0.3, 2.3),
    ],
)
@pytest.mark.asyncio
async def test_polite_delay(
    base_seconds: float,
    max_jitter_seconds: float,
    jitter: float,
    expected_delay: float,
) -> None:
    with (
        patch(
            "price_tracker_py.util.delay.random.uniform",
            return_value=jitter,
        ) as mock_uniform,
        patch(
            "price_tracker_py.util.delay.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep,
    ):
        await polite_delay(base_seconds, max_jitter_seconds)

    mock_uniform.assert_called_once_with(0, max_jitter_seconds)
    mock_sleep.assert_awaited_once_with(expected_delay)


@pytest.mark.parametrize(
    ("attempt", "base_seconds", "expected"),
    [
        (1, 3.0, 3.0),
        (2, 3.0, 6.0),
        (3, 3.0, 12.0),
        (4, 3.0, 24.0),
    ],
)
def test_calculate_exponential_backoff(
    attempt: int,
    base_seconds: float,
    expected: float,
) -> None:
    assert (
        calculate_exponential_backoff(attempt=attempt, base_seconds=base_seconds)
        == expected
    )


@pytest.mark.parametrize("attempt", [0, -1, -5])
def test_calculate_exponential_backoff_rejects_invalid_attempt(
    attempt: int,
) -> None:
    with pytest.raises(ValueError):
        calculate_exponential_backoff(attempt=attempt, base_seconds=3.0)
