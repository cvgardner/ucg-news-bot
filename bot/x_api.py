"""X (Twitter) API client for fetching tweets"""
import aiohttp
from typing import Optional
from utils.logger import get_logger
from utils.error_handler import retry_with_backoff

logger = get_logger(__name__)


class XAPIClient:
    """Client for interacting with X API v2"""

    def __init__(self, bearer_token: str, user_id: str, username: str = None):
        """
        Args:
            bearer_token: X API Bearer token
            user_id: X user ID to fetch tweets from
            username: Optional X username for better URL formatting
        """
        self.bearer_token = bearer_token
        self.user_id = user_id
        self.username = username
        self.base_url = "https://api.x.com/2"

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(aiohttp.ClientError, Exception))
    async def get_latest_tweet_url(self) -> Optional[str]:
        """
        Fetch the latest tweet from the user and return its URL.

        Returns:
            URL of the latest tweet, or None if error
        """
        try:
            logger.debug(f"Fetching tweets for user ID: {self.user_id}")

            url = f"{self.base_url}/users/{self.user_id}/tweets"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "UCG-News-Bot/1.0"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:
                        logger.error("X API rate limit reached. Please wait before retrying.")
                        return None

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"X API request failed: {response.status} - {error_text}")
                        return None

                    data = await response.json()

            # Extract the first tweet's ID
            if "data" in data and len(data["data"]) > 0:
                tweet_id = data["data"][0]["id"]

                # Use username if available, otherwise use generic format
                if self.username:
                    tweet_url = f"https://x.com/{self.username}/status/{tweet_id}"
                else:
                    tweet_url = f"https://x.com/i/web/status/{tweet_id}"

                logger.info(f"Found latest tweet: {tweet_url}")
                return tweet_url
            else:
                logger.warning(f"No tweets found for user ID: {self.user_id}")
                return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching tweets: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}", exc_info=True)
            return None
