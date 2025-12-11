"""Discord bot implementation for multi-source link posting"""
import asyncio
import discord
from discord.ext import commands
from typing import List, Union
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.scraper import WebScraper
from bot.x_api import XAPIClient
from bot.database import Database
from utils.logger import get_logger

logger = get_logger(__name__)


class LinkBot(commands.Bot):
    """Discord bot that posts links from multiple sources"""

    def __init__(
        self,
        token: str,
        scrapers: List[Union[WebScraper, XAPIClient]],
        database: Database,
        channel_name: str,
        poll_interval: int
    ):
        """
        Initialize Discord bot.

        Args:
            token: Discord bot token
            scrapers: List of WebScraper or XAPIClient instances
            database: Database instance
            channel_name: Name of channel to post in
            poll_interval: Polling interval in seconds
        """
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True

        super().__init__(command_prefix="!", intents=intents)

        self.token = token
        self.scrapers = scrapers
        self.database = database
        self.channel_name = channel_name
        self.poll_interval = poll_interval

        # Cache of guild_id -> channel_id
        self.channel_cache = {}
        self.scheduler = AsyncIOScheduler()
        self.is_polling = False

    async def on_ready(self):
        """Called when bot is ready and connected"""
        logger.info(f"Bot logged in as {self.user.name} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")
        logger.info(f"Monitoring {len(self.scrapers)} source(s)")

        # Discover channels
        await self.discover_channels()

        # Start polling
        if not self.is_polling:
            self.start_polling()

        logger.info("Bot ready and polling started")

    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        # Add to database
        await self.database.add_guild(guild.id, guild.name)

        # Find channel
        channel = discord.utils.get(guild.text_channels, name=self.channel_name)
        if channel:
            permissions = channel.permissions_for(guild.me)
            if permissions.send_messages:
                self.channel_cache[guild.id] = channel.id
                logger.info(f"Found channel in {guild.name}: #{channel.name}")
            else:
                logger.warning(f"Missing send permissions in {guild.name} #{channel.name}")
        else:
            logger.info(f"Channel '{self.channel_name}' not found in {guild.name}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot is removed from a guild"""
        logger.info(f"Removed from guild: {guild.name} (ID: {guild.id})")

        # Mark as inactive
        await self.database.remove_guild(guild.id)

        # Remove from cache
        if guild.id in self.channel_cache:
            del self.channel_cache[guild.id]

    async def discover_channels(self):
        """Discover and cache target channels in all guilds"""
        logger.info(f"Discovering '{self.channel_name}' channels in all guilds...")

        found_count = 0

        for guild in self.guilds:
            # Add to database
            await self.database.add_guild(guild.id, guild.name)

            # Find channel
            channel = discord.utils.get(guild.text_channels, name=self.channel_name)
            if channel:
                permissions = channel.permissions_for(guild.me)
                if permissions.send_messages:
                    self.channel_cache[guild.id] = channel.id
                    found_count += 1
                    logger.info(f"  ✓ {guild.name}: #{channel.name}")
                else:
                    logger.warning(f"  ✗ {guild.name}: Missing send permissions")
            else:
                logger.info(f"  - {guild.name}: Channel not found")

        logger.info(f"Channel discovery complete: {found_count} found")

    def start_polling(self):
        """Start the polling task"""
        logger.info(f"Starting polling (interval: {self.poll_interval}s)")

        self.scheduler.add_job(
            self.poll_all_sources,
            'interval',
            seconds=self.poll_interval,
            id='poll_sources',
            replace_existing=True
        )

        self.scheduler.start()
        self.is_polling = True

    async def poll_all_sources(self):
        """Poll all scrapers for new content"""
        try:
            logger.debug("Polling all sources...")

            for scraper in self.scrapers:
                await self.check_source(scraper)

        except Exception as e:
            logger.error(f"Error polling sources: {e}", exc_info=True)

    async def check_source(self, scraper: Union[WebScraper, XAPIClient]):
        """Check one source for new posts"""
        try:
            # Get latest post URL
            post_url = await scraper.get_latest_post_url()

            if not post_url:
                logger.debug(f"No post found from {scraper.source_name}")
                return

            # Check if already posted
            if await self.database.is_post_seen(post_url):
                logger.debug(f"Already posted: {post_url}")
                return

            # New post found! Post to Discord
            logger.info(f"New post from {scraper.source_name}: {post_url}")
            await self.post_link(post_url, scraper.source_name)

            # Mark as seen
            await self.database.mark_post_seen(post_url, scraper.source_name)

        except Exception as e:
            logger.error(f"Error checking source {scraper.source_name}: {e}", exc_info=True)

    async def post_link(self, url: str, source_name: str = "Unknown"):
        """
        Post link to all Discord channels.

        Args:
            url: URL to post
            source_name: Name of source for logging
        """
        if not self.channel_cache:
            logger.warning("No channels available for broadcasting")
            return

        success = 0
        failed = 0

        for guild_id, channel_id in self.channel_cache.items():
            try:
                channel = self.get_channel(channel_id)
                if channel:
                    # Send the link and capture the message
                    message = await channel.send(url)

                    # Create thread from message (auto-archives after 24 hours)
                    try:
                        await message.create_thread(
                            name=url[:100],  # Thread names max 100 characters
                            auto_archive_duration=1440
                        )
                        logger.debug(f"Created thread for {url} in guild {guild_id}")
                    except discord.Forbidden:
                        logger.warning(f"Missing thread permissions in guild {guild_id}")
                        # Post succeeded even if thread creation failed
                    except discord.HTTPException as e:
                        logger.warning(f"Could not create thread in guild {guild_id}: {e}")
                        # Post succeeded even if thread creation failed

                    success += 1
                else:
                    # Channel might have been deleted
                    logger.warning(f"Channel {channel_id} not found in guild {guild_id}")
                    failed += 1
                    # Remove from cache
                    del self.channel_cache[guild_id]

            except discord.Forbidden:
                logger.warning(f"Missing permissions in guild {guild_id}")
                failed += 1
            except discord.HTTPException as e:
                logger.error(f"HTTP error in guild {guild_id}: {e}")
                failed += 1
            except Exception as e:
                logger.error(f"Unexpected error in guild {guild_id}: {e}")
                failed += 1

        logger.info(
            f"Posted {source_name} link: {success} successful, {failed} failed"
        )

    async def close(self):
        """Cleanup when bot is shutting down"""
        logger.info("Shutting down bot...")

        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

        await super().close()
        logger.info("Bot shutdown complete")
