"""
RSS data source connectors for news feeds and government sources.
"""

from .rss_connector import RSSConnector
from .news_outlets import INDIAN_NEWS_OUTLETS
from .government_feeds import GOVERNMENT_FEEDS

__all__ = [
    'RSSConnector',
    'INDIAN_NEWS_OUTLETS',
    'GOVERNMENT_FEEDS'
]