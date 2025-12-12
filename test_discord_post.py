"""Test script for Discord bot posting functionality"""
import asyncio
import sys

from config import Config, ConfigurationError
from bot.database import Database
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.x_api import XAPIClient
from bot.youtube_api import YouTubeAPIClient
from bot.news_publisher import NewsPublisher
from utils.logger import setup_logger


async def test_discord_post():
    """Test Discord bot by manually triggering a post check"""

    # Setup logger
    logger = setup_logger(__name__, level="INFO")

    print("\n" + "=" * 60)
    print("DISCORD BOT POST TEST")
    print("=" * 60 + "\n")

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file")
        sys.exit(1)

    # Initialize database
    logger.info("Initializing database...")
    db = Database(Config.DATABASE_PATH)
    await db.connect()
    await db.initialize_schema()
    logger.info("Database initialized")

    # Ask user which source to test
    print("\nWhich source would you like to test?")
    print("1. Ultraman Columns")
    print("2. Ultraman News")
    print("3. X/Twitter")
    print("4. YouTube")
    print("0. Cancel")

    choice = input("\nEnter choice (0-4): ").strip()

    if choice == "0":
        print("Cancelled.")
        await db.close()
        return

    # Create scraper based on choice
    scraper = None
    if choice == "1":
        scraper = UltramanColumnAPIClient()
        logger.info("Testing Ultraman Columns...")
    elif choice == "2":
        scraper = UltramanNewsAPIClient()
        logger.info("Testing Ultraman News...")
    elif choice == "3":
        if Config.X_API_BEARER and Config.UCG_EN_X_ID:
            scraper = XAPIClient(
                bearer_token=Config.X_API_BEARER,
                user_id=Config.UCG_EN_X_ID,
                username=Config.TWITTER_USERNAME
            )
            # Set source_name attribute for compatibility with discord_bot
            scraper.source_name = "X/Twitter"
            logger.info("Testing X/Twitter...")
        else:
            logger.error("X API credentials not configured")
            await db.close()
            return
    elif choice == "4":
        if Config.YOUTUBE_API_KEY and Config.YOUTUBE_CHANNEL_ID:
            scraper = YouTubeAPIClient(
                api_key=Config.YOUTUBE_API_KEY,
                channel_id=Config.YOUTUBE_CHANNEL_ID
            )
            logger.info("Testing YouTube...")
        else:
            logger.error("YouTube API credentials not configured")
            await db.close()
            return
    else:
        print("Invalid choice.")
        await db.close()
        return

    # Fetch the latest post URL
    print("\nFetching latest post...")
    post_url = await scraper.get_latest_post_url()

    if not post_url:
        logger.error("Failed to fetch post URL")
        await db.close()
        return

    print(f"\n✓ Found post: {post_url}")

    # Check if already posted
    is_seen = await db.is_post_seen(post_url)
    force_post = False

    if is_seen:
        print("\n⚠️  This post has already been posted to Discord.")
        clear = input("Do you want to post it again anyway? (y/n): ").strip().lower()

        if clear == "y":
            logger.info("Will post again (bypassing database check)")
            force_post = True
        else:
            print("Skipping post (already in database)")
            await db.close()
            return

    # Initialize NewsPublisher
    logger.info("Initializing NewsPublisher...")
    publisher = NewsPublisher(
        bot_token=Config.DISCORD_BOT_TOKEN,
        channel_name=Config.CHANNEL_NAME,
        database_path=Config.DATABASE_PATH
    )

    # Post to Discord
    print("\nPosting to Discord...")
    try:
        await publisher._post_to_discord(post_url, scraper.source_name)

        # Mark as seen in database
        if force_post:
            # Update timestamp even though already seen
            await db.mark_post_seen(post_url, scraper.source_name)
        else:
            # Mark as seen for first time
            await db.mark_post_seen(post_url, scraper.source_name)

        print("\n✓ Test complete! Check your Discord channel.\n")
    except Exception as e:
        logger.error(f"Error posting to Discord: {e}", exc_info=True)
        print(f"\n✗ Failed to post: {e}\n")

    # Cleanup
    await db.close()

    # Give asyncio time to clean up any pending tasks/connections
    await asyncio.sleep(0.1)


if __name__ == "__main__":
    try:
        asyncio.run(test_discord_post())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure all async resources are cleaned up
        import asyncio as aio
        try:
            loop = aio.get_event_loop()
            if loop.is_running():
                loop.stop()
        except RuntimeError:
            pass
