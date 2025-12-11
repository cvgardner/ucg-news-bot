"""Ultraman Card Game News API client"""
import aiohttp
from typing import Optional
from utils.logger import get_logger
from utils.error_handler import retry_with_backoff

logger = get_logger(__name__)


class UltramanNewsAPIClient:
    """Client for interacting with Ultraman Card Game News API"""

    def __init__(self):
        """Initialize the Ultraman News API client"""
        self.base_url = "https://api.ultraman-cardgame.com/api/v1/us"
        self.source_name = "Ultraman News"

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(aiohttp.ClientError, Exception))
    async def get_latest_post_url(self) -> Optional[str]:
        """
        Fetch the latest news article (excluding pinned) and return its URL.

        Returns:
            URL of the latest news article, or None if error
        """
        try:
            logger.debug("Fetching latest Ultraman news article")

            url = f"{self.base_url}/news"
            params = {
                "page": 1,
                "per_page": 18
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ultraman News API request failed: {response.status} - {error_text}")
                        return None

                    data = await response.json()

            # Extract the first non-pinned news article from response data
            if "data" in data and len(data["data"]) > 0:
                # Filter out pinned articles (note: API uses "pined" not "pinned")
                non_pinned_articles = [
                    article for article in data["data"]
                    if not article.get("pined", False)
                ]

                if not non_pinned_articles:
                    logger.warning("No non-pinned news articles found in Ultraman API response")
                    return None

                # Get the first non-pinned article
                article = non_pinned_articles[0]
                article_id = article["id"]
                article_title = article.get("title", "Unknown")

                article_url = f"https://ultraman-cardgame.com/page/us/news/news-detail/{article_id}"

                logger.info(f"Found latest news: {article_title}")
                logger.info(f"News URL: {article_url}")
                return article_url
            else:
                logger.warning("No news articles found in Ultraman API response")
                return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching Ultraman news: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching Ultraman news: {e}", exc_info=True)
            return None
