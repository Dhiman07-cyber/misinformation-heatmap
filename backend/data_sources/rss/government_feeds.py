#!/usr/bin/env python3
"""
Configuration for Indian government RSS feeds and official sources.
Includes central government, state governments, and official agencies.
"""

from typing import Dict, List, Any

# Indian government and official RSS feeds
GOVERNMENT_FEEDS: Dict[str, Dict[str, Any]] = {
    
    # Central Government
    'pib_national': {
        'source_id': 'pib_national',
        'feed_url': 'https://pib.gov.in/rss/leng.aspx',
        'feed_title': 'Press Information Bureau - National',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 600,  # 10 minutes
        'enabled': True,
        'authority': 'central_government'
    },
    
    'pib_hindi': {
        'source_id': 'pib_hindi',
        'feed_url': 'https://pib.gov.in/rss/lhindi.aspx',
        'feed_title': 'Press Information Bureau - Hindi',
        'category': 'government',
        'language': 'hi',
        'reliability_score': 0.95,
        'fetch_interval': 600,
        'enabled': True,
        'authority': 'central_government'
    },
    
    'mygov_india': {
        'source_id': 'mygov_india',
        'feed_url': 'https://www.mygov.in/rss.xml',
        'feed_title': 'MyGov India',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 900,  # 15 minutes
        'enabled': True,
        'authority': 'central_government'
    },
    
    # Ministry-specific feeds
    'mha_india': {
        'source_id': 'mha_india',
        'feed_url': 'https://www.mha.gov.in/rss.xml',
        'feed_title': 'Ministry of Home Affairs',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 900,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'home_affairs'
    },
    
    'mea_india': {
        'source_id': 'mea_india',
        'feed_url': 'https://www.mea.gov.in/rss.xml',
        'feed_title': 'Ministry of External Affairs',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 900,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'external_affairs'
    },
    
    'mohfw_india': {
        'source_id': 'mohfw_india',
        'feed_url': 'https://www.mohfw.gov.in/rss.xml',
        'feed_title': 'Ministry of Health and Family Welfare',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 600,  # Health info is critical
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'health'
    },
    
    'finmin_india': {
        'source_id': 'finmin_india',
        'feed_url': 'https://www.finmin.nic.in/rss.xml',
        'feed_title': 'Ministry of Finance',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 900,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'finance'
    },
    
    # Election Commission
    'eci_india': {
        'source_id': 'eci_india',
        'feed_url': 'https://eci.gov.in/rss.xml',
        'feed_title': 'Election Commission of India',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 1800,  # 30 minutes
        'enabled': True,
        'authority': 'constitutional_body'
    },
    
    # Supreme Court
    'sci_india': {
        'source_id': 'sci_india',
        'feed_url': 'https://main.sci.gov.in/rss.xml',
        'feed_title': 'Supreme Court of India',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.98,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'judiciary'
    },
    
    # Reserve Bank of India
    'rbi_india': {
        'source_id': 'rbi_india',
        'feed_url': 'https://www.rbi.org.in/rss.xml',
        'feed_title': 'Reserve Bank of India',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'central_bank'
    },
    
    # State Government Feeds
    'maharashtra_gov': {
        'source_id': 'maharashtra_gov',
        'feed_url': 'https://www.maharashtra.gov.in/rss.xml',
        'feed_title': 'Government of Maharashtra',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Maharashtra'
    },
    
    'karnataka_gov': {
        'source_id': 'karnataka_gov',
        'feed_url': 'https://www.karnataka.gov.in/rss.xml',
        'feed_title': 'Government of Karnataka',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Karnataka'
    },
    
    'tamil_nadu_gov': {
        'source_id': 'tamil_nadu_gov',
        'feed_url': 'https://www.tn.gov.in/rss.xml',
        'feed_title': 'Government of Tamil Nadu',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Tamil Nadu'
    },
    
    'west_bengal_gov': {
        'source_id': 'west_bengal_gov',
        'feed_url': 'https://wb.gov.in/rss.xml',
        'feed_title': 'Government of West Bengal',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'West Bengal'
    },
    
    'gujarat_gov': {
        'source_id': 'gujarat_gov',
        'feed_url': 'https://gujaratindia.gov.in/rss.xml',
        'feed_title': 'Government of Gujarat',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Gujarat'
    },
    
    'rajasthan_gov': {
        'source_id': 'rajasthan_gov',
        'feed_url': 'https://rajasthan.gov.in/rss.xml',
        'feed_title': 'Government of Rajasthan',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Rajasthan'
    },
    
    'uttar_pradesh_gov': {
        'source_id': 'uttar_pradesh_gov',
        'feed_url': 'https://up.gov.in/rss.xml',
        'feed_title': 'Government of Uttar Pradesh',
        'category': 'government',
        'language': 'hi',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Uttar Pradesh'
    },
    
    'delhi_gov': {
        'source_id': 'delhi_gov',
        'feed_url': 'https://delhi.gov.in/rss.xml',
        'feed_title': 'Government of Delhi',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'state_government',
        'state': 'Delhi'
    },
    
    # Disaster Management
    'ndma_india': {
        'source_id': 'ndma_india',
        'feed_url': 'https://ndma.gov.in/rss.xml',
        'feed_title': 'National Disaster Management Authority',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 600,  # Disaster info is time-critical
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'disaster_management'
    },
    
    # Weather and Climate
    'imd_india': {
        'source_id': 'imd_india',
        'feed_url': 'https://mausam.imd.gov.in/rss.xml',
        'feed_title': 'India Meteorological Department',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 600,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'earth_sciences'
    },
    
    # Agriculture
    'agriculture_gov': {
        'source_id': 'agriculture_gov',
        'feed_url': 'https://agricoop.nic.in/rss.xml',
        'feed_title': 'Ministry of Agriculture',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'agriculture'
    },
    
    # Railways
    'railway_india': {
        'source_id': 'railway_india',
        'feed_url': 'https://indianrailways.gov.in/rss.xml',
        'feed_title': 'Indian Railways',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'railways'
    },
    
    # Education
    'education_gov': {
        'source_id': 'education_gov',
        'feed_url': 'https://www.education.gov.in/rss.xml',
        'feed_title': 'Ministry of Education',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.9,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'education'
    },
    
    # ISRO
    'isro_india': {
        'source_id': 'isro_india',
        'feed_url': 'https://www.isro.gov.in/rss.xml',
        'feed_title': 'Indian Space Research Organisation',
        'category': 'government',
        'language': 'en',
        'reliability_score': 0.95,
        'fetch_interval': 1800,
        'enabled': True,
        'authority': 'central_government',
        'ministry': 'space'
    }
}


