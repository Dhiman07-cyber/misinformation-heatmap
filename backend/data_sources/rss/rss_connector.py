#!/usr/bin/env python3
"""
RSS feed connector for ingesting news and information from RSS sources.
Supports major Indian news outlets and government feeds.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import aiohttp
import feedparser
from dateutil import parser as date_parser

from ..base.base_connector import BaseDataConnector, RawEvent, FetchError, ConfigurationError
from ..base.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RSSConnector(BaseDataConnector):
    """RSS feed connector for news and information sources."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize RSS connector.
        
        Args:
            config: Configuration dictionary with RSS feed settings
        """
        super().__init__(config)
        
        # RSS-specific configuration
        self.feed_url = config.get('feed_url')
        self.user_agent = config.get('user_agent', 'MisinformationHeatmap/1.0 (+https://github.com/your-org/misinformation-heatmap)')
        self.timeout = config.get('timeout', 30)
        self.max_entries = config.get('max_entries', 50)
        self.include_content = config.get('include_content', True)
        
        # Feed metadata
        self.feed_title = config.get('feed_title', '')
        self.feed_category = config.get('category', 'news')
        self.reliability_score = config.get('reliability_score', 0.7)
        
        # Rate limiting
        rate_limit = config.get('rate_limit', 30)  # 30 requests per minute for RSS
        self.rate_limiter = RateLimiter(requests_per_minute=rate_limit)
        
        # HTTP session configuration
        self.session_config = {
            'timeout': aiohttp.ClientTimeout(total=self.timeout),
            'headers': {
                'User-Agent': self.user_agent,
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        }
        
        # Last fetch tracking
        self.last_fetch_time = None
        self.last_etag = None
        self.last_modified = None
        
        self.source_type = 'rss'
    
    def validate_config(self) -> bool:
        """Validate RSS connector configuration."""
        if not self.feed_url:
            raise ConfigurationError("RSS feed URL is required")
        
        # Validate URL format
        try:
            parsed = urlparse(self.feed_url)
            if not parsed.scheme or not parsed.netloc:
                raise ConfigurationError(f"Invalid RSS feed URL: {self.feed_url}")
        except Exception as e:
            raise ConfigurationError(f"Invalid RSS feed URL: {e}")
        
        return True
    
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        """Fetch events from RSS feed.
        
        Args:
            since: Only fetch events newer than this timestamp
            
        Returns:
            List of RawEvent objects
            
        Raises:
            FetchError: If fetching fails
        """
        try:
            # Wait for rate limit
            if not await self.rate_limiter.wait_for_tokens(timeout=30):
                raise FetchError("Rate limit timeout")
            
            # Fetch RSS feed
            feed_data = await self._fetch_rss_feed()
            
            # Parse entries
            events = await self._parse_feed_entries(feed_data, since)
            
            self.logger.info(f"Fetched {len(events)} events from RSS feed {self.source_id}")
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to fetch RSS events from {self.source_id}: {e}")
            raise FetchError(f"RSS fetch failed: {e}")
    
    async def _fetch_rss_feed(self) -> Dict[str, Any]:
        """Fetch RSS feed data from URL."""
        
        # Prepare conditional headers for efficient fetching
        headers = self.session_config['headers'].copy()
        if self.last_etag:
            headers['If-None-Match'] = self.last_etag
        if self.last_modified:
            headers['If-Modified-Since'] = self.last_modified
        
        async with aiohttp.ClientSession(
            timeout=self.session_config['timeout'],
            headers=headers
        ) as session:
            
            try:
                async with session.get(self.feed_url) as response:
                    
                    # Handle 304 Not Modified
                    if response.status == 304:
                        self.logger.debug(f"RSS feed {self.source_id} not modified since last fetch")
                        return {'entries': []}  # No new content
                    
                    # Check for successful response
                    if response.status != 200:
                        raise FetchError(f"HTTP {response.status}: {response.reason}")
                    
                    # Update conditional headers for next request
                    self.last_etag = response.headers.get('ETag')
                    self.last_modified = response.headers.get('Last-Modified')
                    
                    # Read and parse RSS content
                    content = await response.text()
                    
                    # Use feedparser for robust RSS parsing
                    feed_data = feedparser.parse(content)
                    
                    if feed_data.bozo and feed_data.bozo_exception:
                        self.logger.warning(f"RSS feed parsing warning for {self.source_id}: {feed_data.bozo_exception}")
                    
                    return feed_data
                    
            except aiohttp.ClientError as e:
                raise FetchError(f"HTTP client error: {e}")
            except asyncio.TimeoutError:
                raise FetchError("Request timeout")
            except Exception as e:
                raise FetchError(f"Unexpected error: {e}")
    
    async def _parse_feed_entries(self, feed_data: Dict[str, Any], since: Optional[datetime] = None) -> List[RawEvent]:
        """Parse RSS feed entries into RawEvent objects."""
        
        events = []
        entries = feed_data.get('entries', [])
        
        # Limit number of entries processed
        if len(entries) > self.max_entries:
            entries = entries[:self.max_entries]
            self.logger.debug(f"Limited RSS entries to {self.max_entries} for {self.source_id}")
        
        for entry in entries:
            try:
                event = await self._parse_single_entry(entry, feed_data)
                
                # Filter by timestamp if specified
                if since and event.timestamp <= since:
                    continue
                
                events.append(event)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse RSS entry from {self.source_id}: {e}")
                continue
        
        return events
    
    async def _parse_single_entry(self, entry: Dict[str, Any], feed_data: Dict[str, Any]) -> RawEvent:
        """Parse a single RSS entry into a RawEvent."""
        
        # Extract basic information
        title = entry.get('title', '').strip()
        link = entry.get('link', '').strip()
        
        # Extract content (try multiple fields)
        content = self._extract_content(entry)
        
        # Combine title and content
        if title and content:
            full_content = f"{title}\n\n{content}"
        elif title:
            full_content = title
        elif content:
            full_content = content
        else:
            raise ValueError("No content found in RSS entry")
        
        # Parse publication date
        timestamp = self._parse_entry_date(entry)
        
        # Extract author information
        author = self._extract_author(entry)
        
        # Extract location hint
        location_hint = self.extract_location_hint(full_content, entry)
        
        # Detect language
        language = self.detect_language(full_content)
        
        # Build metadata
        metadata = {
            'feed_title': feed_data.get('feed', {}).get('title', self.feed_title),
            'feed_url': self.feed_url,
            'category': self.feed_category,
            'reliability_score': self.reliability_score,
            'entry_id': entry.get('id', ''),
            'tags': entry.get('tags', []),
            'summary': entry.get('summary', ''),
        }
        
        # Add any additional entry fields to metadata
        for key in ['comments', 'enclosures', 'media_content', 'media_thumbnail']:
            if key in entry:
                metadata[key] = entry[key]
        
        # Create RawEvent
        event = RawEvent(
            source_id=self.source_id,
            source_type=self.source_type,
            content=self.preprocess_content(full_content),
            timestamp=timestamp,
            url=link,
            title=title,
            author=author,
            language=language,
            location_hint=location_hint,
            metadata=metadata,
            raw_data={'rss_entry': entry}
        )
        
        return event
    
    def _extract_content(self, entry: Dict[str, Any]) -> str:
        """Extract content from RSS entry, trying multiple fields."""
        
        # Try different content fields in order of preference
        content_fields = [
            'content',           # Full content
            'summary',           # Summary/description
            'description',       # Alternative description field
            'subtitle',          # Subtitle
        ]
        
        for field in content_fields:
            if field in entry:
                content_data = entry[field]
                
                # Handle different content formats
                if isinstance(content_data, list) and content_data:
                    # Multiple content entries, take the first one
                    content_item = content_data[0]
                    if isinstance(content_item, dict):
                        content = content_item.get('value', '')
                    else:
                        content = str(content_item)
                elif isinstance(content_data, dict):
                    content = content_data.get('value', '')
                else:
                    content = str(content_data)
                
                # Clean HTML tags if present
                content = self._clean_html(content)
                
                if content.strip():
                    return content.strip()
        
        return ""
    
    def _clean_html(self, content: str) -> str:
        """Remove HTML tags and decode entities from content."""
        if not content:
            return ""
        
        try:
            import html
            import re
            
            # Decode HTML entities
            content = html.unescape(content)
            
            # Remove HTML tags
            content = re.sub(r'<[^>]+>', ' ', content)
            
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content)
            
            return content.strip()
            
        except Exception as e:
            self.logger.warning(f"HTML cleaning failed: {e}")
            return content
    
    def _parse_entry_date(self, entry: Dict[str, Any]) -> datetime:
        """Parse publication date from RSS entry."""
        
        # Try different date fields
        date_fields = ['published', 'updated', 'created', 'date']
        
        for field in date_fields:
            if field in entry:
                date_str = entry[field]
                
                try:
                    # Parse date string
                    if hasattr(date_str, 'timetuple'):
                        # feedparser time struct
                        timestamp = datetime(*date_str.timetuple()[:6], tzinfo=timezone.utc)
                    else:
                        # String date
                        timestamp = date_parser.parse(date_str)
                        
                        # Ensure timezone awareness
                        if timestamp.tzinfo is None:
                            timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    return timestamp
                    
                except Exception as e:
                    self.logger.debug(f"Failed to parse date field '{field}': {e}")
                    continue
        
        # Fallback to current time
        self.logger.warning(f"No valid date found in RSS entry, using current time")
        return datetime.now(timezone.utc)
    
    def _extract_author(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract author information from RSS entry."""
        
        # Try different author fields
        author_fields = ['author', 'author_detail', 'dc_creator', 'creator']
        
        for field in author_fields:
            if field in entry:
                author_data = entry[field]
                
                if isinstance(author_data, dict):
                    # Structured author data
                    author = author_data.get('name') or author_data.get('email') or author_data.get('href')
                elif isinstance(author_data, str):
                    author = author_data
                else:
                    author = str(author_data)
                
                if author and author.strip():
                    return author.strip()
        
        return None
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the RSS connector."""
        
        try:
            # Test connectivity with a HEAD request
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={'User-Agent': self.user_agent}
            ) as session:
                
                async with session.head(self.feed_url) as response:
                    is_accessible = response.status in [200, 301, 302, 304]
                    status_code = response.status
            
            return {
                'status': 'healthy' if is_accessible else 'unhealthy',
                'accessible': is_accessible,
                'status_code': status_code,
                'feed_url': self.feed_url,
                'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                'rate_limiter': self.rate_limiter.get_status(),
                'stats': self.get_stats()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'accessible': False,
                'error': str(e),
                'feed_url': self.feed_url,
                'last_fetch': self.last_fetch_time.isoformat() if self.last_fetch_time else None,
                'stats': self.get_stats()
            }


# Utility functions for RSS processing

def validate_rss_url(url: str) -> bool:
    """Validate if URL is a valid RSS feed URL."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except:
        return False


async def test_rss_feed(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Test RSS feed accessibility and basic parsing."""
    
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {
                        'accessible': False,
                        'error': f"HTTP {response.status}: {response.reason}"
                    }
                
                content = await response.text()
                feed_data = feedparser.parse(content)
                
                return {
                    'accessible': True,
                    'title': feed_data.get('feed', {}).get('title', 'Unknown'),
                    'description': feed_data.get('feed', {}).get('description', ''),
                    'entry_count': len(feed_data.get('entries', [])),
                    'last_updated': feed_data.get('feed', {}).get('updated', ''),
                    'bozo': feed_data.get('bozo', False),
                    'bozo_exception': str(feed_data.get('bozo_exception', '')) if feed_data.get('bozo_exception') else None
                }
                
    except Exception as e:
        return {
            'accessible': False,
            'error': str(e)
        }