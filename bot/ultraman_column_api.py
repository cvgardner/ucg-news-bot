"""Ultraman Card Game Column API client"""
import aiohttp
from typing import Optional
from utils.logger import get_logger
from utils.error_handler import retry_with_backoff

logger = get_logger(__name__)


class UltramanColumnAPIClient:
    """Client for interacting with Ultraman Card Game Column API"""

    def __init__(self):
        """Initialize the Ultraman Column API client"""
        self.base_url = "https://api.ultraman-cardgame.com/api/v1/us"
        self.source_name = "Ultraman Columns"

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(aiohttp.ClientError, Exception))
    async def get_latest_post_url(self) -> Optional[str]:
        """
        Fetch the latest column article and return its URL.

        Returns:
            URL of the latest column article, or None if error
        """
        try:
            logger.debug("Fetching latest Ultraman column article")

            url = f"{self.base_url}/column"
            params = {
                "page": 1,
                "per_page": 20
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ultraman Column API request failed: {response.status} - {error_text}")
                        return None

                    data = await response.json()

            # Extract the first column from response data
            if "data" in data and len(data["data"]) > 0:
                article = data["data"][0]
                article_id = article["id"]
                article_title = article.get("title", "Unknown")

                article_url = f"https://ultraman-cardgame.com/page/us/column/column-detail/{article_id}"

                logger.info(f"Found latest column: {article_title}")
                logger.info(f"Column URL: {article_url}")
                return article_url
            else:
                logger.warning("No columns found in Ultraman API response")
                return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching Ultraman columns: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Ultraman columns: {e}", exc_info=True)
            return None
