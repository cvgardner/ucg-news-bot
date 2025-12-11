"""YouTube Data API v3 client for fetching latest videos"""
import aiohttp
from typing import Optional
from utils.logger import get_logger
from utils.error_handler import retry_with_backoff

logger = get_logger(__name__)


class YouTubeAPIClient:
    """Client for interacting with YouTube Data API v3"""

    def __init__(self, api_key: str, channel_id: str):
        """
        Args:
            api_key: YouTube Data API v3 key
            channel_id: YouTube channel ID (UC...)
        """
        self.api_key = api_key
        self.channel_id = channel_id
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.source_name = "YouTube"

    @retry_with_backoff(max_attempts=3, initial_delay=2.0, exceptions=(aiohttp.ClientError, Exception))
    async def get_latest_post_url(self) -> Optional[str]:
        """
        Fetch the latest video from the channel and return its URL.

        Returns:
            URL of the latest video, or None if error
        """
        try:
            logger.debug(f"Fetching latest video for channel: {self.channel_id}")

            # YouTube Data API v3 search endpoint
            url = f"{self.base_url}/search"
            params = {
                "part": "snippet",
                "channelId": self.channel_id,
                "order": "date",
                "type": "video",
                "maxResults": 3,
                "key": self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    # Handle rate limiting (HTTP 403 with quotaExceeded)
                    if response.status == 403:
                        error_data = await response.json()
                        if "quotaExceeded" in str(error_data):
                            logger.error("YouTube API quota exceeded. Daily limit: 10,000 units.")
                            logger.error("Consider increasing POLL_INTERVAL_SECONDS to reduce API calls.")
                        else:
                            logger.error(f"YouTube API forbidden: {error_data}")
                        return None

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"YouTube API request failed: {response.status} - {error_text}")
                        return None

                    data = await response.json()
            
            # Filter out non [EN] videos
            if "items" in data and len(data["items"]) > 0:
                data["items"] = [
                            item for item in data["items"]
                            if "[EN]" in item["snippet"]["title"]
                        ]

            # Extract video ID from response
            if "items" in data and len(data["items"]) > 0:
                video_id = data["items"][0]["id"]["videoId"]
                video_title = data["items"][0]["snippet"]["title"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                logger.info(f"Found latest video: {video_title}")
                logger.info(f"Video URL: {video_url}")
                return video_url
            else:
                logger.warning(f"No videos found for channel ID: {self.channel_id}")
                return None

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching YouTube videos: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching YouTube videos: {e}", exc_info=True)
            return None
