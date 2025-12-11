"""URL extraction parsers for different sources"""
from bs4 import BeautifulSoup
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_facebook(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract latest post URL from Facebook page.

    Facebook structure: Look for links with /posts/ or /videos/ in href
    """
    try:
        # Facebook post links typically contain /posts/ or /videos/
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/posts/' in href or '/videos/' in href:
                # Make absolute URL
                if href.startswith('http'):
                    return href
                else:
                    return f"https://www.facebook.com{href}"
        return None
    except Exception as e:
        logger.error(f"Error parsing Facebook: {e}")
        return None


def parse_twitter(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract latest tweet URL from Twitter/X profile.

    Twitter structure: Look for /status/ links, skip pinned post (1st), get 2nd
    """
    try:
        status_links = []

        # Find all links with /status/ in them
        for link in soup.find_all('a', href=True):
            href = link['href']

            # Filter out image and analytics links
            if 'image' in href.lower() or 'analytics' in href.lower():
                continue

            # Look for /status/ links (actual tweets)
            if '/status/' in href:
                # Make absolute URL
                if href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://x.com{href}"

                # Avoid duplicates
                if full_url not in status_links:
                    status_links.append(full_url)

        # Get the 2nd status link (skip pinned post which is 1st)
        if len(status_links) >= 2:
            logger.info(f"Found {len(status_links)} tweet links, returning 2nd (skipping pinned)")
            return status_links[1]
        elif len(status_links) == 1:
            logger.warning("Only found 1 tweet link (might be pinned post)")
            return status_links[0]
        else:
            logger.warning("No tweet links found")
            return None

    except Exception as e:
        logger.error(f"Error parsing /X: {e}")
        return None


def parse_ultraman_column(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract latest column URL from Ultraman website.

    Structure: Find first article/column link
    """
    try:
        # Look for column links (adjust selector based on actual HTML)
        # Common patterns: <a class="column-item">, <div class="article">

        # Try finding links in article containers
        articles = soup.find_all('a', class_=['column-item', 'article', 'post', 'item'])
        if articles:
            href = articles[0].get('href')
            if href:
                if href.startswith('http'):
                    return href
                else:
                    return f"https://ultraman-cardgame.com{href}"

        # Fallback: any link with /column/ in it
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/column/' in href and not href.endswith('/column-list'):
                if href.startswith('http'):
                    return href
                else:
                    return f"https://ultraman-cardgame.com{href}"

        return None
    except Exception as e:
        logger.error(f"Error parsing Ultraman column: {e}")
        return None


def parse_ultraman_news(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract latest news URL from Ultraman website.

    Structure: Find first news article link
    """
    try:
        # Similar to column parser but for news
        articles = soup.find_all('a', class_=['news-item', 'article', 'post', 'item'])
        if articles:
            href = articles[0].get('href')
            if href:
                if href.startswith('http'):
                    return href
                else:
                    return f"https://ultraman-cardgame.com{href}"

        # Fallback: any link with /news/ in it
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/news/' in href and not href.endswith('/news-list'):
                if href.startswith('http'):
                    return href
                else:
                    return f"https://ultraman-cardgame.com{href}"

        return None
    except Exception as e:
        logger.error(f"Error parsing Ultraman news: {e}")
        return None
