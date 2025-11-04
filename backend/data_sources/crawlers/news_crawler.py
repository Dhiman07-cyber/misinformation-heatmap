#!/usr/bin/env python3
"""
News-specific web crawler with enhanced content extraction for Indian news sites.
Optimized for common Indian news website structures and patterns.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from bs4 import BeautifulSoup
from .web_crawler import WebCrawler

logger = logging.getLogger(__name__)


class NewsCrawler(WebCrawler):
    """News-specific web crawler optimized for Indian news sites."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize news crawler with enhanced selectors."""
        
        # Enhanced selectors for common Indian news sites
        enhanced_selectors = {
            'title': 'h1.story-title, h1.article-title, h1.headline, h1.entry-title, .story-headline h1, .article-headline h1',
            'content': '.story-content, .article-content, .entry-content, .post-content, .news-content, .story-body, .article-body, .content-body',
            'timestamp': 'time, .publish-date, .story-date, .article-date, .date-published, .timestamp, .post-date, .news-date',
            'author': '.author, .byline, .story-author, .article-author, .author-name, .writer-name, [rel="author"]'
        }
        
        # Merge with user-provided selectors
        user_selectors = config.get('selectors', {})
        enhanced_selectors.update(user_selectors)
        config['selectors'] = enhanced_selectors
        
        # News-specific configuration defaults
        config.setdefault('min_content_length', 200)  # News articles should be longer
        config.setdefault('max_content_length', 15000)  # Allow longer news articles
        config.setdefault('respect_robots', True)
        config.setdefault('rate_limit', 20)  # More conservative for news sites
        
        super().__init__(config)
        
        # News-specific patterns
        self.news_indicators = [
            'breaking', 'news', 'report', 'update', 'alert', 'exclusive',
            'latest', 'developing', 'story', 'coverage', 'investigation'
        ]
        
        # Indian news site specific patterns
        self.indian_news_patterns = {
            'timesofindia.indiatimes.com': {
                'title': 'h1.HNMDR',
                'content': '.ga-headlines, .Normal',
                'timestamp': '.publish_on, .time_cptn'
            },
            'thehindu.com': {
                'title': 'h1.title',
                'content': '.content, .article-content',
                'timestamp': '.publish-time, .date-line'
            },
            'indianexpress.com': {
                'title': 'h1.native_story_title',
                'content': '.story_details, .full-details',
                'timestamp': '.date-modified, .p-time'
            },
            'ndtv.com': {
                'title': 'h1.sp-ttl',
                'content': '.sp-cn, .story-content',
                'timestamp': '.sp-desig, .story-date'
            },
            'news18.com': {
                'title': 'h1.article-title',
                'content': '.article-content, .story-content',
                'timestamp': '.article-date, .publish-date'
            }
        }
    
    async def _extract_events_from_page(self, soup: BeautifulSoup, url: str, since: Optional[datetime] = None) -> List[RawEvent]:
        """Enhanced event extraction for news sites."""
        
        # Use site-specific selectors if available
        domain = self._get_domain(url)
        if domain in self.indian_news_patterns:
            site_selectors = self.indian_news_patterns[domain]
            # Temporarily update selectors for this extraction
            original_selectors = self.selectors.copy()
            self.selectors.update(site_selectors)
            
            try:
                events = await super()._extract_events_from_page(soup, url, since)
            finally:
                # Restore original selectors
                self.selectors = original_selectors
            
            return events
        
        # Use standard extraction for other sites
        return await super()._extract_events_from_page(soup, url, since)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            return urlparse(url).netloc.lower()
        except:
            return ""
    
    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Enhanced content extraction for news articles."""
        
        # Try parent class extraction first
        content = super()._extract_content(soup)
        if content and len(content) > self.min_content_length:
            return self._clean_news_content(content)
        
        # Try additional news-specific selectors
        news_selectors = [
            'div[data-module="ArticleBody"]',  # Common pattern
            '.story-element-text',  # Another common pattern
            '.article-text',
            '.news-text',
            '.story-text',
            'div.story p',  # Paragraph-based extraction
            'div.article p'
        ]
        
        for selector in news_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    # Combine text from multiple elements
                    content_parts = []
                    for element in elements:
                        text = element.get_text(separator=' ', strip=True)
                        if text and len(text) > 20:  # Minimum paragraph length
                            content_parts.append(text)
                    
                    if content_parts:
                        combined_content = ' '.join(content_parts)
                        if len(combined_content) > self.min_content_length:
                            return self._clean_news_content(combined_content)
            except Exception as e:
                logger.debug(f"News selector {selector} failed: {e}")
                continue
        
        return content
    
    def _clean_news_content(self, content: str) -> str:
        """Clean and enhance news content."""
        if not content:
            return content
        
        import re
        
        # Remove common news site artifacts
        artifacts_to_remove = [
            r'Also Read:.*?(?=\n|$)',
            r'READ MORE:.*?(?=\n|$)',
            r'ALSO READ:.*?(?=\n|$)',
            r'Subscribe to.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
            r'Download.*?app.*?(?=\n|$)',
            r'Join.*?WhatsApp.*?(?=\n|$)',
            r'Get latest.*?updates.*?(?=\n|$)',
            r'For more.*?news.*?(?=\n|$)',
            r'\(This story has not been edited.*?\)',
            r'\(With inputs from.*?\)',
            r'\(PTI\)|\(ANI\)|\(IANS\)',  # News agency tags
            r'Image:.*?(?=\n|$)',
            r'Photo:.*?(?=\n|$)',
            r'Video:.*?(?=\n|$)'
        ]
        
        for pattern in artifacts_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Clean up whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Remove very short sentences that are likely artifacts
        sentences = content.split('.')
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 15 and not self._is_likely_artifact(sentence):
                cleaned_sentences.append(sentence)
        
        return '. '.join(cleaned_sentences)
    
    def _is_likely_artifact(self, text: str) -> bool:
        """Check if text is likely a website artifact rather than news content."""
        
        artifact_indicators = [
            'click here', 'read more', 'subscribe', 'follow us', 'download',
            'advertisement', 'sponsored', 'promoted', 'trending now',
            'most popular', 'related stories', 'you may also like',
            'share this', 'tweet this', 'facebook', 'twitter', 'instagram',
            'whatsapp', 'telegram', 'youtube', 'linkedin'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in artifact_indicators)
    
    def _extract_timestamp(self, soup: BeautifulSoup) -> Optional[datetime]:
        """Enhanced timestamp extraction for Indian news sites."""
        
        # Try parent class extraction first
        timestamp = super()._extract_timestamp(soup)
        if timestamp:
            return timestamp
        
        # Try Indian news site specific patterns
        indian_timestamp_selectors = [
            'span.date',
            'div.date',
            'p.date',
            '.story-date',
            '.article-date',
            '.publish-date',
            '.updated-date',
            '.post-date',
            '.news-date',
            '.time-stamp',
            '.date-time',
            '[data-date]',
            '[data-time]',
            '.byline-date'
        ]
        
        for selector in indian_timestamp_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    for element in elements:
                        # Try data attributes
                        for attr in ['data-date', 'data-time', 'datetime']:
                            if element.has_attr(attr):
                                try:
                                    from dateutil import parser as date_parser
                                    return date_parser.parse(element[attr])
                                except:
                                    continue
                        
                        # Try text content
                        text = element.get_text(strip=True)
                        if text:
                            try:
                                from dateutil import parser as date_parser
                                return date_parser.parse(text)
                            except:
                                continue
            except Exception as e:
                logger.debug(f"Timestamp selector {selector} failed: {e}")
                continue
        
        # Try to find timestamp in URL (common pattern)
        try:
            import re
            from urllib.parse import urlparse
            
            parsed_url = urlparse(self.base_url or "")
            path = parsed_url.path
            
            # Look for date patterns in URL path
            date_patterns = [
                r'/(\d{4})/(\d{1,2})/(\d{1,2})/',  # /2024/01/15/
                r'/(\d{4})-(\d{1,2})-(\d{1,2})/',  # /2024-01-15/
                r'(\d{4})(\d{2})(\d{2})',          # 20240115
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, path)
                if match:
                    try:
                        if len(match.groups()) == 3:
                            year, month, day = match.groups()
                            return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
                    except:
                        continue
        except:
            pass
        
        return None
    
    def _is_news_content(self, content: str, title: str = "") -> bool:
        """Check if content appears to be news content."""
        
        if not content:
            return False
        
        content_lower = content.lower()
        title_lower = (title or "").lower()
        combined_text = f"{content_lower} {title_lower}"
        
        # Check for news indicators
        news_score = 0
        
        # Positive indicators
        for indicator in self.news_indicators:
            if indicator in combined_text:
                news_score += 1
        
        # Check for news-like structure
        if any(phrase in content_lower for phrase in [
            'according to', 'sources said', 'reported that', 'officials said',
            'government announced', 'minister said', 'police said', 'court said'
        ]):
            news_score += 2
        
        # Check for Indian context
        if any(term in combined_text for term in [
            'india', 'indian', 'delhi', 'mumbai', 'bangalore', 'chennai',
            'kolkata', 'hyderabad', 'pune', 'ahmedabad'
        ]):
            news_score += 1
        
        # Negative indicators (likely not news)
        if any(phrase in content_lower for phrase in [
            'buy now', 'click here', 'subscribe', 'advertisement',
            'sponsored content', 'promoted post'
        ]):
            news_score -= 2
        
        return news_score >= 2
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status with news-specific information."""
        
        health_status = await super().get_health_status()
        
        # Add news-specific health information
        health_status.update({
            'crawler_type': 'news',
            'supported_sites': len(self.indian_news_patterns),
            'news_patterns_loaded': True
        })
        
        return health_status


