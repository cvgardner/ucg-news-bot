"""Database operations for UCG News Bot using SQLite"""
import aiosqlite
import logging
from datetime import datetime, timedelta
from typing import Optional
from utils.logger import get_logger, log_with_context

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
            log_with_context(
                logger, logging.INFO, "Connecting to database",
                db_path=self.db_path
            )
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row
            log_with_context(
                logger, logging.INFO, "Successfully connected to database",
                db_path=self.db_path
            )
        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Failed to connect to database",
                db_path=self.db_path,
                error_type=type(e).__name__,
                error_message=str(e)
            )
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
            log_with_context(
                logger, logging.DEBUG, "Checking if post was already seen",
                post_url=post_url
            )

            async with self.connection.execute(
                "SELECT 1 FROM posted_content WHERE url = ?",
                (post_url,)
            ) as cursor:
                row = await cursor.fetchone()
                is_seen = row is not None

                log_with_context(
                    logger, logging.INFO if not is_seen else logging.DEBUG,
                    "Post seen check complete",
                    post_url=post_url,
                    is_seen=is_seen,
                    status="duplicate" if is_seen else "new"
                )

                return is_seen

        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Failed to check if post was seen",
                post_url=post_url,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return False

    async def mark_post_seen(self, post_url: str, source: str = "unknown"):
        """
        Mark a post URL as posted.

        Args:
            post_url: URL of the post
            source: Source name (facebook, twitter, etc.)
        """
        try:
            log_with_context(
                logger, logging.INFO, "Marking post as seen in database",
                post_url=post_url,
                source=source
            )

            cursor = await self.connection.execute(
                """
                INSERT OR IGNORE INTO posted_content (url, source, posted_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                """,
                (post_url, source)
            )
            await self.connection.commit()

            # Check if row was actually inserted (rowcount > 0) or was duplicate (rowcount = 0)
            was_inserted = cursor.rowcount > 0

            log_with_context(
                logger, logging.INFO, "Successfully marked post as seen",
                post_url=post_url,
                source=source,
                was_new_entry=was_inserted
            )

        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Failed to mark post as seen",
                post_url=post_url,
                source=source,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise

    async def cleanup_old_posts(self, days: int = 30):
        """
        Remove posted content older than specified days.

        Args:
            days: Number of days to keep (default: 30)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            log_with_context(
                logger, logging.INFO, "Starting cleanup of old posts",
                days=days,
                cutoff_date=cutoff_date.isoformat()
            )

            result = await self.connection.execute(
                "DELETE FROM posted_content WHERE posted_at < ?",
                (cutoff_date.isoformat(),)
            )
            await self.connection.commit()
            deleted_count = result.rowcount

            log_with_context(
                logger, logging.INFO, "Completed cleanup of old posts",
                days=days,
                deleted_count=deleted_count,
                cutoff_date=cutoff_date.isoformat()
            )

        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Failed to cleanup old posts",
                days=days,
                error_type=type(e).__name__,
                error_message=str(e)
            )
