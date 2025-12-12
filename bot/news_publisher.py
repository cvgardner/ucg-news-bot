"""News publisher for stateless cron execution"""
import asyncio
import discord
from bot.database import Database
from bot.x_api import XAPIClient
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.youtube_api import YouTubeAPIClient
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsPublisher:
    """Stateless news publisher that checks sources and posts to Discord"""

    def __init__(self, bot_token: str, channel_name: str, database_path: str):
        """
        Initialize NewsPublisher.

        Args:
            bot_token: Discord bot token
            channel_name: Name of channel to find (e.g., "ucg-news-bot")
            database_path: Path to SQLite database
        """
        self.bot_token = bot_token
        self.channel_name = channel_name
        self.database_path = database_path
        self.scrapers = []

    def _setup_scrapers(self):
        """Setup all configured scrapers"""
        logger.info("Setting up scrapers...")

        if Config.TWITTER_USERNAME:
            # Use X API instead of web scraping
            if Config.X_API_BEARER and Config.UCG_EN_X_ID:
                scraper = XAPIClient(
                    bearer_token=Config.X_API_BEARER,
                    user_id=Config.UCG_EN_X_ID,
                    username=Config.TWITTER_USERNAME
                )
                # Set source_name attribute for compatibility
                scraper.source_name = "X/Twitter"
                self.scrapers.append(scraper)
                logger.info(f"Configured X/Twitter via API: @{Config.TWITTER_USERNAME}")
            else:
                logger.warning("Twitter enabled but X_API_BEARER or UCG_EN_X_ID not configured, skipping")

        if Config.ULTRAMAN_COLUMN_URL:
            # Use Ultraman Column API instead of web scraping
            scraper = UltramanColumnAPIClient()
            self.scrapers.append(scraper)
            logger.info("Configured Ultraman Columns via API")

        if Config.ULTRAMAN_NEWS_URL:
            # Use Ultraman News API instead of web scraping
            scraper = UltramanNewsAPIClient()
            self.scrapers.append(scraper)
            logger.info("Configured Ultraman News via API")

        if Config.YOUTUBE_CHANNEL_ID:
            # Use YouTube Data API v3
            if Config.YOUTUBE_API_KEY:
                scraper = YouTubeAPIClient(
                    api_key=Config.YOUTUBE_API_KEY,
                    channel_id=Config.YOUTUBE_CHANNEL_ID
                )
                self.scrapers.append(scraper)
                logger.info(f"Configured YouTube via API: Channel {Config.YOUTUBE_CHANNEL_ID}")
            else:
                logger.warning("YouTube enabled but YOUTUBE_API_KEY not configured, skipping")

        if not self.scrapers:
            logger.error("No sources configured! Please configure at least one source.")
            raise ValueError("No sources configured")

        logger.info(f"Total sources configured: {len(self.scrapers)}")

    async def run(self):
        """Main execution flow for cron job"""
        logger.info("Starting news check...")

        # Initialize database
        db = Database(self.database_path)
        await db.connect()
        await db.initialize_schema()
        logger.info("Database initialized")

        # Setup scrapers
        self._setup_scrapers()

        # Check all sources
        for scraper in self.scrapers:
            await self._check_source(scraper, db)

        # Cleanup old posts (older than 30 days)
        await db.cleanup_old_posts(days=30)

        # Close database
        await db.close()
        logger.info("News check complete")

    async def _check_source(self, scraper, db: Database):
        """
        Check one source for new posts.

        Args:
            scraper: Scraper instance (WebScraper, XAPIClient, etc.)
            db: Database instance
        """
        try:
            # Get latest post URL
            post_url = await scraper.get_latest_post_url()

            if not post_url:
                logger.debug(f"No post found from {scraper.source_name}")
                return

            # Check if already posted
            if await db.is_post_seen(post_url):
                logger.debug(f"Already posted: {post_url}")
                return

            # New post found! Post to Discord
            logger.info(f"New post from {scraper.source_name}: {post_url}")
            await self._post_to_discord(post_url, scraper.source_name)

            # Mark as seen
            await db.mark_post_seen(post_url, scraper.source_name)

        except Exception as e:
            logger.error(f"Error checking source {scraper.source_name}: {e}", exc_info=True)

    async def _post_to_discord(self, url: str, source_name: str):
        """
        Post URL to all Discord channels with the configured name.

        Args:
            url: URL to post
            source_name: Name of source for logging
        """
        success = 0
        failed = 0

        # Create Discord client with guild intents
        intents = discord.Intents.default()
        intents.guilds = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            """Called when client is ready - do the posting here"""
            nonlocal success, failed

            logger.debug(f"Discord client ready as {client.user}")

            # Discover channels by name across all guilds
            for guild in client.guilds:
                channel = discord.utils.get(guild.text_channels, name=self.channel_name)

                if not channel:
                    continue

                # Check permissions
                permissions = channel.permissions_for(guild.me)
                if not permissions.send_messages:
                    logger.warning(f"Missing send permissions in {guild.name} #{channel.name}")
                    failed += 1
                    continue

                try:
                    # Send the link
                    message = await channel.send(url)

                    # Create thread from message (auto-archives after 24 hours)
                    try:
                        # Validate thread name - ensure it's not empty and has minimum length
                        thread_name = url[:100].strip() if url else "Discussion"
                        if len(thread_name) < 1:
                            thread_name = "Discussion"

                        await message.create_thread(
                            name=thread_name,
                            auto_archive_duration=1440
                        )
                        logger.info(f"✓ Created thread '{thread_name}' in {guild.name}")
                    except discord.Forbidden:
                        logger.error(f"✗ THREAD CREATION FAILED: Missing 'Create Public Threads' permission in {guild.name}")
                        logger.error(f"   → Please enable 'Create Public Threads' permission for the bot role in {guild.name}")
                        # Post succeeded even if thread creation failed
                    except discord.HTTPException as e:
                        logger.error(f"✗ THREAD CREATION FAILED in {guild.name}: {e}")
                        logger.error(f"   → Discord API error. Channel type: {channel.type}")
                        # Post succeeded even if thread creation failed
                    except Exception as e:
                        logger.error(f"✗ THREAD CREATION FAILED in {guild.name}: Unexpected error - {e}")
                        # Post succeeded even if thread creation failed

                    success += 1
                    logger.info(f"Posted to {guild.name} #{channel.name}")

                except discord.Forbidden:
                    logger.error(f"Missing permissions in {guild.name}")
                    failed += 1
                except discord.HTTPException as e:
                    logger.error(f"HTTP error in {guild.name}: {e}")
                    failed += 1
                except Exception as e:
                    logger.error(f"Unexpected error in {guild.name}: {e}")
                    failed += 1

            if success == 0 and failed == 0:
                logger.warning(f"No channels named '{self.channel_name}' found in any guilds")

            logger.info(
                f"Posted {source_name} link: {success} successful, {failed} failed"
            )

            # Close client after posting
            await client.close()

        try:
            # Start the client - it will run until closed in on_ready
            await client.start(self.bot_token)
        except asyncio.CancelledError:
            # Expected when client.close() is called
            pass
        except Exception as e:
            logger.error(f"Error running Discord client: {e}", exc_info=True)
            raise
