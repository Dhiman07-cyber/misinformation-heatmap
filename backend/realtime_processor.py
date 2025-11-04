#!/usr/bin/env python3
"""
Real-time Data Processing Pipeline
- RSS ingestion from Indian news sources
- Fake news detection processing
- Database storage and state aggregation
"""

import asyncio
import logging
import sqlite3
import json
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import feedparser
import requests
from enhanced_fake_news_detector import fake_news_detector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RSS Sources for Indian news
RSS_SOURCES = [
    {"name": "Times of India", "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "reliability": 0.8},
    {"name": "Hindustan Times", "url": "https://www.hindustantimes.com/feeds/rss/india-news/index.xml", "reliability": 0.8},
    {"name": "Indian Express", "url": "https://indianexpress.com/feed/", "reliability": 0.85},
    {"name": "NDTV", "url": "https://feeds.feedburner.com/NDTV-LatestNews", "reliability": 0.8},
    {"name": "News18", "url": "https://www.news18.com/rss/india.xml", "reliability": 0.7},
    {"name": "Zee News", "url": "https://zeenews.india.com/rss/india-national-news.xml", "reliability": 0.7},
    {"name": "Business Standard", "url": "https://www.business-standard.com/rss/home_page_top_stories.rss", "reliability": 0.75},
    {"name": "Deccan Herald", "url": "https://www.deccanherald.com/rss-feed/", "reliability": 0.75},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss", "reliability": 0.9},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms", "reliability": 0.8},
    {"name": "India Today", "url": "https://www.indiatoday.in/rss/1206578", "reliability": 0.8},
    {"name": "Outlook", "url": "https://www.outlookindia.com/rss/main/", "reliability": 0.75},
]

# Indian states for location mapping
INDIAN_STATES = {
    "Andhra Pradesh": {"lat": 15.9129, "lng": 79.7400, "population": 49386799, "capital": "Amaravati"},
    "Arunachal Pradesh": {"lat": 28.2180, "lng": 94.7278, "population": 1382611, "capital": "Itanagar"},
    "Assam": {"lat": 26.2006, "lng": 92.9376, "population": 31169272, "capital": "Dispur"},
    "Bihar": {"lat": 25.0961, "lng": 85.3131, "population": 103804637, "capital": "Patna"},
    "Chhattisgarh": {"lat": 21.2787, "lng": 81.8661, "population": 25540196, "capital": "Raipur"},
    "Delhi": {"lat": 28.7041, "lng": 77.1025, "population": 16787941, "capital": "New Delhi"},
    "Goa": {"lat": 15.2993, "lng": 74.1240, "population": 1457723, "capital": "Panaji"},
    "Gujarat": {"lat": 23.0225, "lng": 72.5714, "population": 60383628, "capital": "Gandhinagar"},
    "Haryana": {"lat": 29.0588, "lng": 76.0856, "population": 25353081, "capital": "Chandigarh"},
    "Himachal Pradesh": {"lat": 31.1048, "lng": 77.1734, "population": 6864602, "capital": "Shimla"},
    "Jharkhand": {"lat": 23.6102, "lng": 85.2799, "population": 32966238, "capital": "Ranchi"},
    "Karnataka": {"lat": 15.3173, "lng": 75.7139, "population": 61130704, "capital": "Bengaluru"},
    "Kerala": {"lat": 10.8505, "lng": 76.2711, "population": 33387677, "capital": "Thiruvananthapuram"},
    "Madhya Pradesh": {"lat": 22.9734, "lng": 78.6569, "population": 72597565, "capital": "Bhopal"},
    "Maharashtra": {"lat": 19.7515, "lng": 75.7139, "population": 112372972, "capital": "Mumbai"},
    "Manipur": {"lat": 24.6637, "lng": 93.9063, "population": 2855794, "capital": "Imphal"},
    "Meghalaya": {"lat": 25.4670, "lng": 91.3662, "population": 2964007, "capital": "Shillong"},
    "Mizoram": {"lat": 23.1645, "lng": 92.9376, "population": 1091014, "capital": "Aizawl"},
    "Nagaland": {"lat": 26.1584, "lng": 94.5624, "population": 1980602, "capital": "Kohima"},
    "Odisha": {"lat": 20.9517, "lng": 85.0985, "population": 42000000, "capital": "Bhubaneswar"},
    "Punjab": {"lat": 31.1471, "lng": 75.3412, "population": 27704236, "capital": "Chandigarh"},
    "Rajasthan": {"lat": 27.0238, "lng": 74.2179, "population": 68621012, "capital": "Jaipur"},
    "Sikkim": {"lat": 27.5330, "lng": 88.5122, "population": 607688, "capital": "Gangtok"},
    "Tamil Nadu": {"lat": 11.1271, "lng": 78.6569, "population": 72138958, "capital": "Chennai"},
    "Telangana": {"lat": 18.1124, "lng": 79.0193, "population": 35000000, "capital": "Hyderabad"},
    "Tripura": {"lat": 23.9408, "lng": 91.9882, "population": 3671032, "capital": "Agartala"},
    "Uttar Pradesh": {"lat": 26.8467, "lng": 80.9462, "population": 199581477, "capital": "Lucknow"},
    "Uttarakhand": {"lat": 30.0668, "lng": 79.0193, "population": 10116752, "capital": "Dehradun"},
    "West Bengal": {"lat": 22.9868, "lng": 87.8550, "population": 91347736, "capital": "Kolkata"},
}

