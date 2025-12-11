"""Test script for Discord bot posting functionality"""
import asyncio
import sys

from config import Config, ConfigurationError
from bot.database import Database
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.x_api import XAPIClient
from bot.discord_bot import LinkBot
from utils.logger import setup_logger, get_logger


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
    print("0. Cancel")

    choice = input("\nEnter choice (0-3): ").strip()

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
            logger.info("Testing X/Twitter...")
        else:
            logger.error("X API credentials not configured")
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

    if is_seen:
        print("\n⚠️  This post has already been posted to Discord.")
        clear = input("Do you want to clear it from database and post again? (y/n): ").strip().lower()

        if clear == "y":
            # Clear from database by deleting the entry
            # Note: There's no delete method, so we'll just proceed and it will be marked as seen again
            logger.info("Will post again (it will be marked as seen in database after posting)")
        else:
            print("Skipping post (already in database)")
            await db.close()
            return

    # Initialize Discord bot
    logger.info("Initializing Discord bot...")
    bot = LinkBot(
        token=Config.DISCORD_BOT_TOKEN,
        scrapers=[scraper],  # Just this one scraper for testing
        database=db,
        channel_name=Config.CHANNEL_NAME,
        poll_interval=Config.POLL_INTERVAL_SECONDS
    )

    # Start bot and wait for it to be ready
    print("\nConnecting to Discord...")

    # Create a task to start the bot
    bot_task = asyncio.create_task(bot.start(Config.DISCORD_BOT_TOKEN))

    # Wait for bot to be ready
    await asyncio.sleep(3)

    if not bot.is_ready():
        logger.error("Bot failed to connect to Discord")
        await bot.close()
        await db.close()
        return

    print(f"\n✓ Connected to Discord as {bot.user.name}")
    print(f"✓ Connected to {len(bot.guilds)} server(s)")
    print(f"✓ Found {len(bot.channel_cache)} channel(s) to post to\n")

    if len(bot.channel_cache) == 0:
        logger.warning(f"No '{Config.CHANNEL_NAME}' channels found in any servers!")
        logger.warning("Make sure the bot has access to a channel with that name.")
        await bot.close()
        await db.close()
        return

    # Manually trigger the check_source method
    print("Posting to Discord...")
    await bot.check_source(scraper)

    print("\n✓ Test complete! Check your Discord channel.\n")

    # Cleanup
    await bot.close()
    await db.close()

    # Cancel the bot task
    bot_task.cancel()
    try:
        await bot_task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(test_discord_post())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
