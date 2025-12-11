"""Generic web scraper for any webpage"""
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional
from utils.logger import get_logger
from utils.error_handler import retry_with_backoff

logger = get_logger(__name__)


class WebScraper:
    """Simple web scraper that fetches and parses HTML"""

    def __init__(self, url: str, parser, source_name: str = "Unknown"):
        """
        Args:
            url: Base URL to scrape
            parser: Parser function to extract post URLs
            source_name: Name of the source for logging
        """
        self.url = url
        self.parser = parser
        self.source_name = source_name

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(aiohttp.ClientError, Exception))
    async def get_latest_post_url(self) -> Optional[str]:
        """
        Fetch page and extract latest post URL.

        Returns:
            URL of latest post, or None if error
        """
        try:
            logger.debug(f"Scraping {self.source_name}: {self.url}")

            # Increase header size limits for sites like Twitter that send long headers
            connector = aiohttp.TCPConnector(limit=10)

            async with aiohttp.ClientSession(
                connector=connector,
                connector_owner=True
            ) as session:
                async with session.get(
                    self.url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    },
                    max_line_size=16384,  # Increase from default 8190
                    max_field_size=16384  # Increase from default 8190
                ) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch {self.url}: {response.status}")
                        return None

                    html = await response.text()

            # Use parser to extract URL
            soup = BeautifulSoup(html, 'html.parser')
            post_url = self.parser(soup)

            if post_url:
                logger.info(f"Found latest post from {self.source_name}: {post_url}")
            else:
                logger.warning(f"No post found on {self.url}")

            return post_url

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error scraping {self.url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {self.url}: {e}", exc_info=True)
            return None
