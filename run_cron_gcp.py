"""
GCP Cloud Run cron job entry point
Runs every 15 minutes to check sources and post new content
Includes Cloud Storage integration for database persistence
"""
import asyncio
import sys
from bot.news_publisher import NewsPublisher
from bot.storage import download_database_from_gcs, upload_database_to_gcs, is_gcs_enabled
from config import Config, ConfigurationError
from utils.logger import setup_logger


async def main():
    """Main entry point for GCP Cloud Run execution"""
    # Setup logger
    logger = setup_logger(__name__, level=Config.LOG_LEVEL)
    logger.info("=" * 60)
    logger.info("UCG News Bot - GCP Cloud Run")
    logger.info("=" * 60)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables")
        sys.exit(1)

    # Download database from Cloud Storage
    if is_gcs_enabled():
        logger.info("Downloading database from Cloud Storage...")
        download_database_from_gcs(Config.DATABASE_PATH)
    else:
        logger.warning("GCS_BUCKET_NAME not configured - database will not persist!")

    # Initialize and run publisher
    try:
        publisher = NewsPublisher(
            bot_token=Config.DISCORD_BOT_TOKEN,
            channel_name=Config.CHANNEL_NAME,
            database_path=Config.DATABASE_PATH
        )

        await publisher.run()

        # Upload database to Cloud Storage
        if is_gcs_enabled():
            logger.info("Uploading database to Cloud Storage...")
            upload_database_to_gcs(Config.DATABASE_PATH)

        # Give asyncio time to clean up any pending tasks/connections
        await asyncio.sleep(0.25)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)

        # Still try to upload database even on error (preserve state)
        if is_gcs_enabled():
            logger.info("Attempting to upload database despite error...")
            try:
                upload_database_to_gcs(Config.DATABASE_PATH)
            except Exception as upload_error:
                logger.error(f"Failed to upload database after error: {upload_error}")

        sys.exit(1)

    logger.info("GCP Cloud Run execution complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
