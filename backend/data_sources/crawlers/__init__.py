"""
Web crawler data source connectors for news sites and content scraping.
"""

from .web_crawler import WebCrawler
from .news_crawler import NewsCrawler

__all__ = [
    'WebCrawler',
    'NewsCrawler'
]