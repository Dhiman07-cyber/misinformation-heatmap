"""
Local mode data ingestion system for development and testing.
Simulates real-time data feeds using RSS feeds, file-based sources,
and manual test data injection without requiring external API credentials.
"""

import asyncio
import logging
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator
from pathlib import Path
import random
import hashlib

# HTTP client imports
import httpx
import feedparser

# Local imports
from config import config
from models import EventSource, LanguageCode
from processor import RawEvent

# Configure logging
logger = logging.getLogger(__name__)


class LocalNewsIngester:
    """
    Ingests news content from RSS feeds and local sources for development mode.
    Simulates real-time news ingestion without requiring API keys.
    """
    
    def __init__(self):
        self.data_dir = Path(config.data_dir)
        self.cache_dir = self.data_dir / "ingestion_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Indian news RSS feeds (publicly available)
        self.rss_feeds = {
            "times_of_india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
            "hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
            "indian_express": "https://indianexpress.com/section/india/feed/",
            "ndtv": "https://feeds.feedburner.com/ndtvnews-top-stories",
            "zee_news": "https://zeenews.india.com/rss/india-national-news.xml"
        }
        
        # Sample local news data for offline testing
        self.sample_news = self._load_sample_news()
        
    def _load_sample_news(self) -> List[Dict[str, Any]]:
        """Load sample news data for offline testing"""
        return [
            {
                "title": "Heavy rainfall causes flooding in Mumbai suburbs",
                "description": "Several areas in Mumbai experienced waterlogging after heavy monsoon rains. Local authorities are monitoring the situation.",
                "source": "Mumbai News",
                "location": "Mumbai, Maharashtra",
                "category": "disaster"
            },
            {
                "title": "New metro line construction begins in Delhi",
                "description": "Delhi Metro Rail Corporation started construction of a new metro line connecting Dwarka to Gurgaon.",
                "source": "Delhi Metro News",
                "location": "Delhi",
                "category": "infrastructure"
            },
            {
                "title": "Vaccination drive reaches milestone in Karnataka",
                "description": "Karnataka state achieves 80% vaccination coverage as health officials continue awareness campaigns.",
                "source": "Health News Karnataka",
                "location": "Bangalore, Karnataka",
                "category": "health"
            },
            {
                "title": "Forest fire reported in Uttarakhand hills",
                "description": "Forest department teams are working to control a fire that broke out in the hills of Uttarakhand.",
                "source": "Uttarakhand Forest Dept",
                "location": "Uttarakhand",
                "category": "disaster"
            },
            {
                "title": "Tech company announces expansion in Hyderabad",
                "description": "Major technology company plans to hire 5000 employees in new Hyderabad development center.",
                "source": "Tech News India",
                "location": "Hyderabad, Telangana",
                "category": "technology"
            }
        ]
    
    async def ingest_rss_feeds(self, max_articles: int = 50) -> List[RawEvent]:
        """
        Ingest news articles from RSS feeds.
        Falls back to cached data if feeds are unavailable.
        """
        events = []
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for source_name, feed_url in self.rss_feeds.items():
                    try:
                        logger.debug(f"Fetching RSS feed: {source_name}")
                        
                        # Try to fetch RSS feed
                        response = await client.get(feed_url)
                        if response.status_code == 200:
                            feed_events = self._parse_rss_feed(
                                response.text, source_name, max_articles // len(self.rss_feeds)
                            )
                            events.extend(feed_events)
                        else:
                            logger.warning(f"RSS feed {source_name} returned status {response.status_code}")
                            
                    except Exception as e:
                        logger.warning(f"Failed to fetch RSS feed {source_name}: {e}")
                        
                        # Fall back to cached data
                        cached_events = self._get_cached_feed_data(source_name)
                        events.extend(cached_events)
        
        except Exception as e:
            logger.error(f"RSS ingestion failed: {e}")
            
            # Fall back to sample news data
            events = self._generate_sample_events(max_articles)
        
        # If no events were collected, use sample data
        if not events:
            events = self._generate_sample_events(max_articles)
        
        logger.info(f"Ingested {len(events)} news events from RSS feeds")
        return events[:max_articles]
    
    def _parse_rss_feed(self, feed_content: str, source_name: str, max_items: int) -> List[RawEvent]:
        """Parse RSS feed content and convert to RawEvent objects"""
        events = []
        
        try:
            # Use feedparser for robust RSS parsing
            feed = feedparser.parse(feed_content)
            
            for entry in feed.entries[:max_items]:
                try:
                    # Extract basic information
                    title = entry.get('title', '')
                    description = entry.get('description', '') or entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    # Parse publication date
                    pub_date = entry.get('published_parsed')
                    if pub_date:
                        timestamp = datetime(*pub_date[:6])
                    else:
                        timestamp = datetime.utcnow()
                    
                    # Create combined text
                    combined_text = f"{title}. {description}".strip()
                    
                    if len(combined_text) < 20:  # Skip very short articles
                        continue
                    
                    # Extract location hints from content
                    location_hint = self._extract_location_from_text(combined_text)
                    
                    # Create raw event
                    event = RawEvent(
                        source=EventSource.RSS,
                        original_text=combined_text,
                        timestamp=timestamp,
                        metadata={
                            "source_name": source_name,
                            "title": title,
                            "description": description,
                            "url": link,
                            "location_hint": location_hint,
                            "feed_source": "rss"
                        }
                    )
                    
                    events.append(event)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse RSS entry: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Failed to parse RSS feed: {e}")
        
        return events
    
    def _extract_location_from_text(self, text: str) -> str:
        """Extract Indian location hints from news text"""
        text_lower = text.lower()
        
        # Indian cities and states to look for
        locations = [
            "mumbai", "delhi", "bangalore", "hyderabad", "chennai", "kolkata",
            "pune", "ahmedabad", "surat", "jaipur", "lucknow", "kanpur",
            "maharashtra", "karnataka", "tamil nadu", "uttar pradesh", "gujarat",
            "rajasthan", "west bengal", "madhya pradesh", "bihar", "odisha"
        ]
        
        for location in locations:
            if location in text_lower:
                return location.title()
        
        return ""
    
    def _generate_sample_events(self, count: int) -> List[RawEvent]:
        """Generate sample events from predefined news data"""
        events = []
        
        for i in range(min(count, len(self.sample_news) * 3)):  # Allow repetition with variation
            sample = self.sample_news[i % len(self.sample_news)]
            
            # Add some variation to avoid exact duplicates
            variation_suffix = f" (Report #{i+1})" if i >= len(self.sample_news) else ""
            
            # Create timestamp with some randomness (last 24 hours)
            hours_ago = random.randint(0, 24)
            timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
            
            combined_text = f"{sample['title']}{variation_suffix}. {sample['description']}"
            
            event = RawEvent(
                source=EventSource.NEWS,
                original_text=combined_text,
                timestamp=timestamp,
                metadata={
                    "source_name": "sample_news",
                    "title": sample['title'] + variation_suffix,
                    "description": sample['description'],
                    "location_hint": sample['location'],
                    "category": sample['category'],
                    "feed_source": "sample"
                }
            )
            
            events.append(event)
        
        return events
    
    def _get_cached_feed_data(self, source_name: str) -> List[RawEvent]:
        """Get cached RSS feed data as fallback"""
        cache_file = self.cache_dir / f"rss_{source_name}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # Check if cache is not too old (less than 6 hours)
                cache_time = datetime.fromisoformat(cached_data['cached_at'])
                if (datetime.utcnow() - cache_time).seconds < 21600:  # 6 hours
                    
                    events = []
                    for item in cached_data['items'][:10]:  # Limit cached items
                        event = RawEvent(
                            source=EventSource.RSS,
                            original_text=item['text'],
                            timestamp=datetime.fromisoformat(item['timestamp']),
                            metadata=item['metadata']
                        )
                        events.append(event)
                    
                    logger.info(f"Using cached data for {source_name}")
                    return events
                    
            except Exception as e:
                logger.warning(f"Failed to load cached data for {source_name}: {e}")
        
        return []
    
    async def ingest_from_file(self, file_path: str) -> List[RawEvent]:
        """Ingest events from a local file (CSV or JSON)"""
        events = []
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return events
        
        try:
            if file_path.suffix.lower() == '.csv':
                events = self._parse_csv_file(file_path)
            elif file_path.suffix.lower() == '.json':
                events = self._parse_json_file(file_path)
            else:
                logger.error(f"Unsupported file format: {file_path.suffix}")
        
        except Exception as e:
            logger.error(f"Failed to ingest from file {file_path}: {e}")
        
        logger.info(f"Ingested {len(events)} events from file: {file_path}")
        return events
    
    def _parse_csv_file(self, file_path: Path) -> List[RawEvent]:
        """Parse CSV file containing news data"""
        events = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Expected columns: text, timestamp, source, location
                    text = row.get('text', '').strip()
                    if not text:
                        continue
                    
                    # Parse timestamp
                    timestamp_str = row.get('timestamp', '')
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                        except:
                            timestamp = datetime.utcnow()
                    else:
                        timestamp = datetime.utcnow()
                    
                    event = RawEvent(
                        source=EventSource.MANUAL,
                        original_text=text,
                        timestamp=timestamp,
                        metadata={
                            "source_name": row.get('source', 'csv_file'),
                            "location_hint": row.get('location', ''),
                            "category": row.get('category', ''),
                            "feed_source": "csv_file"
                        }
                    )
                    
                    events.append(event)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse CSV row: {e}")
                    continue
        
        return events
    
    def _parse_json_file(self, file_path: Path) -> List[RawEvent]:
        """Parse JSON file containing news data"""
        events = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single object and array of objects
        if isinstance(data, dict):
            data = [data]
        
        for item in data:
            try:
                text = item.get('text', '').strip()
                if not text:
                    continue
                
                # Parse timestamp
                timestamp_str = item.get('timestamp', '')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str)
                    except:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
                
                event = RawEvent(
                    source=EventSource.MANUAL,
                    original_text=text,
                    timestamp=timestamp,
                    metadata={
                        "source_name": item.get('source', 'json_file'),
                        "location_hint": item.get('location', ''),
                        "category": item.get('category', ''),
                        "feed_source": "json_file",
                        **{k: v for k, v in item.items() if k not in ['text', 'timestamp', 'source', 'location', 'category']}
                    }
                )
                
                events.append(event)
                
            except Exception as e:
                logger.warning(f"Failed to parse JSON item: {e}")
                continue
        
        return events


