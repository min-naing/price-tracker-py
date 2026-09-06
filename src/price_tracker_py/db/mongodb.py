import logging
from typing import ClassVar

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)
from pymongo.server_api import ServerApi

from price_tracker_py.config.settings import MongoConfig
from price_tracker_py.db.document import ProductDocument, ProductObservationDocument

logger = logging.getLogger(__name__)


class MongoDB:
    PRODUCTS_COLLECTION_NAME: ClassVar[str] = "products"
    PRODUCT_OBSERVATIONS_COLLECTION_NAME: ClassVar[str] = "product_observations"

    def __init__(self, config: MongoConfig) -> None:
        self._client = AsyncMongoClient(
            config.uri,
            server_api=ServerApi(
                version="1",
                strict=True,
                deprecation_errors=True,
            ),
            tz_aware=True,
        )
        self._database = self._client.get_database(config.database_name)

    @property
    def database(self) -> AsyncDatabase:
        return self._database

    @property
    def products(self) -> AsyncCollection[ProductDocument]:
        return self._database[self.PRODUCTS_COLLECTION_NAME]

    @property
    def product_observations(self) -> AsyncCollection[ProductObservationDocument]:
        return self._database[self.PRODUCT_OBSERVATIONS_COLLECTION_NAME]

    async def connect(self) -> None:
        try:
            await self._client.admin.command("ping")
            await self._initialize()

            logger.info("✅ Connected to MongoDB")

        except ConfigurationError:
            logger.exception(
                "❌ MongoDB Configuration Error: Verify your connection URI."
            )

        except ServerSelectionTimeoutError:
            logger.exception(
                "❌ MongoDB Timeout Error: The server appears to be down or unreachable."
            )

        except ConnectionFailure:
            logger.exception(
                "❌ MongoDB Connection Failure: Could not establish network bridge."
            )

        except PyMongoError:
            logger.exception("❌ General PyMongo Error occurred.")

        except Exception:
            logger.exception("❌ An unexpected application error occurred.")

    async def _initialize(self) -> None:
        await self._create_product_observations_timeseries_collection()
        await self._create_indexes()

    async def _create_product_observations_timeseries_collection(self) -> None:
        collection_names = await self._database.list_collection_names(
            filter={"name": self.PRODUCT_OBSERVATIONS_COLLECTION_NAME}
        )

        if self.PRODUCT_OBSERVATIONS_COLLECTION_NAME in collection_names:
            return

        timeseries_options = {
            "timeField": "timestamp",
            "metaField": "full_url",
            "granularity": "minutes",
        }
        await self._database.create_collection(
            self.PRODUCT_OBSERVATIONS_COLLECTION_NAME,
            timeseries=timeseries_options,
            expireAfterSeconds=60 * 60 * 24 * 30,
        )
        logger.info(
            "Created %s time-series collection",
            self.PRODUCT_OBSERVATIONS_COLLECTION_NAME,
        )

    async def _create_indexes(self) -> None:
        # Add only indexes required by actual query patterns.
        pass

    async def close(self) -> None:
        await self._client.close()