# Helper functions for government feeds
def get_central_government_feeds() -> Dict[str, Dict[str, Any]]:
    """Get central government RSS feeds."""
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if config.get('authority') == 'central_government'
    }


def get_state_government_feeds() -> Dict[str, Dict[str, Any]]:
    """Get state government RSS feeds."""
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if config.get('authority') == 'state_government'
    }


def get_feeds_by_state(state: str) -> Dict[str, Dict[str, Any]]:
    """Get government feeds for a specific state."""
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if config.get('state') == state
    }


def get_feeds_by_ministry(ministry: str) -> Dict[str, Dict[str, Any]]:
    """Get feeds from a specific ministry."""
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if config.get('ministry') == ministry
    }


def get_critical_feeds() -> Dict[str, Dict[str, Any]]:
    """Get feeds for critical/emergency information."""
    critical_ministries = ['health', 'disaster_management', 'home_affairs']
    critical_authorities = ['constitutional_body', 'judiciary']
    
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if (config.get('ministry') in critical_ministries or 
            config.get('authority') in critical_authorities or
            config.get('fetch_interval', 1800) <= 600)  # Frequent updates
    }


def get_high_authority_feeds() -> Dict[str, Dict[str, Any]]:
    """Get feeds from highest authority sources."""
    return {
        source_id: config 
        for source_id, config in GOVERNMENT_FEEDS.items() 
        if config.get('reliability_score', 0) >= 0.95
    }


