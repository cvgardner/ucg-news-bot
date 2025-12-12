"""Database operations for UCG News Bot using SQLite"""
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Handles all database operations for the bot"""

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Establish database connection"""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
            logger.info("Database connection closed")

    async def initialize_schema(self):
        """Create database tables if they don't exist"""
        try:
            async with self.connection.execute("BEGIN"):
                # Posted content table for deduplication (any source)
                await self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS posted_content (
                        url TEXT PRIMARY KEY,
                        posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source TEXT
                    )
                """)

                await self.connection.commit()

            logger.info("Database schema initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    async def is_post_seen(self, post_url: str) -> bool:
        """
        Check if a post URL has already been posted.

        Args:
            post_url: URL to check

        Returns:
            True if URL was already posted, False otherwise
        """
        try:
            async with self.connection.execute(
                "SELECT 1 FROM posted_content WHERE url = ?",
                (post_url,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

        except Exception as e:
            logger.error(f"Failed to check if post was seen: {e}")
            return False

    async def mark_post_seen(self, post_url: str, source: str = "unknown"):
        """
        Mark a post URL as posted.

        Args:
            post_url: URL of the post
            source: Source name (facebook, twitter, etc.)
        """
        try:
            await self.connection.execute(
                """
                INSERT OR IGNORE INTO posted_content (url, source, posted_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (post_url, source)
            )
            await self.connection.commit()
            logger.debug(f"Marked post as seen: {post_url} (source: {source})")

        except Exception as e:
            logger.error(f"Failed to mark post as seen: {e}")
            raise

    async def cleanup_old_posts(self, days: int = 30):
        """
        Remove posted content older than specified days.

        Args:
            days: Number of days to keep (default: 30)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = await self.connection.execute(
                "DELETE FROM posted_content WHERE posted_at < ?",
                (cutoff_date.isoformat(),)
            )
            await self.connection.commit()
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old post records")

        except Exception as e:
            logger.error(f"Failed to cleanup old posts: {e}")
