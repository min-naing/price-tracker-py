import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T")


class OnRetry(Protocol):
    def __call__(self, attempt: int, error: Exception) -> None: ...


class GetDelay(Protocol):
    def __call__(
        self,
        attempt: int,
        error: Exception,
        base_delay: float,
    ) -> float: ...


class RetryIf(Protocol):
    def __call__(self, error: Exception) -> bool: ...


@dataclass(frozen=True)
class RetryOptions:
    base_delay: float = 1.0
    max_attempts: int = 3
    on_retry: OnRetry | None = None
    get_delay: GetDelay | None = None
    retry_if: RetryIf | None = None


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    options: RetryOptions,
) -> T:

    for attempt in range(1, options.max_attempts + 1):
        try:
            return await fn()
        except Exception as ex:
            should_retry = options.retry_if is None or options.retry_if(ex)

            if not should_retry or attempt == options.max_attempts:
                raise

            if options.on_retry is not None:
                options.on_retry(attempt, ex)

            if options.get_delay is not None:
                wait = options.get_delay(
                    attempt,
                    ex,
                    options.base_delay,
                )
            else:
                wait = options.base_delay * 2 ** (attempt - 1)

            await asyncio.sleep(wait)

    raise AssertionError("Retry loop exited unexpectedly")