class LocalSocialMediaIngester:
    """
    Simulates social media content ingestion for local development.
    Generates realistic social media posts without requiring API access.
    """
    
    def __init__(self):
        self.data_dir = Path(config.data_dir)
        
        # Sample social media templates
        self.social_templates = {
            "twitter": [
                "Breaking: {event} in {location}! #BreakingNews #{location_tag}",
                "Urgent update: {event} reported in {location}. Stay safe everyone! 🙏",
                "Can't believe {event} is happening in {location} right now. Thoughts and prayers 💭",
                "ALERT: {event} in {location}. Local authorities responding. #Alert #{location_tag}",
                "Just heard about {event} in {location}. Hope everyone is okay! 😟"
            ],
            "facebook": [
                "Friends in {location}, please be careful! There are reports of {event} in the area.",
                "Sharing this important update: {event} has been reported in {location}. Please stay informed.",
                "Concerned about the {event} situation in {location}. Sending thoughts to everyone affected.",
                "Update from {location}: {event} is currently ongoing. Please follow official sources for updates.",
                "Please share: {event} reported in {location}. Everyone in the area should take precautions."
            ]
        }
        
        # Sample events for social media
        self.social_events = [
            {"event": "heavy flooding", "location": "Mumbai", "location_tag": "Mumbai"},
            {"event": "traffic disruption", "location": "Delhi", "location_tag": "Delhi"},
            {"event": "power outage", "location": "Bangalore", "location_tag": "Bangalore"},
            {"event": "water shortage", "location": "Chennai", "location_tag": "Chennai"},
            {"event": "road construction", "location": "Pune", "location_tag": "Pune"},
            {"event": "festival celebrations", "location": "Kolkata", "location_tag": "Kolkata"},
            {"event": "metro service disruption", "location": "Hyderabad", "location_tag": "Hyderabad"},
            {"event": "air quality concerns", "location": "Gurgaon", "location_tag": "Gurgaon"}
        ]
    
    async def generate_social_media_posts(self, count: int = 20) -> List[RawEvent]:
        """Generate realistic social media posts for testing"""
        events = []
        
        for i in range(count):
            # Choose random platform and template
            platform = random.choice(["twitter", "facebook"])
            template = random.choice(self.social_templates[platform])
            event_data = random.choice(self.social_events)
            
            # Generate post text
            post_text = template.format(**event_data)
            
            # Add some variation
            if random.random() < 0.3:  # 30% chance of adding extra content
                extras = [
                    " Please RT to spread awareness!",
                    " #StaySafe #India",
                    " More updates to follow...",
                    " Source: Local news reports",
                    " Verified by multiple sources"
                ]
                post_text += random.choice(extras)
            
            # Generate timestamp (last 12 hours)
            hours_ago = random.uniform(0, 12)
            timestamp = datetime.utcnow() - timedelta(hours=hours_ago)
            
            # Generate engagement metrics
            engagement = self._generate_engagement_metrics(platform)
            
            event = RawEvent(
                source=EventSource.TWITTER if platform == "twitter" else EventSource.FACEBOOK,
                original_text=post_text,
                timestamp=timestamp,
                metadata={
                    "platform": platform,
                    "location_hint": event_data["location"],
                    "engagement_metrics": engagement,
                    "user_id": f"user_{random.randint(1000, 9999)}",
                    "post_id": f"post_{random.randint(100000, 999999)}",
                    "feed_source": "social_simulation"
                },
                engagement_metrics=engagement
            )
            
            events.append(event)
        
        logger.info(f"Generated {len(events)} social media posts")
        return events
    
    def _generate_engagement_metrics(self, platform: str) -> Dict[str, int]:
        """Generate realistic engagement metrics for social media posts"""
        if platform == "twitter":
            return {
                "likes": random.randint(0, 500),
                "retweets": random.randint(0, 100),
                "replies": random.randint(0, 50),
                "shares": random.randint(0, 100)
            }
        else:  # facebook
            return {
                "likes": random.randint(0, 200),
                "shares": random.randint(0, 50),
                "comments": random.randint(0, 30),
                "reactions": random.randint(0, 150)
            }