# Utility functions for news crawling
def create_news_crawler_config(base_url: str, **kwargs) -> Dict[str, Any]:
    """Create a news crawler configuration with sensible defaults.
    
    Args:
        base_url: Base URL of the news site
        **kwargs: Additional configuration options
        
    Returns:
        Configuration dictionary
    """
    config = {
        'source_type': 'crawler',
        'base_url': base_url,
        'respect_robots': True,
        'rate_limit': 20,  # Conservative rate limiting
        'min_content_length': 200,
        'max_content_length': 15000,
        'timeout': 30,
        'max_pages': 5,  # Limit pages per crawl
        'enabled': True,
        'priority': 'medium'
    }
    
    config.update(kwargs)
    return config


# Pre-configured news site configurations
INDIAN_NEWS_SITES = {
    'news18_crawler': create_news_crawler_config(
        'https://www.news18.com',
        target_urls=[
            'https://www.news18.com/india/',
            'https://www.news18.com/politics/'
        ],
        source_id='news18_crawler',
        feed_title='News18 India (Crawler)',
        category='news',
        language='en',
        reliability_score=0.75
    ),
    
    'firstpost_crawler': create_news_crawler_config(
        'https://www.firstpost.com',
        target_urls=[
            'https://www.firstpost.com/india',
            'https://www.firstpost.com/politics'
        ],
        source_id='firstpost_crawler',
        feed_title='Firstpost (Crawler)',
        category='news',
        language='en',
        reliability_score=0.8
    ),
    
    'scroll_crawler': create_news_crawler_config(
        'https://scroll.in',
        target_urls=[
            'https://scroll.in/latest',
            'https://scroll.in/article'
        ],
        source_id='scroll_crawler',
        feed_title='Scroll.in (Crawler)',
        category='news',
        language='en',
        reliability_score=0.85
    )
}