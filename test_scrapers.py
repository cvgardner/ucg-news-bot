"""Test script for web scrapers"""
import asyncio
from bot.scraper import WebScraper
from bot.x_api import XAPIClient
from bot.ultraman_column_api import UltramanColumnAPIClient
from bot.ultraman_news_api import UltramanNewsAPIClient
from bot.parsers import (
    parse_facebook,
)
from config import Config


async def test_twitter():
    """Test Twitter API"""
    print("=" * 60)
    print("Testing X API...")
    print("=" * 60)

    if not Config.X_API_BEARER or not Config.UCG_EN_X_ID:
        print("✗ X API credentials not configured")
        print("  Please set X_API_BEARER and UCG_EN_X_ID in .env")
        print()
        return

    client = XAPIClient(
        bearer_token=Config.X_API_BEARER,
        user_id=Config.UCG_EN_X_ID,
        username=Config.TWITTER_USERNAME
    )
    url = await client.get_latest_tweet_url()

    if url:
        print(f"✓ Success! Latest tweet: {url}")
    else:
        print("✗ Failed to fetch tweet from X API")
        print("  (May be rate limited - free tier has strict limits)")
    print()


async def test_facebook():
    """Test Facebook scraper"""
    print("=" * 60)
    print("Testing Facebook scraper...")
    print("=" * 60)

    scraper = WebScraper(
        'https://www.facebook.com/ultramancardgame',
        parse_facebook,
        'Facebook Test'
    )
    url = await scraper.get_latest_post_url()

    if url:
        print(f"✓ Success! Latest post: {url}")
    else:
        print("✗ Failed to find post URL")
    print()


async def test_ultraman_columns():
    """Test Ultraman Columns API"""
    print("=" * 60)
    print("Testing Ultraman Columns API...")
    print("=" * 60)

    client = UltramanColumnAPIClient()
    url = await client.get_latest_post_url()

    if url:
        print(f"✓ Success! Latest column: {url}")
    else:
        print("✗ Failed to fetch from Ultraman Column API")
    print()


async def test_ultraman_news():
    """Test Ultraman News API"""
    print("=" * 60)
    print("Testing Ultraman News API...")
    print("=" * 60)

    client = UltramanNewsAPIClient()
    url = await client.get_latest_post_url()

    if url:
        print(f"✓ Success! Latest news: {url}")
    else:
        print("✗ Failed to fetch from Ultraman News API")
    print()


async def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("TESTING ALL SCRAPERS")
    print("=" * 60)
    print("\n")

    # Test each scraper
    await test_twitter()
    # await test_facebook()
    # await test_ultraman_columns()
    # await test_ultraman_news()

    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
