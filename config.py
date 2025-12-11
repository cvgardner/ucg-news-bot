"""Configuration loader and validator for Multi-Source Link Bot"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass


class Config:
    """Configuration class for bot settings"""

    # Required fields
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # X/Twitter API credentials
    X_API_BEARER = os.getenv("X_API_BEARER")
    UCG_EN_X_ID = os.getenv("UCG_EN_X_ID")

    # YouTube API credentials
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

    # Sources to monitor (optional - configure which are active)
    FACEBOOK_PAGE = os.getenv("FACEBOOK_PAGE")
    TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
    ULTRAMAN_COLUMN_URL = os.getenv("ULTRAMAN_COLUMN_URL")
    ULTRAMAN_NEWS_URL = os.getenv("ULTRAMAN_NEWS_URL")

    # Bot settings with defaults
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))  # 5 minutes
    CHANNEL_NAME = os.getenv("CHANNEL_NAME", "ucg-news-bot")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./bot_data.db")

    @classmethod
    def validate(cls):
        """
        Validate that all required configuration values are present.
        Raises ConfigurationError if any required fields are missing.
        """
        errors = []

        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN is required")

        # Check X API credentials if Twitter is enabled
        if cls.TWITTER_USERNAME and (not cls.X_API_BEARER or not cls.UCG_EN_X_ID):
            errors.append("X_API_BEARER and UCG_EN_X_ID are required when TWITTER_USERNAME is set")

        # Check YouTube API credentials if YouTube is enabled
        if cls.YOUTUBE_CHANNEL_ID and not cls.YOUTUBE_API_KEY:
            errors.append("YOUTUBE_API_KEY is required when YOUTUBE_CHANNEL_ID is set")

        # Check that at least one source is configured
        has_source = any([
            cls.FACEBOOK_PAGE,
            cls.TWITTER_USERNAME,
            cls.ULTRAMAN_COLUMN_URL,
            cls.ULTRAMAN_NEWS_URL,
            cls.YOUTUBE_CHANNEL_ID
        ])

        if not has_source:
            errors.append("At least one source must be configured (FACEBOOK_PAGE, TWITTER_USERNAME, ULTRAMAN_COLUMN_URL, or ULTRAMAN_NEWS_URL)")

        if cls.POLL_INTERVAL_SECONDS < 60:
            errors.append("POLL_INTERVAL_SECONDS must be at least 60 seconds")

        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ConfigurationError(error_message)

    @classmethod
    def get_all(cls):
        """Return all configuration values as a dictionary"""
        return {
            "DISCORD_BOT_TOKEN": "***" if cls.DISCORD_BOT_TOKEN else None,
            "X_API_BEARER": "***" if cls.X_API_BEARER else None,
            "UCG_EN_X_ID": cls.UCG_EN_X_ID,
            "YOUTUBE_API_KEY": "***" if cls.YOUTUBE_API_KEY else None,
            "YOUTUBE_CHANNEL_ID": cls.YOUTUBE_CHANNEL_ID,
            "FACEBOOK_PAGE": cls.FACEBOOK_PAGE,
            "TWITTER_USERNAME": cls.TWITTER_USERNAME,
            "ULTRAMAN_COLUMN_URL": cls.ULTRAMAN_COLUMN_URL,
            "ULTRAMAN_NEWS_URL": cls.ULTRAMAN_NEWS_URL,
            "POLL_INTERVAL_SECONDS": cls.POLL_INTERVAL_SECONDS,
            "CHANNEL_NAME": cls.CHANNEL_NAME,
            "LOG_LEVEL": cls.LOG_LEVEL,
            "DATABASE_PATH": cls.DATABASE_PATH,
        }
