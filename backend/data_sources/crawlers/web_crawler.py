#!/usr/bin/env python3
"""
Basic web crawler connector for scraping news sites and content.
Implements respectful crawling with rate limiting and robots.txt compliance.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from urllib.parse import urljoin, urlparse, robots
from urllib.robotparser import RobotFileParser
import re

import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..base.base_connector import BaseDataConnector, RawEvent, FetchError, ConfigurationError
from ..base.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class WebCrawler(BaseDataConnector):
    """Basic web crawler for scraping content from websites."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize web crawler.
        
        Args:
            config: Configuration dictionary with crawler settings
        """
        super().__init__(config)
        
        # Crawler-specific configuration
        self.base_url = config.get('base_url')
        self.target_urls = config.get('target_urls', [])
        self.selectors = config.get('selectors', {})
        self.user_agent = config.get('user_agent', 'MisinformationHeatmap/1.0 (+https://github.com/your-org/misinformation-heatmap)')
        self.timeout = config.get('timeout', 30)
        self.max_pages = config.get('max_pages', 10)
        self.respect_robots = config.get('respect_robots', True)
        self.follow_links = config.get('follow_links', False)
        self.link_patterns = config.get('link_patterns', [])
        
        # Content extraction settings
        self.min_content_length = config.get('min_content_length', 100)
        self.max_content_length = config.get('max_content_length', 10000)
        
        # Rate limiting (more conservative for crawling)
        rate_limit = config.get('rate_limit', 30)  # 30 requests per minute
        self.rate_limiter = RateLimiter(requests_per_minute=rate_limit)
        
        # HTTP session configuration
        self.session_config = {
            'timeout': aiohttp.ClientTimeout(total=self.timeout),
            'headers': {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # Robots.txt cache
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.crawled_urls: Set[str] = set()
        
        self.source_type = 'crawler'
    
    def validate_config(self) -> bool:
        """Validate crawler configuration."""
        if not self.base_url and not self.target_urls:
            raise ConfigurationError("Either base_url or target_urls must be specified")
        
        if self.base_url:
            try:
                parsed = urlparse(self.base_url)
                if not parsed.scheme or not parsed.netloc:
                    raise ConfigurationError(f"Invalid base URL: {self.base_url}")
            except Exception as e:
                raise ConfigurationError(f"Invalid base URL: {e}")
        
        # Validate selectors
        required_selectors = ['title', 'content']
        for selector in required_selectors:
            if selector not in self.selectors:
                logger.warning(f"Missing recommended selector: {selector}")
        
        return True
    
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        """Fetch events by crawling target URLs.
        
        Args:
            since: Only fetch events newer than this timestamp
            
        Returns:
            List of RawEvent objects
            
        Raises:
            FetchError: If crawling fails
        """
        try:
            # Determine URLs to crawl
            urls_to_crawl = self._get_urls_to_crawl()
            
            if not urls_to_crawl:
                logger.warning(f"No URLs to crawl for {self.source_id}")
                return []
            
            # Limit number of URLs
            if len(urls_to_crawl) > self.max_pages:
                urls_to_crawl = urls_to_crawl[:self.max_pages]
                logger.info(f"Limited crawling to {self.max_pages} URLs for {self.source_id}")
            
            # Crawl URLs and extract events
            events = []
            
            async with aiohttp.ClientSession(**self.session_config) as session:
                for url in urls_to_crawl:
                    try:
                        # Check robots.txt
                        if self.respect_robots and not await self._can_fetch(url):
                            logger.debug(f"Robots.txt disallows crawling: {url}")
                            continue
                        
                        # Rate limiting
                        if not await self.rate_limiter.wait_for_tokens(timeout=30):
                            logger.warning(f"Rate limit timeout for {self.source_id}")
                            break
                        
                        # Crawl URL
                        page_events = await self._crawl_url(session, url, since)
                        events.extend(page_events)
                        
                        # Mark as crawled
                        self.crawled_urls.add(url)
                        
                    except Exception as e:
                        logger.warning(f"Failed to crawl URL {url}: {e}")
                        continue
            
            logger.info(f"Crawled {len(events)} events from {len(urls_to_crawl)} URLs for {self.source_id}")
            return events
            
        except Exception as e:
            logger.error(f"Crawling failed for {self.source_id}: {e}")
            raise FetchError(f"Crawling failed: {e}")
    
    def _get_urls_to_crawl(self) -> List[str]:
        """Get list of URLs to crawl."""
        urls = []
        
        # Add configured target URLs
        if self.target_urls:
            urls.extend(self.target_urls)
        
        # Add base URL if specified
        if self.base_url:
            urls.append(self.base_url)
        
        # Remove duplicates and already crawled URLs
        unique_urls = []
        for url in urls:
            if url not in unique_urls and url not in self.crawled_urls:
                unique_urls.append(url)
        
        return unique_urls
    
    async def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check cache first
            if base_url in self.robots_cache:
                rp = self.robots_cache[base_url]
            else:
                # Fetch and parse robots.txt
                rp = RobotFileParser()
                robots_url = urljoin(base_url, '/robots.txt')
                
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                        async with session.get(robots_url) as response:
                            if response.status == 200:
                                robots_content = await response.text()
                                rp.set_url(robots_url)
                                rp.read()  # This would need the content, simplified here
                except:
                    # If robots.txt can't be fetched, assume crawling is allowed
                    pass
                
                self.robots_cache[base_url] = rp
            
            # Check if crawling is allowed
            return rp.can_fetch(self.user_agent, url)
            
        except Exception as e:
            logger.debug(f"Robots.txt check failed for {url}: {e}")
            return True  # Default to allowing if check fails
    
    async def _crawl_url(self, session: aiohttp.ClientSession, url: str, since: Optional[datetime] = None) -> List[RawEvent]:
        """Crawl a single URL and extract events."""
        try:
            logger.debug(f"Crawling URL: {url}")
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for URL: {url}")
                    return []
                
                # Get content
                html_content = await response.text()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract events from page
                events = await self._extract_events_from_page(soup, url, since)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to crawl URL {url}: {e}")
            return []
    
    async def _extract_events_from_page(self, soup: BeautifulSoup, url: str, since: Optional[datetime] = None) -> List[RawEvent]:
        """Extract events from a parsed HTML page."""
        events = []
        
        try:
            # Extract title
            title = self._extract_title(soup)
            
            # Extract main content
            content = self._extract_content(soup)
            
            if not content or len(content) < self.min_content_length:
                logger.debug(f"Insufficient content from {url}")
                return []
            
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "..."
            
            # Extract timestamp
            timestamp = self._extract_timestamp(soup) or datetime.now(timezone.utc)
            
            # Filter by timestamp if specified
            if since and timestamp <= since:
                logger.debug(f"Content too old from {url}: {timestamp}")
                return []
            
            # Extract author
            author = self._extract_author(soup)
            
            # Extract location hint
            location_hint = self.extract_location_hint(content + " " + (title or ""))
            
            # Detect language
            language = self.detect_language(content)
            
            # Build metadata
            metadata = {
                'crawled_url': url,
                'crawl_timestamp': datetime.now(timezone.utc).isoformat(),
                'base_url': self.base_url,
                'selectors_used': self.selectors,
                'content_length': len(content)
            }
            
            # Create RawEvent
            event = RawEvent(
                source_id=self.source_id,
                source_type=self.source_type,
                content=self.preprocess_content(content),
                timestamp=timestamp,
                url=url,
                title=title,
                author=author,
                language=language,
                location_hint=location_hint,
                metadata=metadata,
                raw_data={'html_snippet': str(soup)[:1000]}  # Store snippet for debugging
            )
            
            events.append(event)
            
        except Exception as e:
            logger.error(f"Failed to extract events from {url}: {e}")
        
        return events
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract title from HTML."""
        title_selector = self.selectors.get('title', 'h1, title')
        
        try:
            title_elements = soup.select(title_selector)
            if title_elements:
                title = title_elements[0].get_text(strip=True)
                return title if title else None
        except Exception as e:
            logger.debug(f"Title extraction failed: {e}")
        
        # Fallback to page title
        try:
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text(strip=True)
        except:
            pass
        
        return None
    
    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract main content from HTML."""
        content_selector = self.selectors.get('content', 'article, .content, .article-content, .story-content, main')
        
        try:
            content_elements = soup.select(content_selector)
            if content_elements:
                # Get text from the first matching element
                content = content_elements[0].get_text(separator=' ', strip=True)
                return content if content else None
        except Exception as e:
            logger.debug(f"Content extraction failed: {e}")
        
        # Fallback to body content
        try:
            body = soup.find('body')
            if body:
                # Remove script and style elements
                for script in body(["script", "style", "nav", "header", "footer", "aside"]):
                    script.decompose()
                
                content = body.get_text(separator=' ', strip=True)
                return content if content else None
        except:
            pass
        
        return None
    
    def _extract_timestamp(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Extract timestamp from HTML."""
        timestamp_selector = self.selectors.get('timestamp', 'time, .date, .publish-date, .timestamp')
        
        try:
            timestamp_elements = soup.select(timestamp_selector)
            if timestamp_elements:
                timestamp_element = timestamp_elements[0]
                
                # Try datetime attribute first
                datetime_attr = timestamp_element.get('datetime')
                if datetime_attr:
                    return date_parser.parse(datetime_attr)
                
                # Try text content
                timestamp_text = timestamp_element.get_text(strip=True)
                if timestamp_text:
                    return date_parser.parse(timestamp_text)
                    
        except Exception as e:
            logger.debug(f"Timestamp extraction failed: {e}")
        
        # Try meta tags
        try:
            meta_selectors = [
                'meta[property="article:published_time"]',
                'meta[name="publish-date"]',
                'meta[name="date"]'
            ]
            
            for selector in meta_selectors:
                meta_tag = soup.select_one(selector)
                if meta_tag:
                    content = meta_tag.get('content')
                    if content:
                        return date_parser.parse(content)
        except:
            pass
        
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from HTML."""
        author_selector = self.selectors.get('author', '.author, .byline, [rel="author"]')
        
        try:
            author_elements = soup.select(author_selector)
            if author_elements:
                author = author_elements[0].get_text(strip=True)
                return author if author else None
        except Exception as e:
            logger.debug(f"Author extraction failed: {e}")
        
        # Try meta tags
        try:
            meta_selectors = [
                'meta[name="author"]',
                'meta[property="article:author"]'
            ]
            
            for selector in meta_selectors:
                meta_tag = soup.select_one(selector)
                if meta_tag:
                    content = meta_tag.get('content')
                    if content:
                        return content
        except:
            pass
        
        return None
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the crawler."""
        try:
            # Test connectivity to base URL
            if self.base_url:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={'User-Agent': self.user_agent}
                ) as session:
                    
                    async with session.head(self.base_url) as response:
                        is_accessible = response.status in [200, 301, 302, 304]
                        status_code = response.status
            else:
                is_accessible = True
                status_code = None
            
            return {
                'status': 'healthy' if is_accessible else 'unhealthy',
                'accessible': is_accessible,
                'status_code': status_code,
                'base_url': self.base_url,
                'target_urls_count': len(self.target_urls),
                'crawled_urls_count': len(self.crawled_urls),
                'rate_limiter': self.rate_limiter.get_status(),
                'stats': self.get_stats()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'accessible': False,
                'error': str(e),
                'base_url': self.base_url,
                'stats': self.get_stats()
            }