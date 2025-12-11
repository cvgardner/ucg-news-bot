"""Multi-Source Link Bot - Main entry point"""
import asyncio
import signal
import sys

from config import Config, ConfigurationError
from bot.database import Database
from bot.scraper import WebScraper
from bot.x_api import XAPIClient
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.discord_bot import LinkBot
from bot.parsers import (
    parse_facebook,
)
from utils.logger import setup_logger, get_logger

# Setup main logger
logger = None


async def initialize_database(db_path: str) -> Database:
    """
    Initialize and connect to the database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Connected Database instance
    """
    logger.info("Initializing database...")
    db = Database(db_path)
    await db.connect()
    await db.initialize_schema()
    logger.info("Database initialized successfully")
    return db


async def cleanup_old_data(db: Database):
    """
    Cleanup old data from the database.

    Args:
        db: Database instance
    """
    logger.info("Cleaning up old data...")
    await db.cleanup_old_posts(days=30)
    logger.info("Cleanup complete")


async def shutdown(bot: LinkBot, db: Database):
    """
    Gracefully shutdown the bot and cleanup resources.

    Args:
        bot: Discord bot instance
        db: Database instance
    """
    logger.info("Shutdown signal received, cleaning up...")

    try:
        # Close bot
        await bot.close()

        # Close database
        await db.close()

        logger.info("Cleanup complete, exiting")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main application entry point"""
    global logger

    # Setup logger
    logger = setup_logger(__name__, level=Config.LOG_LEVEL)

    # Print banner
    logger.info("=" * 60)
    logger.info("Multi-Source Link Bot")
    logger.info("=" * 60)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")

        # Log configuration (with secrets masked)
        config_dict = Config.get_all()
        logger.info("Configuration:")
        for key, value in config_dict.items():
            logger.info(f"  {key}: {value}")

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        logger.error("See .env.example for required configuration.")
        sys.exit(1)

    # Initialize database
    db = None
    bot = None

    try:
        db = await initialize_database(Config.DATABASE_PATH)

        # Cleanup old data
        await cleanup_old_data(db)

        # Create scrapers for each configured source
        scrapers = []

        if Config.FACEBOOK_PAGE:
            fb_url = f"https://www.facebook.com/{Config.FACEBOOK_PAGE}"
            scraper = WebScraper(fb_url, parse_facebook, source_name="Facebook")
            scrapers.append(scraper)
            logger.info(f"Monitoring Facebook: {fb_url}")

        if Config.TWITTER_USERNAME:
            # Use X API instead of web scraping
            if Config.X_API_BEARER and Config.UCG_EN_X_ID:
                scraper = XAPIClient(
                    bearer_token=Config.X_API_BEARER,
                    user_id=Config.UCG_EN_X_ID,
                    username=Config.TWITTER_USERNAME
                )
                # Set source_name attribute for compatibility with discord_bot
                scraper.source_name = "X/Twitter"
                scrapers.append(scraper)
                logger.info(f"Monitoring X/Twitter via API: @{Config.TWITTER_USERNAME}")
            else:
                logger.warning("Twitter enabled but X_API_BEARER or UCG_EN_X_ID not configured, skipping")

        if Config.ULTRAMAN_COLUMN_URL:
            # Use Ultraman Column API instead of web scraping
            scraper = UltramanColumnAPIClient()
            scrapers.append(scraper)
            logger.info("Monitoring Ultraman Columns via API")

        if Config.ULTRAMAN_NEWS_URL:
            # Use Ultraman News API instead of web scraping
            scraper = UltramanNewsAPIClient()
            scrapers.append(scraper)
            logger.info("Monitoring Ultraman News via API")

        if not scrapers:
            logger.error("No sources configured! Please configure at least one source in .env")
            sys.exit(1)

        logger.info(f"Total sources configured: {len(scrapers)}")

        # Initialize Discord bot
        logger.info("Initializing Discord bot...")
        bot = LinkBot(
            token=Config.DISCORD_BOT_TOKEN,
            scrapers=scrapers,
            database=db,
            channel_name=Config.CHANNEL_NAME,
            poll_interval=Config.POLL_INTERVAL_SECONDS
        )
        logger.info("Discord bot initialized")

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, _frame):
            logger.info(f"Received signal {sig}")
            asyncio.create_task(shutdown(bot, db))

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start the bot (this blocks until bot is stopped)
        logger.info("Starting bot...")
        await bot.start(Config.DISCORD_BOT_TOKEN)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure cleanup
        if bot:
            await bot.close()
        if db:
            await db.close()


if __name__ == "__main__":
    try:
        # Run the async main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