# Global variables
processing_active = False
live_events = []
processed_count = 0

def fetch_single_rss_source(source: Dict) -> List[Dict]:
    """Fetch events from a single RSS source"""
    events = []
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(source['url'], headers=headers, timeout=30)
        feed = feedparser.parse(response.content)
        
        # Get latest entries
        for entry in feed.entries[:5]:  # 5 entries per source
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
        logger.error(f"❌ RSS fetch failed for {source['name']}: {e}")
    
    return events

async def fetch_rss_data():
    """Fetch data from all RSS sources"""
    events = []
    
    # Use ThreadPoolExecutor for concurrent RSS fetching
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        
        for source in RSS_SOURCES:
            future = executor.submit(fetch_single_rss_source, source)
            futures.append(future)
        
        # Collect results
        for future in futures:
            try:
                source_events = future.result(timeout=30)
                events.extend(source_events)
            except Exception as e:
                logger.error(f"RSS fetch failed: {e}")
    
    logger.info(f"📊 Fetched {len(events)} events from {len(RSS_SOURCES)} sources")
    return events

def extract_location(text: str) -> str:
    """Extract Indian state from text"""
    text_lower = text.lower()
    
    # State variations and major cities
    state_variations = {
        'maharashtra': ['mumbai', 'pune', 'nagpur', 'nashik', 'aurangabad'],
        'delhi': ['new delhi', 'delhi ncr', 'national capital'],
        'karnataka': ['bangalore', 'bengaluru', 'mysore', 'hubli'],
        'tamil nadu': ['chennai', 'madras', 'coimbatore', 'salem', 'madurai'],
        'west bengal': ['kolkata', 'calcutta', 'howrah', 'durgapur'],
        'uttar pradesh': ['lucknow', 'kanpur', 'agra', 'varanasi', 'allahabad', 'prayagraj'],
        'gujarat': ['ahmedabad', 'surat', 'vadodara', 'rajkot'],
        'rajasthan': ['jaipur', 'jodhpur', 'udaipur', 'kota'],
        'punjab': ['chandigarh', 'amritsar', 'ludhiana', 'jalandhar'],
        'haryana': ['gurgaon', 'gurugram', 'faridabad', 'panipat'],
        'bihar': ['patna', 'gaya', 'muzaffarpur', 'bhagalpur'],
        'odisha': ['bhubaneswar', 'cuttack', 'rourkela'],
        'kerala': ['kochi', 'thiruvananthapuram', 'kozhikode', 'thrissur'],
        'andhra pradesh': ['visakhapatnam', 'vijayawada', 'guntur'],
        'telangana': ['hyderabad', 'secunderabad', 'warangal']
    }
    
    # Check for state names and their cities
    for state, cities in state_variations.items():
        if state in text_lower or any(city in text_lower for city in cities):
            # Convert to proper case
            return ' '.join(word.capitalize() for word in state.split())
    
    # Check for remaining states
    for state in INDIAN_STATES.keys():
        if state.lower() in text_lower:
            return state
    
    # Random fallback for demonstration
    import random
    return random.choice(list(INDIAN_STATES.keys()))

def categorize_content(content: str) -> str:
    """Categorize content into topics"""
    content_lower = content.lower()
    
    categories = {
        'Politics': ['election', 'government', 'minister', 'party', 'vote', 'parliament', 'policy', 'bjp', 'congress'],
        'Health': ['covid', 'vaccine', 'medicine', 'doctor', 'hospital', 'health', 'disease', 'medical'],
        'Technology': ['5g', 'internet', 'app', 'phone', 'digital', 'cyber', 'ai', 'tech', 'smartphone'],
        'Economy': ['rupee', 'inflation', 'price', 'market', 'economy', 'business', 'finance', 'stock'],
        'Social': ['caste', 'religion', 'community', 'protest', 'violence', 'social', 'hindu', 'muslim'],
        'Infrastructure': ['road', 'bridge', 'railway', 'airport', 'construction', 'development', 'metro'],
        'Education': ['school', 'college', 'university', 'student', 'education', 'exam', 'neet', 'jee'],
        'Environment': ['pollution', 'climate', 'environment', 'forest', 'wildlife', 'green', 'carbon'],
        'Sports': ['cricket', 'football', 'hockey', 'olympics', 'ipl', 'sports', 'match', 'tournament'],
        'Entertainment': ['bollywood', 'movie', 'film', 'actor', 'actress', 'celebrity', 'entertainment'],
        'Crime': ['murder', 'rape', 'theft', 'crime', 'police', 'arrest', 'investigation', 'court'],
        'Disaster': ['flood', 'earthquake', 'cyclone', 'fire', 'accident', 'disaster', 'emergency']
    }
    
    # Score each category
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in content_lower)
        if score > 0:
            category_scores[category] = score
    
    # Return category with highest score
    if category_scores:
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    return 'General'