class ManualTestDataInjector:
    """
    Allows manual injection of test data for development and testing purposes.
    Provides predefined test scenarios and custom data injection capabilities.
    """
    
    def __init__(self):
        self.test_scenarios = self._load_test_scenarios()
    
    def _load_test_scenarios(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load predefined test scenarios for different types of misinformation"""
        return {
            "disaster_scenarios": [
                {
                    "text": "BREAKING: Massive earthquake hits Delhi, buildings collapsing everywhere! Magnitude 8.5 confirmed by seismic centers.",
                    "location": "Delhi",
                    "category": "disaster",
                    "expected_reality": "low"  # Likely false - no recent major earthquakes in Delhi
                },
                {
                    "text": "Severe flooding in Mumbai suburbs after unprecedented rainfall. Water levels rising rapidly in Andheri and Bandra areas.",
                    "location": "Mumbai, Maharashtra", 
                    "category": "disaster",
                    "expected_reality": "high"  # Plausible - Mumbai does experience monsoon flooding
                },
                {
                    "text": "Forest fires spreading rapidly across Uttarakhand hills. Multiple villages evacuated as flames approach residential areas.",
                    "location": "Uttarakhand",
                    "category": "disaster", 
                    "expected_reality": "medium"  # Possible - forest fires do occur in hill regions
                }
            ],
            "health_scenarios": [
                {
                    "text": "COVID vaccine contains microchips for government surveillance. Doctors in Bangalore hospital confirm chip detection in patients.",
                    "location": "Bangalore, Karnataka",
                    "category": "health",
                    "expected_reality": "very_low"  # Classic conspiracy theory
                },
                {
                    "text": "New variant of COVID-19 detected in Kerala. Health ministry issues advisory for increased testing and precautions.",
                    "location": "Kerala",
                    "category": "health",
                    "expected_reality": "medium"  # Plausible health update
                }
            ],
            "political_scenarios": [
                {
                    "text": "Election fraud discovered in Maharashtra constituency. EVMs found to be hacked, results being manipulated by external forces.",
                    "location": "Maharashtra",
                    "category": "politics",
                    "expected_reality": "low"  # Unsubstantiated fraud claims
                },
                {
                    "text": "New infrastructure project announced for connecting rural areas in Rajasthan. Government allocates budget for road development.",
                    "location": "Rajasthan",
                    "category": "politics",
                    "expected_reality": "high"  # Typical government announcement
                }
            ]
        }
    
    def inject_test_scenario(self, scenario_type: str, scenario_index: int = 0) -> RawEvent:
        """Inject a specific test scenario"""
        if scenario_type not in self.test_scenarios:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        
        scenarios = self.test_scenarios[scenario_type]
        if scenario_index >= len(scenarios):
            raise ValueError(f"Scenario index {scenario_index} out of range for {scenario_type}")
        
        scenario = scenarios[scenario_index]
        
        event = RawEvent(
            source=EventSource.MANUAL,
            original_text=scenario["text"],
            timestamp=datetime.utcnow(),
            metadata={
                "source_name": "test_injection",
                "location_hint": scenario["location"],
                "category": scenario["category"],
                "expected_reality": scenario["expected_reality"],
                "scenario_type": scenario_type,
                "scenario_index": scenario_index,
                "feed_source": "manual_test"
            }
        )
        
        return event
    
    def inject_custom_event(self, text: str, location: str = "", 
                          category: str = "", metadata: Dict[str, Any] = None) -> RawEvent:
        """Inject a custom test event"""
        if metadata is None:
            metadata = {}
        
        event = RawEvent(
            source=EventSource.MANUAL,
            original_text=text,
            timestamp=datetime.utcnow(),
            metadata={
                "source_name": "custom_injection",
                "location_hint": location,
                "category": category,
                "feed_source": "manual_custom",
                **metadata
            }
        )
        
        return event
    
    def get_available_scenarios(self) -> Dict[str, List[str]]:
        """Get list of available test scenarios"""
        scenarios = {}
        for scenario_type, scenario_list in self.test_scenarios.items():
            scenarios[scenario_type] = [
                f"{i}: {scenario['text'][:100]}..." 
                for i, scenario in enumerate(scenario_list)
            ]
        return scenarios


class LocalIngestionManager:
    """
    Main manager for local mode data ingestion.
    Coordinates news, social media, and manual data sources.
    """
    
    def __init__(self):
        self.news_ingester = LocalNewsIngester()
        self.social_ingester = LocalSocialMediaIngester()
        self.test_injector = ManualTestDataInjector()
        
    async def ingest_all_sources(self, max_events: int = 100) -> List[RawEvent]:
        """Ingest from all available local sources"""
        all_events = []
        
        try:
            # Ingest news (60% of events)
            news_count = int(max_events * 0.6)
            news_events = await self.news_ingester.ingest_rss_feeds(news_count)
            all_events.extend(news_events)
            
            # Ingest social media (30% of events)
            social_count = int(max_events * 0.3)
            social_events = await self.social_ingester.generate_social_media_posts(social_count)
            all_events.extend(social_events)
            
            # Add some test scenarios (10% of events)
            test_count = max_events - len(all_events)
            if test_count > 0:
                test_events = self._generate_test_events(test_count)
                all_events.extend(test_events)
            
        except Exception as e:
            logger.error(f"Failed to ingest from all sources: {e}")
        
        # Sort by timestamp (most recent first)
        all_events.sort(key=lambda x: x.timestamp, reverse=True)
        
        logger.info(f"Total ingested events: {len(all_events)}")
        return all_events[:max_events]
    
    def _generate_test_events(self, count: int) -> List[RawEvent]:
        """Generate test events from predefined scenarios"""
        events = []
        
        scenario_types = list(self.test_injector.test_scenarios.keys())
        
        for i in range(count):
            scenario_type = scenario_types[i % len(scenario_types)]
            scenarios = self.test_injector.test_scenarios[scenario_type]
            scenario_index = (i // len(scenario_types)) % len(scenarios)
            
            try:
                event = self.test_injector.inject_test_scenario(scenario_type, scenario_index)
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to generate test event: {e}")
        
        return events
    
    async def ingest_from_source(self, source_type: str, **kwargs) -> List[RawEvent]:
        """Ingest from a specific source type"""
        if source_type == "rss":
            max_articles = kwargs.get("max_articles", 20)
            return await self.news_ingester.ingest_rss_feeds(max_articles)
        
        elif source_type == "social":
            count = kwargs.get("count", 10)
            return await self.social_ingester.generate_social_media_posts(count)
        
        elif source_type == "file":
            file_path = kwargs.get("file_path")
            if not file_path:
                raise ValueError("file_path required for file ingestion")
            return await self.news_ingester.ingest_from_file(file_path)
        
        elif source_type == "test":
            scenario_type = kwargs.get("scenario_type", "disaster_scenarios")
            scenario_index = kwargs.get("scenario_index", 0)
            event = self.test_injector.inject_test_scenario(scenario_type, scenario_index)
            return [event]
        
        elif source_type == "custom":
            text = kwargs.get("text")
            if not text:
                raise ValueError("text required for custom injection")
            location = kwargs.get("location", "")
            category = kwargs.get("category", "")
            metadata = kwargs.get("metadata", {})
            event = self.test_injector.inject_custom_event(text, location, category, metadata)
            return [event]
        
        else:
            raise ValueError(f"Unknown source type: {source_type}")


# Global ingestion manager instance
local_ingestion_manager = LocalIngestionManager()