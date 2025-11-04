#!/usr/bin/env python3
"""
Configuration for major Indian news outlets RSS feeds.
Comprehensive list of reliable news sources across India.
"""

from typing import Dict, List, Any

# Major Indian news outlets with RSS feeds
INDIAN_NEWS_OUTLETS: Dict[str, Dict[str, Any]] = {
    
    # National English News
    'times_of_india': {
        'source_id': 'times_of_india',
        'feed_url': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
        'feed_title': 'Times of India - Top Stories',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 300,  # 5 minutes
        'enabled': True
    },
    
    'hindu_national': {
        'source_id': 'hindu_national',
        'feed_url': 'https://www.thehindu.com/news/national/feeder/default.rss',
        'feed_title': 'The Hindu - National News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 300,
        'enabled': True
    },
    
    'indian_express': {
        'source_id': 'indian_express',
        'feed_url': 'https://indianexpress.com/section/india/feed/',
        'feed_title': 'Indian Express - India News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.85,
        'fetch_interval': 300,
        'enabled': True
    },
    
    'ndtv_news': {
        'source_id': 'ndtv_news',
        'feed_url': 'https://feeds.feedburner.com/NDTV-LatestNews',
        'feed_title': 'NDTV Latest News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 300,
        'enabled': True
    },
    
    'hindustan_times': {
        'source_id': 'hindustan_times',
        'feed_url': 'https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml',
        'feed_title': 'Hindustan Times - India News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 300,
        'enabled': True
    },
    
    'news18_india': {
        'source_id': 'news18_india',
        'feed_url': 'https://www.news18.com/rss/india.xml',
        'feed_title': 'News18 India',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.75,
        'fetch_interval': 300,
        'enabled': True
    },
    
    'india_today': {
        'source_id': 'india_today',
        'feed_url': 'https://www.indiatoday.in/rss/1206514',
        'feed_title': 'India Today - Latest News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 300,
        'enabled': True
    },
    
    # Regional English News
    'deccan_herald': {
        'source_id': 'deccan_herald',
        'feed_url': 'https://www.deccanherald.com/rss-feed',
        'feed_title': 'Deccan Herald',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 600,  # 10 minutes
        'enabled': True
    },
    
    'telegraph_india': {
        'source_id': 'telegraph_india',
        'feed_url': 'https://www.telegraphindia.com/rss.xml',
        'feed_title': 'The Telegraph India',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.85,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'mint_news': {
        'source_id': 'mint_news',
        'feed_url': 'https://www.livemint.com/rss/news',
        'feed_title': 'Mint News',
        'category': 'news',
        'language': 'en',
        'reliability_score': 0.85,
        'fetch_interval': 600,
        'enabled': True
    },
    
    # Business News
    'economic_times': {
        'source_id': 'economic_times',
        'feed_url': 'https://economictimes.indiatimes.com/rssfeedsdefault.cms',
        'feed_title': 'Economic Times',
        'category': 'business',
        'language': 'en',
        'reliability_score': 0.85,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'business_standard': {
        'source_id': 'business_standard',
        'feed_url': 'https://www.business-standard.com/rss/latest.rss',
        'feed_title': 'Business Standard',
        'category': 'business',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 600,
        'enabled': True
    },
    
    # Regional Language News (Hindi)
    'dainik_bhaskar': {
        'source_id': 'dainik_bhaskar',
        'feed_url': 'https://www.bhaskar.com/rss-feed/1061/',
        'feed_title': 'Dainik Bhaskar',
        'category': 'news',
        'language': 'hi',
        'reliability_score': 0.75,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'amar_ujala': {
        'source_id': 'amar_ujala',
        'feed_url': 'https://www.amarujala.com/rss/breaking-news.xml',
        'feed_title': 'Amar Ujala',
        'category': 'news',
        'language': 'hi',
        'reliability_score': 0.75,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'jagran': {
        'source_id': 'jagran',
        'feed_url': 'https://www.jagran.com/rss/news.xml',
        'feed_title': 'Dainik Jagran',
        'category': 'news',
        'language': 'hi',
        'reliability_score': 0.75,
        'fetch_interval': 600,
        'enabled': True
    },
    
    # State-specific News Sources
    'maharashtra_times': {
        'source_id': 'maharashtra_times',
        'feed_url': 'https://maharashtratimes.com/rss.cms',
        'feed_title': 'Maharashtra Times',
        'category': 'regional',
        'language': 'mr',
        'reliability_score': 0.75,
        'fetch_interval': 900,  # 15 minutes
        'enabled': True
    },
    
    'anandabazar': {
        'source_id': 'anandabazar',
        'feed_url': 'https://www.anandabazar.com/rss.xml',
        'feed_title': 'Anandabazar Patrika',
        'category': 'regional',
        'language': 'bn',
        'reliability_score': 0.8,
        'fetch_interval': 900,
        'enabled': True
    },
    
    'dinamalar': {
        'source_id': 'dinamalar',
        'feed_url': 'https://www.dinamalar.com/rss_feed/rss_tamil_news.xml',
        'feed_title': 'Dinamalar',
        'category': 'regional',
        'language': 'ta',
        'reliability_score': 0.75,
        'fetch_interval': 900,
        'enabled': True
    },
    
    'eenadu': {
        'source_id': 'eenadu',
        'feed_url': 'https://www.eenadu.net/rss/telangana-news.xml',
        'feed_title': 'Eenadu Telugu',
        'category': 'regional',
        'language': 'te',
        'reliability_score': 0.75,
        'fetch_interval': 900,
        'enabled': True
    },
    
    'malayala_manorama': {
        'source_id': 'malayala_manorama',
        'feed_url': 'https://www.manoramaonline.com/rss/news.xml',
        'feed_title': 'Malayala Manorama',
        'category': 'regional',
        'language': 'ml',
        'reliability_score': 0.8,
        'fetch_interval': 900,
        'enabled': True
    },
    
    'divya_bhaskar': {
        'source_id': 'divya_bhaskar',
        'feed_url': 'https://www.divyabhaskar.co.in/rss/gujarat-news.xml',
        'feed_title': 'Divya Bhaskar Gujarat',
        'category': 'regional',
        'language': 'gu',
        'reliability_score': 0.75,
        'fetch_interval': 900,
        'enabled': True
    },
    
    # Fact-checking Organizations
    'alt_news': {
        'source_id': 'alt_news',
        'feed_url': 'https://www.altnews.in/feed/',
        'feed_title': 'Alt News',
        'category': 'fact_check',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'boom_live': {
        'source_id': 'boom_live',
        'feed_url': 'https://www.boomlive.in/feed',
        'feed_title': 'BOOM Live',
        'category': 'fact_check',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'factly': {
        'source_id': 'factly',
        'feed_url': 'https://factly.in/feed/',
        'feed_title': 'Factly',
        'category': 'fact_check',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 600,
        'enabled': True
    },
    
    'webqoof_quint': {
        'source_id': 'webqoof_quint',
        'feed_url': 'https://www.thequint.com/rss/webqoof',
        'feed_title': 'WebQoof - The Quint',
        'category': 'fact_check',
        'language': 'en',
        'reliability_score': 0.85,
        'fetch_interval': 600,
        'enabled': True
    },
    
    # Technology and Digital News
    'medianama': {
        'source_id': 'medianama',
        'feed_url': 'https://www.medianama.com/feed/',
        'feed_title': 'MediaNama',
        'category': 'technology',
        'language': 'en',
        'reliability_score': 0.8,
        'fetch_interval': 900,
        'enabled': True
    },
    
    'inc42': {
        'source_id': 'inc42',
        'feed_url': 'https://inc42.com/feed/',
        'feed_title': 'Inc42',
        'category': 'technology',
        'language': 'en',
        'reliability_score': 0.75,
        'fetch_interval': 900,
        'enabled': True
    }
}


# Categorized lists for easy access
def get_sources_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """Get news sources filtered by category."""
    return {
        source_id: config 
        for source_id, config in INDIAN_NEWS_OUTLETS.items() 
        if config.get('category') == category
    }


def get_sources_by_language(language: str) -> Dict[str, Dict[str, Any]]:
    """Get news sources filtered by language."""
    return {
        source_id: config 
        for source_id, config in INDIAN_NEWS_OUTLETS.items() 
        if config.get('language') == language
    }


def get_high_reliability_sources(min_score: float = 0.8) -> Dict[str, Dict[str, Any]]:
    """Get news sources with high reliability scores."""
    return {
        source_id: config 
        for source_id, config in INDIAN_NEWS_OUTLETS.items() 
        if config.get('reliability_score', 0) >= min_score
    }


def get_enabled_sources() -> Dict[str, Dict[str, Any]]:
    """Get only enabled news sources."""
    return {
        source_id: config 
        for source_id, config in INDIAN_NEWS_OUTLETS.items() 
        if config.get('enabled', False)
    }


# Quick access lists
NATIONAL_NEWS_SOURCES = get_sources_by_category('news')
FACT_CHECK_SOURCES = get_sources_by_category('fact_check')
REGIONAL_NEWS_SOURCES = get_sources_by_category('regional')
BUSINESS_NEWS_SOURCES = get_sources_by_category('business')

ENGLISH_SOURCES = get_sources_by_language('en')
HINDI_SOURCES = get_sources_by_language('hi')

HIGH_RELIABILITY_SOURCES = get_high_reliability_sources(0.85)


# Source validation
def validate_source_config(config: Dict[str, Any]) -> List[str]:
    """Validate a news source configuration."""
    errors = []
    
    required_fields = ['source_id', 'feed_url', 'category', 'language', 'reliability_score']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    if 'reliability_score' in config:
        score = config['reliability_score']
        if not isinstance(score, (int, float)) or not (0 <= score <= 1):
            errors.append("reliability_score must be a number between 0 and 1")
    
    if 'fetch_interval' in config:
        interval = config['fetch_interval']
        if not isinstance(interval, int) or interval < 60:
            errors.append("fetch_interval must be an integer >= 60 seconds")
    
    return errors


def get_source_statistics() -> Dict[str, Any]:
    """Get statistics about configured news sources."""
    total_sources = len(INDIAN_NEWS_OUTLETS)
    enabled_sources = len(get_enabled_sources())
    
    categories = {}
    languages = {}
    reliability_distribution = {'high': 0, 'medium': 0, 'low': 0}
    
    for config in INDIAN_NEWS_OUTLETS.values():
        # Count by category
        category = config.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1
        
        # Count by language
        language = config.get('language', 'unknown')
        languages[language] = languages.get(language, 0) + 1
        
        # Count by reliability
        reliability = config.get('reliability_score', 0)
        if reliability >= 0.8:
            reliability_distribution['high'] += 1
        elif reliability >= 0.6:
            reliability_distribution['medium'] += 1
        else:
            reliability_distribution['low'] += 1
    
    return {
        'total_sources': total_sources,
        'enabled_sources': enabled_sources,
        'categories': categories,
        'languages': languages,
        'reliability_distribution': reliability_distribution,
        'avg_reliability_score': sum(
            config.get('reliability_score', 0) 
            for config in INDIAN_NEWS_OUTLETS.values()
        ) / total_sources if total_sources > 0 else 0
    }