"""
GitHub Actions cron job entry point
Runs every 15 minutes to check sources and post new content
"""
import asyncio
import sys
from bot.news_publisher import NewsPublisher
from config import Config, ConfigurationError
from utils.logger import setup_logger, get_logger


async def main():
    """Main entry point for cron execution"""
    # Setup logger
    logger = setup_logger(__name__, level=Config.LOG_LEVEL)
    logger.info("=" * 60)
    logger.info("UCG News Bot - Cron Run")
    logger.info("=" * 60)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables or .env file")
        sys.exit(1)

    # Initialize and run publisher
    try:
        publisher = NewsPublisher(
            bot_token=Config.DISCORD_BOT_TOKEN,
            channel_name=Config.CHANNEL_NAME,
            database_path=Config.DATABASE_PATH
        )

        await publisher.run()

        # Give asyncio time to clean up any pending tasks/connections
        await asyncio.sleep(0.25)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Cron run complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
