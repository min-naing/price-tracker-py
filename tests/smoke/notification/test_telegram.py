import pytest

from price_tracker_py.config.settings import load_telegram_config
from price_tracker_py.notification.telegram import send_telegram_alert


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_telegram_send_alert_smoke() -> None:
    config = load_telegram_config()

    await send_telegram_alert(
        message="hello testing",
        config=config,
    )
