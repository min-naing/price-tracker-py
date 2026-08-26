import json

import httpx
import pytest

from price_tracker_py.config.settings import TelegramConfig
from price_tracker_py.notification.telegram import (
    TelegramRateLimitError,
    TelegramSendFailError,
    TelegramSendHttpError,
    _get_delay,
    _parse_retry_after,
    _should_retry,
    send_telegram_alert,
)


@pytest.mark.parametrize(
    ("response_body", "expected"),
    [
        ('{"parameters": {"retry_after": 15}}', 15.0),
        ('{"parameters": {"retry_after": 10}}', 10.0),
        ('{"parameters": {}}', None),
        ('{"parameters": null}', None),
        ('{"parameters": "invalid"}', None),
        ("{}", None),
        ("invalid json", None),
        ("[]", None),
        ('{"parameters": []}', None),
        ('{"parameters": {"retry_after": "5"}}', None),
        ('{"parameters": {"retry_after": true}}', None),
        ('{"parameters": {"retry_after": false}}', None),
        ('{"parameters": {"retry_after": null}}', None),
        ('{"parameters": {"retry_after": 5.5}}', None),
    ],
)
def test_parse_retry_after(
    response_body: str,
    expected: float | None,
) -> None:
    result = _parse_retry_after(response_body)

    assert result == expected


@pytest.mark.parametrize(
    ("attempt", "base_delay", "expected"),
    [
        (1, 1.0, 1.0),
        (2, 1.0, 2.0),
        (3, 1.0, 4.0),
        (1, 2.0, 2.0),
        (2, 2.0, 4.0),
        (3, 2.0, 8.0),
    ],
)
def test_get_delay_uses_exponential_backoff(
    attempt: int,
    base_delay: float,
    expected: float,
) -> None:
    error = ValueError("temporary error")
    assert _get_delay(attempt, error, base_delay) == expected


def test_get_delay_uses_retry_after_for_rate_limit() -> None:
    error = TelegramRateLimitError(retry_after=5.0)
    result = _get_delay(
        attempt=1,
        error=error,
        base_delay=1.0,
    )

    assert result == 6.0


def test_get_delay_uses_base_delay_when_retry_after_is_none() -> None:
    error = TelegramRateLimitError(retry_after=None)

    result = _get_delay(
        attempt=2,
        error=error,
        base_delay=2.0,
    )

    assert result == 4.0


def test_should_retry_rate_limit_error() -> None:
    error = TelegramRateLimitError(retry_after=5.0)
    assert _should_retry(error) is True


@pytest.mark.parametrize(
    "status_code",
    [500, 501, 502, 503, 504, 599],
)
def test_should_retry_server_error(status_code: int) -> None:
    error = TelegramSendHttpError(
        status_code=status_code,
        response_body="server error",
    )
    assert _should_retry(error) is True


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 405, 422],
)
def test_should_not_retry_client_error(status_code: int) -> None:
    error = TelegramSendHttpError(
        status_code=status_code,
        response_body="client error",
    )

    assert _should_retry(error) is False


def test_should_retry_request_error() -> None:
    request = httpx.Request(
        "POST",
        "https://api.telegram.org",
    )

    error = httpx.RequestError(
        "connection failed",
        request=request,
    )

    assert _should_retry(error) is True


@pytest.mark.parametrize(
    "error",
    [
        ValueError("bad value"),
        TypeError("bad type"),
        KeyError("missing key"),
    ],
)
def test_should_not_retry_unexpected_error(error: Exception) -> None:
    assert _should_retry(error) is False


@pytest.mark.asyncio
async def test_send_telegram_alert_succeeds(
    telegram_config: TelegramConfig,
) -> None:

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "ok": True,
                "result": {},
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await send_telegram_alert(
            "Hello",
            config=telegram_config,
            client=client,
        )


@pytest.mark.asyncio
async def test_send_telegram_alert_sends_correct_request(
    telegram_config: TelegramConfig,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"

        assert request.url.path.endswith("/sendMessage")

        data = json.loads(request.content)

        assert data == {
            "chat_id": "123456",
            "text": "Hello",
        }

        return httpx.Response(
            status_code=200,
            json={"ok": True},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await send_telegram_alert(
            "Hello",
            config=telegram_config,
            client=client,
        )


@pytest.mark.asyncio
async def test_send_telegram_alert_does_not_retry_bad_request(
    telegram_config: TelegramConfig,
) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts

        attempts += 1

        return httpx.Response(
            status_code=400,
            json={
                "ok": False,
                "description": "Bad Request",
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        with pytest.raises(TelegramSendFailError):
            await send_telegram_alert(
                "Hello",
                config=telegram_config,
                client=client,
            )

    assert attempts == 1


@pytest.mark.asyncio
async def test_send_telegram_alert_retries_server_error(
    telegram_config: TelegramConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(
        "price_tracker_py.util.retry.asyncio.sleep",
        fake_sleep,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts

        attempts += 1

        if attempts == 1:
            return httpx.Response(
                status_code=500,
                json={
                    "ok": False,
                    "description": "Internal Server Error",
                },
            )

        return httpx.Response(
            status_code=200,
            json={
                "ok": True,
                "result": {},
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await send_telegram_alert(
            "Hello",
            config=telegram_config,
            client=client,
        )

    assert attempts == 2
    assert sleep_calls == [1.0]


@pytest.mark.asyncio
async def test_send_telegram_alert_retries_rate_limit(
    telegram_config: TelegramConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    sleep_calls: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    monkeypatch.setattr(
        "price_tracker_py.util.retry.asyncio.sleep",
        fake_sleep,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts

        attempts += 1

        if attempts == 1:
            return httpx.Response(
                status_code=httpx.codes.TOO_MANY_REQUESTS,
                json={
                    "ok": False,
                    "parameters": {
                        "retry_after": 5,
                    },
                },
            )

        return httpx.Response(
            status_code=httpx.codes.OK,
            json={
                "ok": True,
                "result": {},
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await send_telegram_alert(
            "Hello",
            config=telegram_config,
            client=client,
        )

    assert attempts == 2
    assert sleep_calls == [6.0]
