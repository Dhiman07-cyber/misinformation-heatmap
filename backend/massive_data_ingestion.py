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
import gc
from datetime import datetime
import random
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

async def fetch_massive_rss_data():
    """Fetch massive amounts of data from all sources"""
    events = []
    
    logger.info(f"📡 Starting massive data ingestion from {len(MASSIVE_RSS_SOURCES)} RSS sources")
    
    # Use conservative ThreadPoolExecutor to prevent threading overhead / RAM bloat
    with ThreadPoolExecutor(max_workers=5) as executor:
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
            
            # Prune old events to prevent unbounded DB growth
            cleanup_old_events()
            
            # Explicit garbage collection to free any dangling objects from this massive cycle
            gc.collect()
            
            # Shorter wait time for more frequent updates
            await asyncio.sleep(120)  # 2 minutes
            
        except Exception as e:
            logger.error(f"High-volume processing error: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error

def cleanup_old_events():
    """Delete events older than 24 hours to prevent unbounded database growth"""
    try:
        import os
        from db_adapter import get_db_connection
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        db_path = os.path.join(data_dir, 'enhanced_fake_news.db')
        
        # Don't check for db_path if Postgres is used via environ
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM events WHERE timestamp < datetime('now', '-24 hours')")
        # Handle SQLite cursor vs Postgres wrapper differences in reporting deleted rows
        deleted = getattr(cursor, 'rowcount', 0)
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"🧹 Pruned {deleted} old events from database")
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")

async def process_event_with_fake_news_detection(event: Dict) -> Optional[Dict]:
    """Process event with enhanced fake news detection"""
    try:
        # Import here to avoid circular imports
        from realtime_processor import extract_location, categorize_content
        
        # Extract location (may return None if article has no detectable Indian location)
        state = extract_location(f"{event['title']} {event['content']}")
        
        # If state genuinely cannot be determined, mark as 'National' (India-wide story)
        if state is None:
            state = 'National'
        
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
    """Store event in db using the seamless DB adapter."""
    try:
        import os
        from db_adapter import get_db_connection
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        db_path = os.path.join(data_dir, 'enhanced_fake_news.db')
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        # Cast numpy types → native Python types so psycopg2 can serialize them
        confidence = float(event['fake_news_confidence']) if event['fake_news_confidence'] is not None else None
        score      = float(event['fake_news_score'])      if event['fake_news_score']      is not None else None
        cross_ref  = float(event['cross_reference_score'])if event['cross_reference_score']is not None else None

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
            event['fake_news_verdict'], confidence, score,
            event['ml_classification_result'], event['linguistic_analysis_result'], 
            event['source_credibility_result'], event['fact_check_result'],
            event['satellite_verification_result'], cross_ref,
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

def is_processing_active():
    return processing_active

def get_total_processed():
    return processed_count

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