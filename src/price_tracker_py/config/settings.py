import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MongoConfig:
    uri: str
    database_name: str


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass(frozen=True)
class BackblazeB2Config:
    region: str
    end_point: str
    key_id: str
    app_key: str
    bucket_name: str


@dataclass(frozen=True)
class ScraperConfig:
    navigation_timeout_ms: float
    element_timeout_ms: float

    max_rate_limit_retries: int
    rate_limit_backoff_seconds: float

    max_consecutive_scrape_failures: int
    page_failure_backoff_seconds: float

    fail_rate_threshold: float
    min_items_before_rate_check: int


@dataclass(frozen=True)
class AppConfig:
    scraper: ScraperConfig
    mongodb: MongoConfig
    telegram: TelegramConfig
    backblaze_b2: BackblazeB2Config


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_telegram_config() -> TelegramConfig:
    return TelegramConfig(
        bot_token=_require_env("TELEGRAM_BOT_TOKEN"),
        chat_id=_require_env("TELEGRAM_CHAT_ID"),
    )


def load_mongo_config() -> MongoConfig:
    return MongoConfig(
        uri=_require_env("MONGODB_URI"), database_name=_require_env("MONGODB_DATABASE")
    )


def load_backblaze_b2_config() -> BackblazeB2Config:
    return BackblazeB2Config(
        region=_require_env("B2_REGION"),
        end_point=_require_env("B2_ENDPOINT"),
        key_id=_require_env("B2_KEY_ID"),
        app_key=_require_env("B2_APP_KEY"),
        bucket_name=_require_env("B2_BUCKET_NAME"),
    )


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)), base=10)


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


_config: AppConfig | None = None


def load_config() -> AppConfig:
    global _config

    if _config is not None:
        return _config

    _config = AppConfig(
        mongodb=load_mongo_config(),
        telegram=load_telegram_config(),
        backblaze_b2=load_backblaze_b2_config(),
        scraper=ScraperConfig(
            navigation_timeout_ms=_env_float(
                "SCRAPER_NAVIGATION_TIMEOUT_MS", 30_000
            ),  # frmt: skip
            element_timeout_ms=_env_float(
                "SCRAPER_ELEMENT_TIMEOUT_MS", 5_000
            ),  # frmt: skip
            max_rate_limit_retries=_env_int(
                "SCRAPER_MAX_RATE_LIMIT_RETRIES", 5
            ),  # frmt: skip
            rate_limit_backoff_seconds=_env_float(
                "SCRAPER_RATE_LIMIT_BACKOFF_SECONDS", 10
            ),  # frmt: skip
            max_consecutive_scrape_failures=_env_int(
                "SCRAPER_MAX_CONSECUTIVE_SCRAPE_FAILURES", 3
            ),  # frmt: skip
            page_failure_backoff_seconds=_env_float(
                "SCRAPER_PAGE_FAILURE_BACKOFF_SECONDS", 3
            ),  # frmt: skip
            fail_rate_threshold=_env_float(
                "SCRAPER_FAIL_RATE_THRESHOLD", 0.3
            ),  # frmt: skip
            min_items_before_rate_check=_env_int(
                "SCRAPER_MIN_ITEMS_BEFORE_RATE_CHECK", 5
            ),  # frmt: skip
        ),
    )
    return _config


def get_config() -> AppConfig:
    return _config if _config is not None else load_config()


def reset_config() -> None:
    global _config
    _config = None
