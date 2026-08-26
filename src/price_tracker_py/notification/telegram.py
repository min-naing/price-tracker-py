import json
from contextlib import asynccontextmanager

import httpx

from price_tracker_py.config.settings import TelegramConfig
from price_tracker_py.util.retry import RetryOptions, with_retry

MAX_ATTEMPTS = 3
BASE_DELAY = 1.0


class TelegramRateLimitError(Exception):
    def __init__(self, retry_after: float | None) -> None:
        self.retry_after = retry_after

        if retry_after is None:
            message = "Telegram rate limited without retry_after."
        else:
            message = f"Telegram rate limited. Retry after {retry_after} seconds."

        super().__init__(message)


class TelegramSendHttpError(Exception):
    def __init__(
        self,
        status_code: int,
        response_body: str,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body

        super().__init__(
            f"Telegram send failed with status {status_code}: "
            f"{response_body or 'No response body'}"
        )


class TelegramSendFailError(Exception):
    pass


def _parse_retry_after(response_body: str) -> float | None:
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError, TypeError:
        return None

    if not isinstance(parsed, dict):
        return None

    parameters = parsed.get("parameters")

    if not isinstance(parameters, dict):
        return None

    retry_after = parameters.get("retry_after")

    if type(retry_after) is int:
        return float(retry_after)

    return None


def _should_retry(error: Exception) -> bool:
    if isinstance(error, TelegramRateLimitError):
        return True

    if isinstance(error, TelegramSendHttpError):
        return 500 <= error.status_code < 600

    return isinstance(error, httpx.RequestError)


def _get_delay(
    attempt: int,
    error: Exception,
    base_delay: float,
) -> float:
    if isinstance(error, TelegramRateLimitError) and error.retry_after is not None:
        return error.retry_after + base_delay

    return base_delay * 2 ** (attempt - 1)


@asynccontextmanager
async def _get_client(
    client: httpx.AsyncClient | None,
):
    if client is not None:
        yield client
        return

    async with httpx.AsyncClient() as new_client:
        yield new_client


async def send_telegram_alert(
    message: str,
    config: TelegramConfig,
    client: httpx.AsyncClient | None = None,
) -> None:

    url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"

    async with _get_client(client) as http_client:

        async def post_send_message() -> None:
            data = {
                "chat_id": config.chat_id,
                "text": message,
            }
            response = await http_client.post(url=url, json=data)
            response_body = response.text

            if response.status_code == httpx.codes.OK:
                return

            if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                retry_after = _parse_retry_after(response_body)

                raise TelegramRateLimitError(retry_after)

            raise TelegramSendHttpError(
                response.status_code,
                response_body,
            )

        try:
            await with_retry(
                post_send_message,
                options=RetryOptions(
                    max_attempts=MAX_ATTEMPTS,
                    base_delay=BASE_DELAY,
                    get_delay=_get_delay,
                    retry_if=_should_retry,
                ),
            )
        except (
            TelegramRateLimitError,
            TelegramSendHttpError,
            httpx.RequestError,
        ) as ex:
            raise TelegramSendFailError(
                f"Telegram send failed after {MAX_ATTEMPTS} attempts",
            ) from ex
