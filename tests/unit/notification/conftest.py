import pytest

from price_tracker_py.config.settings import TelegramConfig


@pytest.fixture
def telegram_config() -> TelegramConfig:
    return TelegramConfig(
        bot_token="test-bot-token",
        chat_id="123456",
    )