# Government source categories
CENTRAL_GOVT_FEEDS = get_central_government_feeds()
STATE_GOVT_FEEDS = get_state_government_feeds()
CRITICAL_GOVT_FEEDS = get_critical_feeds()
HIGH_AUTHORITY_FEEDS = get_high_authority_feeds()


# Validation and statistics
def validate_government_feed_config(config: Dict[str, Any]) -> List[str]:
    """Validate a government feed configuration."""
    errors = []
    
    required_fields = ['source_id', 'feed_url', 'category', 'language', 'reliability_score', 'authority']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    valid_authorities = [
        'central_government', 'state_government', 'constitutional_body', 
        'judiciary', 'central_bank'
    ]
    if 'authority' in config and config['authority'] not in valid_authorities:
        errors.append(f"Invalid authority: {config['authority']}")
    
    if 'reliability_score' in config:
        score = config['reliability_score']
        if not isinstance(score, (int, float)) or not (0 <= score <= 1):
            errors.append("reliability_score must be a number between 0 and 1")
        elif score < 0.8:  # Government sources should be highly reliable
            errors.append("Government sources should have reliability_score >= 0.8")
    
    return errors


def get_government_feed_statistics() -> Dict[str, Any]:
    """Get statistics about government RSS feeds."""
    total_feeds = len(GOVERNMENT_FEEDS)
    enabled_feeds = len([f for f in GOVERNMENT_FEEDS.values() if f.get('enabled', False)])
    
    authorities = {}
    ministries = {}
    states = {}
    languages = {}
    
    for config in GOVERNMENT_FEEDS.values():
        # Count by authority
        authority = config.get('authority', 'unknown')
        authorities[authority] = authorities.get(authority, 0) + 1
        
        # Count by ministry
        ministry = config.get('ministry')
        if ministry:
            ministries[ministry] = ministries.get(ministry, 0) + 1
        
        # Count by state
        state = config.get('state')
        if state:
            states[state] = states.get(state, 0) + 1
        
        # Count by language
        language = config.get('language', 'unknown')
        languages[language] = languages.get(language, 0) + 1
    
    return {
        'total_feeds': total_feeds,
        'enabled_feeds': enabled_feeds,
        'authorities': authorities,
        'ministries': ministries,
        'states': states,
        'languages': languages,
        'avg_reliability_score': sum(
            config.get('reliability_score', 0) 
            for config in GOVERNMENT_FEEDS.values()
        ) / total_feeds if total_feeds > 0 else 0,
        'critical_feeds': len(CRITICAL_GOVT_FEEDS),
        'high_authority_feeds': len(HIGH_AUTHORITY_FEEDS)
    }


# Priority levels for government feeds
PRIORITY_LEVELS = {
    'critical': {
        'sources': ['pib_national', 'pib_hindi', 'mha_india', 'mohfw_india', 'ndma_india', 'imd_india'],
        'fetch_interval': 300,  # 5 minutes
        'description': 'Critical government communications'
    },
    'high': {
        'sources': ['sci_india', 'eci_india', 'rbi_india', 'mea_india'],
        'fetch_interval': 600,  # 10 minutes
        'description': 'High-authority constitutional bodies'
    },
    'medium': {
        'sources': ['mygov_india', 'finmin_india', 'education_gov', 'agriculture_gov'],
        'fetch_interval': 900,  # 15 minutes
        'description': 'Regular government ministries'
    },
    'low': {
        'sources': ['railway_india', 'isro_india'],
        'fetch_interval': 1800,  # 30 minutes
        'description': 'Specialized government agencies'
    }
}


def get_feeds_by_priority(priority: str) -> Dict[str, Dict[str, Any]]:
    """Get government feeds by priority level."""
    if priority not in PRIORITY_LEVELS:
        return {}
    
    priority_sources = PRIORITY_LEVELS[priority]['sources']
    return {
        source_id: GOVERNMENT_FEEDS[source_id] 
        for source_id in priority_sources 
        if source_id in GOVERNMENT_FEEDS
    }