async def process_event(event: Dict) -> Optional[Dict]:
    """Process event with fake news detection"""
    try:
        # Extract location
        state = extract_location(f"{event['title']} {event['content']}")
        
        # Fake news analysis - using real detection
        analysis = await fake_news_detector.detect_fake_news(
            event['title'], 
            event['content'], 
            event['source'], 
            event.get('url', '')
        )
        
        # Create processed event
        processed_event = {
            'event_id': f"{event['source']}_{hashlib.md5(event['title'].encode()).hexdigest()}_{int(time.time())}",
            'source': event['source'],
            'title': event['title'],
            'content': event['content'],
            'summary': event['content'][:300] + '...' if len(event['content']) > 300 else event['content'],
            'url': event.get('url', ''),
            'state': state,
            'category': categorize_content(event['content']),
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
        logger.error(f"Event processing failed: {e}")
        return None

def store_event(event: Dict):
    """Store event in database and update aggregations"""
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
        update_state_aggregations(event['state'], cursor)
        
        # Add to live events
        live_events.append(event)
        if len(live_events) > 200:  # Keep only latest 200 events
            live_events.pop(0)
        
        conn.commit()
        conn.close()
        
        verdict_emoji = "🔴" if event['fake_news_verdict'] == 'fake' else "🟢" if event['fake_news_verdict'] == 'real' else "🟡"
        logger.info(f"✅ Stored: {event['title'][:60]}... | {event['state']} | {verdict_emoji} {event['fake_news_verdict'].upper()} ({event['fake_news_confidence']:.2f})")
        
    except Exception as e:
        logger.error(f"Failed to store event: {e}")

def update_state_aggregations(state: str, cursor):
    """Update state-level aggregations"""
    try:
        # Get recent events for this state (last 24 hours)
        cursor.execute('''
            SELECT fake_news_verdict, fake_news_score, category, title
            FROM events 
            WHERE state = ? AND timestamp >= datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        ''', (state,))
        
        recent_events = cursor.fetchall()
        
        if recent_events:
            # Calculate metrics
            total_events = len(recent_events)
            fake_count = sum(1 for event in recent_events if event[0] == 'fake')
            real_count = sum(1 for event in recent_events if event[0] == 'real')
            uncertain_count = sum(1 for event in recent_events if event[0] == 'uncertain')
            
            scores = [event[1] for event in recent_events]
            avg_score = sum(scores) / len(scores)
            
            # Get trending categories
            categories = [event[2] for event in recent_events]
            category_counts = {}
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            trending_topics = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            trending_topics = [cat for cat, count in trending_topics]
            
            # Get recent headlines
            recent_headlines = [event[3] for event in recent_events[:5]]
            
            # Update aggregations
            cursor.execute('''
                UPDATE state_aggregations 
                SET total_events = ?, fake_news_count = ?, real_news_count = ?, 
                    uncertain_count = ?, avg_fake_score = ?, 
                    trending_topics = ?, recent_headlines = ?, last_updated = CURRENT_TIMESTAMP
                WHERE state = ?
            ''', (
                total_events, fake_count, real_count, uncertain_count, avg_score,
                json.dumps(trending_topics), json.dumps(recent_headlines), state
            ))
            
    except Exception as e:
        logger.error(f"Failed to update state aggregations for {state}: {e}")

async def real_time_processing_loop():
    """Main real-time processing loop"""
    global processing_active, processed_count
    processing_active = True
    
    logger.info("🚀 Starting REAL-TIME fake news detection processing")
    logger.info(f"📊 Monitoring {len(RSS_SOURCES)} RSS sources")
    logger.info(f"🗺️ Covering {len(INDIAN_STATES)} Indian states")
    
    cycle_count = 0
    
    while processing_active:
        try:
            cycle_count += 1
            start_time = time.time()
            
            logger.info(f"🔄 Processing cycle #{cycle_count} started")
            
            # Fetch RSS data
            events = await fetch_rss_data()
            
            # Process events with fake news detection
            processed_events = 0
            for event in events:
                processed_event = await process_event(event)
                if processed_event:
                    store_event(processed_event)
                    processed_events += 1
                    processed_count += 1
            
            end_time = time.time()
            cycle_duration = end_time - start_time
            
            logger.info(f"📊 Cycle #{cycle_count} completed in {cycle_duration:.2f}s")
            logger.info(f"   📰 Fetched: {len(events)} events")
            logger.info(f"   ✅ Processed: {processed_events} events")
            logger.info(f"   🗺️ Live events: {len(live_events)}")
            logger.info(f"   📈 Total processed: {processed_count}")
            
            # Wait 3 minutes before next cycle
            await asyncio.sleep(180)
            
        except Exception as e:
            logger.error(f"Processing loop error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

def get_processing_stats():
    """Get current processing statistics"""
    return {
        'processing_active': processing_active,
        'live_events_count': len(live_events),
        'total_processed': processed_count,
        'live_events': live_events[-10:] if live_events else []  # Latest 10 events
    }

if __name__ == "__main__":
    # Test the processor
    asyncio.run(real_time_processing_loop())