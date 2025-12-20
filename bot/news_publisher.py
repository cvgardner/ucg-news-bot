"""News publisher for stateless cron execution"""
import asyncio
import logging
import discord
from bot.database import Database
from bot.x_api import XAPIClient
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.youtube_api import YouTubeAPIClient
from config import Config
from utils.logger import get_logger, log_with_context

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
        log_with_context(
            logger, logging.INFO, "Starting news check",
            database_path=self.database_path,
            channel_name=self.channel_name
        )

        # Initialize database
        db = Database(self.database_path)
        await db.connect()
        await db.initialize_schema()

        # Setup scrapers
        self._setup_scrapers()

        log_with_context(
            logger, logging.INFO, "Checking all configured sources",
            total_sources=len(self.scrapers),
            source_names=[getattr(s, 'source_name', 'unknown') for s in self.scrapers]
        )

        # Check all sources
        for scraper in self.scrapers:
            await self._check_source(scraper, db)

        # Cleanup old posts (older than 30 days)
        await db.cleanup_old_posts(days=30)

        # Close database
        await db.close()

        log_with_context(
            logger, logging.INFO, "News check complete",
            total_sources_checked=len(self.scrapers)
        )

    async def _check_source(self, scraper, db: Database):
        """
        Check one source for new posts.

        Args:
            scraper: Scraper instance (WebScraper, XAPIClient, etc.)
            db: Database instance
        """
        source_name = getattr(scraper, 'source_name', 'unknown')

        try:
            log_with_context(
                logger, logging.INFO, "Checking source for new posts",
                source_name=source_name
            )

            # Get latest post URL
            post_url = await scraper.get_latest_post_url()

            if not post_url:
                log_with_context(
                    logger, logging.WARNING, "No post found from source",
                    source_name=source_name,
                    reason="get_latest_post_url returned None"
                )
                return

            log_with_context(
                logger, logging.INFO, "Retrieved latest post URL from source",
                source_name=source_name,
                post_url=post_url
            )

            # Check if already posted
            if await db.is_post_seen(post_url):
                log_with_context(
                    logger, logging.INFO, "Post already seen, skipping",
                    source_name=source_name,
                    post_url=post_url
                )
                return

            # New post found! Post to Discord
            log_with_context(
                logger, logging.INFO, "New post detected, posting to Discord",
                source_name=source_name,
                post_url=post_url
            )

            await self._post_to_discord(post_url, source_name)

            # Mark as seen
            await db.mark_post_seen(post_url, source_name)

            log_with_context(
                logger, logging.INFO, "Successfully processed new post",
                source_name=source_name,
                post_url=post_url
            )

        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Error checking source",
                source_name=source_name,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            logger.error(f"Full traceback for source {source_name}:", exc_info=True)

    async def _post_to_discord(self, url: str, source_name: str):
        """
        Post URL to all Discord channels with the configured name.

        Args:
            url: URL to post
            source_name: Name of source for logging
        """
        success = 0
        failed = 0

        log_with_context(
            logger, logging.INFO, "Initializing Discord client for posting",
            url=url,
            source_name=source_name,
            channel_name=self.channel_name
        )

        # Create Discord client with guild intents
        intents = discord.Intents.default()
        intents.guilds = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            """Called when client is ready - do the posting here"""
            nonlocal success, failed

            log_with_context(
                logger, logging.INFO, "Discord client connected",
                bot_user=str(client.user),
                total_guilds=len(client.guilds),
                guild_names=[g.name for g in client.guilds]
            )

            # Discover channels by name across all guilds
            for guild in client.guilds:
                log_with_context(
                    logger, logging.DEBUG, "Searching for channel in guild",
                    guild_name=guild.name,
                    guild_id=guild.id,
                    channel_name=self.channel_name
                )
                channel = discord.utils.get(guild.text_channels, name=self.channel_name)

                if not channel:
                    log_with_context(
                        logger, logging.DEBUG, "Channel not found in guild",
                        guild_name=guild.name,
                        channel_name=self.channel_name,
                        available_channels=[c.name for c in guild.text_channels[:10]]  # First 10
                    )
                    continue

                log_with_context(
                    logger, logging.INFO, "Found target channel in guild",
                    guild_name=guild.name,
                    channel_name=channel.name,
                    channel_id=channel.id
                )

                # Check permissions
                permissions = channel.permissions_for(guild.me)
                if not permissions.send_messages:
                    log_with_context(
                        logger, logging.ERROR, "Missing send_messages permission",
                        guild_name=guild.name,
                        channel_name=channel.name,
                        has_send_messages=permissions.send_messages,
                        has_create_threads=permissions.create_public_threads
                    )
                    failed += 1
                    continue

                try:
                    log_with_context(
                        logger, logging.INFO, "Sending message to channel",
                        guild_name=guild.name,
                        channel_name=channel.name,
                        url=url
                    )

                    # Send the link
                    message = await channel.send(url)

                    log_with_context(
                        logger, logging.INFO, "Message sent successfully",
                        guild_name=guild.name,
                        channel_name=channel.name,
                        message_id=message.id
                    )

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

                        log_with_context(
                            logger, logging.INFO, "Thread created successfully",
                            guild_name=guild.name,
                            thread_name=thread_name
                        )
                    except discord.Forbidden:
                        log_with_context(
                            logger, logging.ERROR, "Thread creation failed - missing permissions",
                            guild_name=guild.name,
                            channel_name=channel.name,
                            error="Missing 'Create Public Threads' permission"
                        )
                        # Post succeeded even if thread creation failed
                    except discord.HTTPException as e:
                        log_with_context(
                            logger, logging.ERROR, "Thread creation failed - Discord API error",
                            guild_name=guild.name,
                            channel_type=str(channel.type),
                            error_message=str(e)
                        )
                        # Post succeeded even if thread creation failed
                    except Exception as e:
                        log_with_context(
                            logger, logging.ERROR, "Thread creation failed - unexpected error",
                            guild_name=guild.name,
                            error_type=type(e).__name__,
                            error_message=str(e)
                        )
                        # Post succeeded even if thread creation failed

                    success += 1

                    log_with_context(
                        logger, logging.INFO, "Successfully posted to guild",
                        guild_name=guild.name,
                        channel_name=channel.name,
                        url=url
                    )

                except discord.Forbidden:
                    log_with_context(
                        logger, logging.ERROR, "Failed to post - forbidden",
                        guild_name=guild.name,
                        channel_name=channel.name if channel else "unknown"
                    )
                    failed += 1
                except discord.HTTPException as e:
                    log_with_context(
                        logger, logging.ERROR, "Failed to post - HTTP error",
                        guild_name=guild.name,
                        error_message=str(e)
                    )
                    failed += 1
                except Exception as e:
                    log_with_context(
                        logger, logging.ERROR, "Failed to post - unexpected error",
                        guild_name=guild.name,
                        error_type=type(e).__name__,
                        error_message=str(e)
                    )
                    failed += 1

            if success == 0 and failed == 0:
                log_with_context(
                    logger, logging.WARNING, "No target channels found in any guilds",
                    channel_name=self.channel_name,
                    total_guilds=len(client.guilds),
                    guild_names=[g.name for g in client.guilds]
                )

            log_with_context(
                logger, logging.INFO, "Discord posting complete",
                source_name=source_name,
                url=url,
                successful_posts=success,
                failed_posts=failed
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
