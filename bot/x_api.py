"""X (Twitter) API client for fetching tweets"""
import aiohttp
import logging
from typing import Optional
from utils.logger import get_logger, log_with_context
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
    async def get_latest_post_url(self) -> Optional[str]:
        """
        Fetch the latest tweet from the user and return its URL.

        Returns:
            URL of the latest tweet, or None if error
        """
        try:
            log_with_context(
                logger, logging.INFO, "Starting X API request",
                user_id=self.user_id,
                username=self.username or "unknown"
            )

            url = f"{self.base_url}/users/{self.user_id}/tweets"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "User-Agent": "UCG-News-Bot/1.0"
            }

            log_with_context(
                logger, logging.DEBUG, "Making HTTP GET request",
                url=url,
                timeout=30
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    status_code = response.status

                    log_with_context(
                        logger, logging.DEBUG, "Received X API response",
                        status_code=status_code,
                        user_id=self.user_id
                    )

                    if status_code == 429:
                        # Rate limit - try to get reset time from headers
                        rate_limit_reset = response.headers.get("x-rate-limit-reset", "unknown")
                        rate_limit_remaining = response.headers.get("x-rate-limit-remaining", "unknown")

                        log_with_context(
                            logger, logging.ERROR, "X API rate limit reached",
                            user_id=self.user_id,
                            rate_limit_reset=rate_limit_reset,
                            rate_limit_remaining=rate_limit_remaining
                        )
                        return None

                    if status_code != 200:
                        error_text = await response.text()
                        log_with_context(
                            logger, logging.ERROR, "X API request failed",
                            status_code=status_code,
                            user_id=self.user_id,
                            error_text=error_text[:500]  # Limit error text length
                        )
                        return None

                    data = await response.json()

                    log_with_context(
                        logger, logging.DEBUG, "Successfully parsed X API response",
                        user_id=self.user_id,
                        has_data="data" in data,
                        data_count=len(data.get("data", []))
                    )

            # Extract the first tweet's ID
            if "data" in data and len(data["data"]) > 0:
                tweet_data = data["data"][0]
                tweet_id = tweet_data["id"]
                tweet_text = tweet_data.get("text", "")[:100]  # First 100 chars

                # Use username if available, otherwise use generic format
                if self.username:
                    tweet_url = f"https://x.com/{self.username}/status/{tweet_id}"
                else:
                    tweet_url = f"https://x.com/i/web/status/{tweet_id}"

                log_with_context(
                    logger, logging.INFO, "Successfully fetched latest tweet",
                    user_id=self.user_id,
                    username=self.username or "unknown",
                    tweet_id=tweet_id,
                    tweet_url=tweet_url,
                    tweet_preview=tweet_text
                )
                return tweet_url
            else:
                # Log more details about why no tweets were found
                log_with_context(
                    logger, logging.WARNING, "No tweets found in X API response",
                    user_id=self.user_id,
                    username=self.username or "unknown",
                    response_has_data="data" in data,
                    response_keys=list(data.keys()),
                    data_length=len(data.get("data", []))
                )
                return None

        except aiohttp.ClientError as e:
            log_with_context(
                logger, logging.ERROR, "HTTP client error fetching tweets",
                user_id=self.user_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            return None
        except Exception as e:
            log_with_context(
                logger, logging.ERROR, "Unexpected error fetching tweets",
                user_id=self.user_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            logger.error(f"Full traceback for user {self.user_id}:", exc_info=True)
            return None
