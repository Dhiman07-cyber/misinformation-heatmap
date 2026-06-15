import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests

from .base import DataIngestor

logger = logging.getLogger(__name__)

MASSIVE_RSS_SOURCES = [
    # National English News (Tier 1)
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "reliability": 0.8, "articles": 25},
    {"name": "Hindustan Times", "url": "https://www.hindustantimes.com/feeds/rss/india-news/index.xml", "reliability": 0.8, "articles": 25},
    {"name": "Indian Express", "url": "https://indianexpress.com/feed/", "reliability": 0.85, "articles": 25},
    {"name": "NDTV", "url": "https://feeds.feedburner.com/NDTV-LatestNews", "reliability": 0.8, "articles": 25},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss", "reliability": 0.9, "articles": 25},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "reliability": 0.8, "articles": 25},
    {"name": "Business Standard", "url": "https://www.business-standard.com/rss/home_page_top_stories.rss", "reliability": 0.75, "articles": 20},
    {"name": "Deccan Herald", "url": "https://www.deccanherald.com/rss-feed/", "reliability": 0.75, "articles": 20},
    {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206578", "reliability": 0.8, "articles": 20},
    {"name": "Outlook", "url": "https://www.outlookindia.com/rss/main/", "reliability": 0.75, "articles": 20},
    
    # Regional News (Tier 2)
    {"name": "News18", "url": "https://www.news18.com/rss/india.xml", "reliability": 0.7, "articles": 20},
    {"name": "Zee News", "url": "https://zeenews.india.com/rss/india-national-news.xml", "reliability": 0.7, "articles": 20},
    {"name": "Mumbai Mirror", "url": "https://mumbaimirror.indiatimes.com/rss.cms", "reliability": 0.7, "articles": 15},
    {"name": "Pune Mirror", "url": "https://punemirror.indiatimes.com/rss.cms", "reliability": 0.7, "articles": 15},
    {"name": "Bangalore Mirror", "url": "https://bangaloremirror.indiatimes.com/rss.cms", "reliability": 0.7, "articles": 15},
    {"name": "Delhi Times", "url": "https://timesofindia.indiatimes.com/rss/city/delhi.cms", "reliability": 0.75, "articles": 15},
    {"name": "Chennai Times", "url": "https://timesofindia.indiatimes.com/rss/city/chennai.cms", "reliability": 0.75, "articles": 15},
    {"name": "Kolkata Times", "url": "https://timesofindia.indiatimes.com/rss/city/kolkata.cms", "reliability": 0.75, "articles": 15},
    
    # Alternative/Opinion Sources (Tier 3)
    {"name": "The Wire", "url": "https://thewire.in/feed/", "reliability": 0.6, "articles": 15},
    {"name": "Scroll.in", "url": "https://scroll.in/feed", "reliability": 0.7, "articles": 15},
    {"name": "The Quint", "url": "https://www.thequint.com/rss", "reliability": 0.7, "articles": 15},
    {"name": "News Minute", "url": "https://www.thenewsminute.com/rss.xml", "reliability": 0.75, "articles": 15},
    {"name": "Firstpost", "url": "https://www.firstpost.com/rss/india.xml", "reliability": 0.7, "articles": 15},
    {"name": "LiveMint", "url": "https://www.livemint.com/rss/news", "reliability": 0.8, "articles": 15},
    {"name": "Financial Express", "url": "https://www.financialexpress.com/feed/", "reliability": 0.8, "articles": 15},
    {"name": "OpIndia", "url": "https://www.opindia.com/feed/", "reliability": 0.4, "articles": 15},
    
    # Regional Language Sources (Tier 4)
    {"name": "Deccan Chronicle", "url": "https://www.deccanchronicle.com/rss_feed/", "reliability": 0.7, "articles": 10},
    {"name": "New Indian Express", "url": "https://www.newindianexpress.com/rss/", "reliability": 0.75, "articles": 10},
    {"name": "Telegraph India", "url": "https://www.telegraphindia.com/rss.xml", "reliability": 0.8, "articles": 10},
    {"name": "Asian Age", "url": "https://www.asianage.com/rss/", "reliability": 0.7, "articles": 10},
    
    # Specialized Sources (Tier 5)
    {"name": "Cricbuzz", "url": "https://www.cricbuzz.com/rss-feed/cricket-news", "reliability": 0.8, "articles": 10},
    {"name": "Bollywood Hungama", "url": "https://www.bollywoodhungama.com/rss/news.xml", "reliability": 0.6, "articles": 10},
    {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/business.xml", "reliability": 0.8, "articles": 10},
    {"name": "ET Now", "url": "https://www.etnow.in/rss/", "reliability": 0.75, "articles": 10},
]


def fetch_single_rss_source_enhanced(source: Dict) -> List[Dict]:
    """Enhanced RSS fetching with more articles per source"""
    events = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(source['url'], headers=headers, timeout=20, stream=True)
        response.raise_for_status()
        
        # SAFEGUARD: Limit response payload to 3MB to prevent massive RAM leaks 
        content_bytes = bytearray()
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content_bytes.extend(chunk)
                if len(content_bytes) > 3 * 1024 * 1024:
                    logger.warning(f"⚠️ Feed {source['name']} exceeded 3MB limit. Truncating.")
                    break
                    
        # Convert bytearray → bytes for feedparser compatibility
        content = bytes(content_bytes)
        feed = feedparser.parse(content)

        # Get more entries per source
        max_articles = source.get('articles', 15)
        for entry in feed.entries[:max_articles]:
            event = {
                'source': source['name'],
                'title': entry.title,
                'content': entry.get('summary', entry.get('description', '')),
                'url': entry.get('link', ''),
                'timestamp': datetime.now(),
                'reliability': source['reliability']
            }
            events.append(event)
            
    except Exception as e:
        logger.error(f"❌ Enhanced RSS fetch failed for {source['name']}: {e}")
    
    return events


class RssIngestor(DataIngestor):
    """
    Ingests data from 30+ Indian News RSS Feeds.
    """
    
    def __init__(self, sources: List[Dict] = None):
        self.sources = sources or MASSIVE_RSS_SOURCES

    async def fetch_data(self) -> List[Dict]:
        events = []
        logger.info(f"📡 Starting RSS data ingestion from {len(self.sources)} sources")
        
        # Use conservative ThreadPoolExecutor to prevent threading overhead / RAM bloat
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all RSS fetch tasks
            future_to_source = {
                executor.submit(fetch_single_rss_source_enhanced, source): source 
                for source in self.sources
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_source, timeout=60):
                source = future_to_source[future]
                try:
                    source_events = future.result()
                    events.extend(source_events)
                    logger.info(f"✅ {source['name']}: {len(source_events)} articles")
                except Exception as e:
                    logger.error(f"❌ {source['name']} failed: {e}")
        
        logger.info(f"📊 RSS FETCH COMPLETE: {len(events)} real articles from {len(self.sources)} sources")
        return events
