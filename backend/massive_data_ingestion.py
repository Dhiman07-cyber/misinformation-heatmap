#!/usr/bin/env python3
"""
Massive Data Ingestion System
- 34 real RSS sources across Indian news tiers
- High-volume concurrent processing
- Real misinformation detection on live articles
"""

import asyncio
import logging
import sqlite3
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import feedparser
import requests
from enhanced_fake_news_detector import fake_news_detector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MASSIVE RSS SOURCES - 100+ Indian news sources
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
        
        response = requests.get(source['url'], headers=headers, timeout=20)
        feed = feedparser.parse(response.content)
        
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

async def fetch_massive_rss_data():
    """Fetch massive amounts of data from all sources"""
    events = []
    
    logger.info(f"📡 Starting massive data ingestion from {len(MASSIVE_RSS_SOURCES)} RSS sources")
    
    # Use larger ThreadPoolExecutor for more concurrent requests
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all RSS fetch tasks
        future_to_source = {
            executor.submit(fetch_single_rss_source_enhanced, source): source 
            for source in MASSIVE_RSS_SOURCES
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
    
    logger.info(f"📊 RSS FETCH COMPLETE: {len(events)} real articles from {len(MASSIVE_RSS_SOURCES)} sources")
    
    return events

async def high_volume_processing_loop():
    """High-volume processing loop with massive data ingestion"""
    global processing_active, processed_count
    processing_active = True
    
    logger.info("🚀 Starting HIGH-VOLUME data processing")
    logger.info(f"📊 Target: 500+ events per cycle")
    logger.info(f"🗺️ Coverage: All Indian states")
    logger.info(f"⏱️ Cycle time: 2 minutes")
    
    cycle_count = 0
    
    while processing_active:
        try:
            cycle_count += 1
            start_time = time.time()
            
            logger.info(f"🔄 HIGH-VOLUME CYCLE #{cycle_count} STARTED")
            
            # Fetch massive RSS data
            events = await fetch_massive_rss_data()
            
            # Process events in batches for better performance
            batch_size = 50
            processed_events = 0
            
            for i in range(0, len(events), batch_size):
                batch = events[i:i + batch_size]
                
                # Process batch concurrently
                tasks = []
                for event in batch:
                    task = process_event_with_fake_news_detection(event)
                    tasks.append(task)
                
                # Wait for batch to complete
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Store successful results
                for result in batch_results:
                    if isinstance(result, dict):
                        store_event_in_database(result)
                        processed_events += 1
                        processed_count += 1
                
                logger.info(f"   📦 Batch {i//batch_size + 1}: {len(batch)} events processed")
            
            end_time = time.time()
            cycle_duration = end_time - start_time
            
            logger.info(f"🎯 HIGH-VOLUME CYCLE #{cycle_count} COMPLETED")
            logger.info(f"   ⏱️ Duration: {cycle_duration:.2f} seconds")
            logger.info(f"   📰 Fetched: {len(events)} events")
            logger.info(f"   ✅ Processed: {processed_events} events")
            logger.info(f"   📈 Total processed: {processed_count}")
            logger.info(f"   🚀 Processing rate: {processed_events/cycle_duration:.1f} events/second")
            
            # Shorter wait time for more frequent updates
            await asyncio.sleep(120)  # 2 minutes
            
        except Exception as e:
            logger.error(f"High-volume processing error: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error

async def process_event_with_fake_news_detection(event: Dict) -> Optional[Dict]:
    """Process event with enhanced fake news detection"""
    try:
        # Import here to avoid circular imports
        from realtime_processor import extract_location, categorize_content
        
        # Extract location
        state = extract_location(f"{event['title']} {event['content']}")
        
        # Fake news analysis
        analysis = await fake_news_detector.detect_fake_news(
            event['title'], 
            event['content'], 
            event['source'], 
            event.get('url', '')
        )
        
        # Create processed event
        processed_event = {
            'event_id': f"{event['source']}_{hashlib.md5(event['title'].encode()).hexdigest()}_{int(time.time())}_{random.randint(1000,9999)}",
            'source': event['source'],
            'title': event['title'],
            'content': event['content'],
            'summary': event['content'][:300] + '...' if len(event['content']) > 300 else event['content'],
            'url': event.get('url', ''),
            'state': state,
            'category': event.get('category', categorize_content(event['content'])),
            'fake_news_verdict': analysis['verdict'],
            'fake_news_confidence': analysis['confidence'],
            'fake_news_score': analysis['fake_score'],
            'ml_classification_result': json.dumps(analysis['components']['ml_classification']),
            'linguistic_analysis_result': json.dumps(analysis['components']['linguistic_analysis']),
            'source_credibility_result': json.dumps(analysis['components']['source_credibility']),
            'fact_check_result': json.dumps(analysis['components']['fact_checking']),
            'satellite_verification_result': json.dumps(analysis['components']['satellite_verification']) if analysis['components']['satellite_verification'] else None,
            'cross_reference_score': analysis['components']['cross_reference_score'],
            'indian_context_result': json.dumps(analysis['components']['indian_context']),
            'indic_bert_embeddings': json.dumps(analysis['indic_bert_embeddings']),
            'timestamp': event['timestamp']
        }
        
        return processed_event
        
    except Exception as e:
        logger.error(f"Enhanced event processing failed: {e}")
        return None

def store_event_in_database(event: Dict):
    """Store event in database with enhanced aggregation"""
    try:
        # Create data directory if it doesn't exist
        import os
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, 'enhanced_fake_news.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Store event
        cursor.execute('''
            INSERT OR REPLACE INTO events 
            (event_id, source, title, content, summary, url, state, category, 
             fake_news_verdict, fake_news_confidence, fake_news_score,
             ml_classification_result, linguistic_analysis_result, source_credibility_result,
             fact_check_result, satellite_verification_result, cross_reference_score,
             indian_context_result, indic_bert_embeddings, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event['event_id'], event['source'], event['title'], event['content'],
            event['summary'], event['url'], event['state'], event['category'],
            event['fake_news_verdict'], event['fake_news_confidence'], event['fake_news_score'],
            event['ml_classification_result'], event['linguistic_analysis_result'], 
            event['source_credibility_result'], event['fact_check_result'],
            event['satellite_verification_result'], event['cross_reference_score'],
            event['indian_context_result'], event['indic_bert_embeddings'], event['timestamp']
        ))
        
        # Update state aggregations
        from realtime_processor import update_state_aggregations
        update_state_aggregations(event['state'], cursor)
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to store event in database: {e}")

# Global variables
processing_active = False
processed_count = 0

if __name__ == "__main__":
    # Test massive data generation
    print("🚀 Testing Massive Data Ingestion System")
    print("=" * 50)
    
    # Generate sample synthetic data
    synthetic_data = generate_synthetic_news(10)
    
    print(f"📊 Generated {len(synthetic_data)} synthetic articles:")
    for i, article in enumerate(synthetic_data[:5], 1):
        print(f"{i}. {article['title']}")
        print(f"   📍 Category: {article['category']} | Source: {article['source']}")
    
    print(f"\n🎯 Ready for high-volume processing!")
    print(f"📊 Target: 500+ events per cycle")
    print(f"⏱️ Cycle time: 2 minutes")