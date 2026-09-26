import asyncio
import logging
import time
from datetime import UTC, datetime

from dotenv import load_dotenv

from price_tracker_py.util.delay import polite_delay

from .config.settings import get_config
from .db.mongodb import MongoDB
from .export.csv_exporter import export_to_csv
from .notification.telegram import build_alert_messages, send_telegram_alert
from .scraper.ecommerce import scrape_product_list
from .service.product_service import sync_product
from .storage.b2 import create_b2_client, upload_csv

# boto3.set_stream_logger(name="botocore", level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    pipeline_start = time.perf_counter()
    try:
        logger.info("🚀 Starting pipeline...")
        config = get_config()

        logger.info("📦 Step 1: Scraping...")
        stage_start = time.perf_counter()

        scraped_products = await scrape_product_list(config=config.scraper, max_pages=3)

        logger.info(
            "📦 Scraping completed in %.2f seconds",
            time.perf_counter() - stage_start,
        )

        logger.info("🔁 Step 2: Syncing to MongoDB...")
        stage_start = time.perf_counter()

        db = MongoDB(config=config.mongodb)
        try:
            await db.connect()

            alert_messages: list[str] = []
            for product in scraped_products:
                alert_message = await sync_product(
                    product, db.products, db.product_observations
                )

                if alert_message is not None:
                    alert_messages.append(alert_message)

        finally:
            await db.close()
            logger.info("🛑 Closed MongoDB")

        logger.info(
            "🔁 MongoDB sync completed in %.2f seconds",
            time.perf_counter() - stage_start,
        )

        logger.info("📨 Step 3: Sending Telegram alerts...")
        stage_start = time.perf_counter()

        messages = build_alert_messages(alert_messages)
        for message in messages:
            await send_telegram_alert(message, config=config.telegram)
            await polite_delay(base_seconds=2)

        logger.info(
            "📨 Telegram stage completed in %.2f seconds",
            time.perf_counter() - stage_start,
        )

        logger.info("📄 Step 4: Exporting CSV...")
        stage_start = time.perf_counter()

        csv_data = export_to_csv(scraped_products)

        logger.info(
            "📄 CSV export completed in %.2f seconds",
            time.perf_counter() - stage_start,
        )

        logger.info("☁️ Step 5: Uploading to B2...")
        stage_start = time.perf_counter()

        b2_client = create_b2_client()
        now = datetime.now(UTC)
        object_key = f"products/{now:%Y-%m-%d}/products-{now:%Y%m%dT%H%M%SZ}.csv"
        upload_csv(
            client=b2_client,
            bucket_name=config.backblaze_b2.bucket_name,
            object_key=object_key,
            csv_data=csv_data,
        )

        logger.info(
            "☁️ B2 upload completed in %.2f seconds",
            time.perf_counter() - stage_start,
        )

        logger.info(
            "✅ Pipeline completed successfully in %.2f seconds",
            time.perf_counter() - pipeline_start,
        )
    except Exception:
        logger.exception(
            "❌ Pipeline failed after %.2f seconds",
            time.perf_counter() - pipeline_start,
        )
        raise


def main() -> None:
    load_dotenv()

    asyncio.run(run())


if __name__ == "__main__":
    main()
