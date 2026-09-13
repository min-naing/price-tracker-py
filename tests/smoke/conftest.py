from collections.abc import AsyncIterator

import pytest_asyncio
from dotenv import load_dotenv

from price_tracker_py.config.settings import load_mongo_config
from price_tracker_py.db.mongodb import MongoDB

load_dotenv()


@pytest_asyncio.fixture
async def db() -> AsyncIterator[MongoDB]:
    config = load_mongo_config()
    db = MongoDB(config)

    try:
        await db.connect()
        yield db
    finally:
        await db.close()
