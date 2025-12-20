#!/usr/bin/env python3
"""Test script to verify logging configuration works for both text and JSON formats"""
import os
import logging
from utils.logger import setup_logger, log_with_context


def test_text_logging():
    """Test text-based logging (for local development)"""
    print("\n" + "="*80)
    print("TEST 1: Text-based logging (local development)")
    print("="*80 + "\n")

    logger = setup_logger("test.text", level="INFO", force_json=False)

    logger.info("Simple info message")
    logger.warning("Simple warning message")
    logger.error("Simple error message")

    log_with_context(
        logger, logging.INFO, "Post fetched from X API",
        user_id="1798233243185303552",
        username="ucg_en",
        tweet_id="1234567890",
        tweet_url="https://x.com/ucg_en/status/1234567890"
    )

    log_with_context(
        logger, logging.ERROR, "X API request failed",
        status_code=429,
        user_id="1798233243185303552",
        rate_limit_reset="1703001600"
    )


def test_json_logging():
    """Test JSON-based logging (for Google Cloud Run)"""
    print("\n" + "="*80)
    print("TEST 2: JSON-based logging (Google Cloud Run)")
    print("="*80 + "\n")

    # Simulate GCP environment
    os.environ["K_SERVICE"] = "ucg-news-bot"

    logger = setup_logger("test.json", level="INFO")

    logger.info("Simple info message")
    logger.warning("Simple warning message")
    logger.error("Simple error message")

    log_with_context(
        logger, logging.INFO, "Post fetched from X API",
        user_id="1798233243185303552",
        username="ucg_en",
        tweet_id="1234567890",
        tweet_url="https://x.com/ucg_en/status/1234567890"
    )

    log_with_context(
        logger, logging.ERROR, "X API request failed",
        status_code=429,
        user_id="1798233243185303552",
        rate_limit_reset="1703001600"
    )

    # Test exception logging
    try:
        raise ValueError("Test exception for logging")
    except Exception as e:
        log_with_context(
            logger, logging.ERROR, "Caught an exception",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        logger.error("Exception with traceback:", exc_info=True)

    # Clean up
    del os.environ["K_SERVICE"]


if __name__ == "__main__":
    print("\nTesting UCG News Bot Logging Configuration")
    print("This demonstrates how logs will appear in different environments\n")

    test_text_logging()
    test_json_logging()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("""
- Text logging: Used locally for human-readable output
- JSON logging: Used in Google Cloud Run for structured logging
- The K_SERVICE environment variable automatically switches between modes
- Context fields appear as key=value in text mode
- Context fields appear as top-level JSON fields in JSON mode
- All logs include source location (file, line, function)
    """)
