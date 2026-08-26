import pytest

from price_tracker_py.util.retry import RetryOptions, with_retry


@pytest.mark.asyncio
async def test_with_retry_returns_result_without_retry() -> None:
    async def operation() -> str:
        return "success"

    result = await with_retry(
        operation,
        options=RetryOptions(),
    )

    assert result == "success"


@pytest.mark.asyncio
async def test_with_retry_retries_after_failure() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts

        attempts += 1

        if attempts == 1:
            raise ValueError("temporary failure")

        return "success"

    result = await with_retry(
        operation, options=RetryOptions(base_delay=0, max_attempts=3)
    )

    assert result == "success"
    assert attempts == 2


@pytest.mark.asyncio
async def test_with_retry_raises_after_max_attempts() -> None:
    attempts = 0

    async def operation() -> None:
        nonlocal attempts

        attempts += 1
        raise ValueError("always fails")

    with pytest.raises(ValueError, match="always fails"):
        await with_retry(
            operation,
            options=RetryOptions(
                max_attempts=3,
                base_delay=0,
            ),
        )

    assert attempts == 3


@pytest.mark.asyncio
async def test_with_retry_stops_when_retry_if_returns_false() -> None:
    attempts = 0

    async def operation() -> None:
        nonlocal attempts

        attempts += 1
        raise ValueError("do not retry")

    def retry_if(error: Exception) -> bool:
        return False

    with pytest.raises(ValueError, match="do not retry"):
        await with_retry(
            operation,
            options=RetryOptions(
                max_attempts=3,
                base_delay=0,
                retry_if=retry_if,
            ),
        )

    assert attempts == 1
