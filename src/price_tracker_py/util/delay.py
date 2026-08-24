import asyncio
import random


async def polite_delay(
    base_seconds: float = 1.5,
    max_jitter_seconds: float = 0.5,
) -> None:
    jitter = random.uniform(0, max_jitter_seconds)
    await asyncio.sleep(base_seconds + jitter)


def calculate_exponential_backoff(
    *,
    attempt: int,
    base_seconds: float,
) -> float:
    return base_seconds * (2 ** (attempt - 1))
