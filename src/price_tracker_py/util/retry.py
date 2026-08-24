import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T")


class OnRetry(Protocol):
    def __call__(self, attempt: int, error: Exception): ...


class GetDelay(Protocol):
    def __call__(self, attempt: int, error: Exception) -> float: ...


@dataclass(frozen=True)
class RetryOptions:
    base_delay: float = 1.0
    max_attempts: int = 3
    on_retry: OnRetry | None = None
    get_delay: GetDelay | None = None


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    options: RetryOptions,
) -> T:

    for attempt in range(1, options.max_attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            if attempt == options.max_attempts:
                raise

            if options.on_retry is not None:
                options.on_retry(attempt, exc)

            if options.get_delay is not None:
                wait = options.get_delay(attempt, exc)
            else:
                wait = options.base_delay * 2 ** (attempt - 1)

            await asyncio.sleep(wait)

    raise AssertionError("Retry loop exited unexpectedly")
