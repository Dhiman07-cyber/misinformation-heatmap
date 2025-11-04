# Data Ingestion Architecture - Extensible Design

## 🏗️ **Modular Data Ingestion Framework**

### **Core Philosophy: Plugin-Based Architecture**
Instead of hardcoding specific data sources, we'll build a **plugin system** where each data source is a separate module that implements a common interface. This allows easy addition of new sources without touching core code.

```
backend/data_sources/
├── base/
│   ├── __init__.py
│   ├── base_connector.py      # Abstract base class
│   ├── data_validator.py      # Common validation logic
│   └── rate_limiter.py        # Rate limiting utilities
├── rss/
│   ├── __init__.py
│   ├── rss_connector.py       # RSS feed implementation
│   ├── news_outlets.py        # Indian news outlet configs
│   └── government_feeds.py    # PIB and govt feeds
├── crawlers/
│   ├── __init__.py
│   ├── web_crawler.py         # General web scraping
│   ├── news_crawler.py        # News-specific crawler
│   └── social_crawler.py      # Social media crawler
├── apis/
│   ├── __init__.py
│   ├── twitter_api.py         # Twitter/X API (when available)
│   ├── reddit_api.py          # Reddit API
│   └── telegram_api.py        # Telegram channels
├── manual/
│   ├── __init__.py
│   ├── user_reports.py        # User-submitted reports
│   └── admin_input.py         # Manual admin input
└── registry.py                # Data source registry
```

## 🔌 **Plugin Interface Design**

### **Base Connector Class**
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RawEvent:
    """Standardized raw event format from any source"""
    source_id: str          # Unique source identifier
    source_type: str        # 'rss', 'crawler', 'api', 'manual'
    content: str            # Main text content
    url: Optional[str]      # Source URL if available
    timestamp: datetime     # When content was published
    metadata: Dict          # Source-specific metadata
    language: Optional[str] # Detected/specified language
    location_hint: Optional[str]  # Geographic hint if available

class BaseDataConnector(ABC):
    """Abstract base class for all data connectors"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.source_id = config.get('source_id')
        self.enabled = config.get('enabled', True)
        self.rate_limit = config.get('rate_limit', 60)  # requests per minute
    
    @abstractmethod
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        """Fetch new events since the given timestamp"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate connector configuration"""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict:
        """Return health status of the connector"""
        pass
    
    def preprocess_content(self, content: str) -> str:
        """Common preprocessing (can be overridden)"""
        # Remove excessive whitespace, normalize encoding, etc.
        return content.strip()
```

## 📊 **Data Source Types & Use Cases**

### **1. RSS Feeds** (Immediate - Day 1-2)
**Best for**: News outlets, government feeds, blogs
**Pros**: Reliable, structured, no rate limits, easy to implement
**Cons**: Limited to sources that provide RSS

```python
# Example RSS sources
RSS_SOURCES = {
    'times_of_india': {
        'url': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
        'category': 'news',
        'reliability_score': 0.8
    },
    'pib_releases': {
        'url': 'https://pib.gov.in/rss/leng.aspx',
        'category': 'government',
        'reliability_score': 0.9
    }
}
```

### **2. Web Crawlers** (Day 2-3)
**Best for**: News sites without RSS, social media posts, forums
**Pros**: Can access any public content, very flexible
**Cons**: More complex, rate limiting needed, legal considerations

```python
# Example crawler targets
CRAWLER_TARGETS = {
    'news_websites': [
        'https://www.thehindu.com/news/',
        'https://indianexpress.com/section/india/',
        'https://www.ndtv.com/india-news'
    ],
    'fact_check_sites': [
        'https://www.altnews.in/',
        'https://www.boomlive.in/',
        'https://factly.in/'
    ]
}
```

### **3. API Integrations** (Future expansion)
**Best for**: Social media platforms, news aggregators
**Pros**: Real-time, structured data, official access
**Cons**: Cost, rate limits, API changes

```python
# Future API integrations
API_SOURCES = {
    'twitter_api': {
        'endpoint': 'https://api.twitter.com/2/tweets/search/recent',
        'cost_per_request': 0.01,  # Track costs
        'rate_limit': 300  # requests per 15 min
    },
    'reddit_api': {
        'endpoint': 'https://www.reddit.com/r/india/new.json',
        'cost_per_request': 0.0,  # Free tier
        'rate_limit': 60  # requests per minute
    }
}
```

### **4. User Reports** (Future feature)
**Best for**: Citizen journalism, direct reports
**Pros**: Ground truth, local insights, community engagement
**Cons**: Quality control needed, potential spam

## 🚀 **Implementation Strategy**

### **Phase 1: RSS Foundation** (Days 1-2)
```python
# backend/data_sources/rss/rss_connector.py
class RSSConnector(BaseDataConnector):
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        # Fetch RSS feed
        # Parse XML
        # Convert to RawEvent format
        # Filter by timestamp if 'since' provided
        pass
```

### **Phase 2: Smart Crawlers** (Days 2-3)
```python
# backend/data_sources/crawlers/news_crawler.py
class NewsCrawler(BaseDataConnector):
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        # Crawl target websites
        # Extract article content using newspaper3k or similar
        # Respect robots.txt and rate limits
        # Return structured events
        pass
```

### **Phase 3: API Integrations** (Future)
```python
# backend/data_sources/apis/twitter_api.py
class TwitterAPIConnector(BaseDataConnector):
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        # Use Twitter API v2
        # Search for India-related content
        # Handle rate limits and pagination
        # Return tweets as events
        pass
```

## 🔧 **Configuration Management**

### **Dynamic Source Configuration**
```yaml
# config/data_sources.yaml
data_sources:
  rss_feeds:
    enabled: true
    sources:
      - source_id: "times_of_india"
        url: "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
        fetch_interval: 300  # 5 minutes
        enabled: true
      - source_id: "pib_releases"
        url: "https://pib.gov.in/rss/leng.aspx"
        fetch_interval: 600  # 10 minutes
        enabled: true
  
  crawlers:
    enabled: true
    sources:
      - source_id: "hindu_news"
        base_url: "https://www.thehindu.com"
        selectors:
          title: "h1.title"
          content: "div.article-content"
        fetch_interval: 900  # 15 minutes
        enabled: true
  
  apis:
    enabled: false  # Enable when ready
    sources:
      - source_id: "twitter_india"
        api_key: "${TWITTER_API_KEY}"
        search_terms: ["India", "भारत", "misinformation"]
        fetch_interval: 180  # 3 minutes
        enabled: false
```

## 📈 **Scalability & Future Expansion**

### **Easy Addition of New Sources**
1. **Create new connector class** inheriting from `BaseDataConnector`
2. **Add configuration** to `data_sources.yaml`
3. **Register in source registry** - automatic discovery
4. **No core code changes needed**

### **Example: Adding WhatsApp Groups** (Future)
```python
# backend/data_sources/messaging/whatsapp_connector.py
class WhatsAppConnector(BaseDataConnector):
    """Monitor WhatsApp groups for misinformation (with proper permissions)"""
    
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        # Use WhatsApp Business API or web scraping
        # Extract messages from monitored groups
        # Return as standardized events
        pass
```

### **Example: Adding Telegram Channels**
```python
# backend/data_sources/messaging/telegram_connector.py
class TelegramConnector(BaseDataConnector):
    """Monitor public Telegram channels"""
    
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        # Use Telegram Bot API
        # Monitor public channels and groups
        # Extract messages and media
        pass
```

## 🛡️ **Quality Control & Filtering**

### **Multi-Layer Filtering**
```python
# backend/data_sources/base/data_validator.py
class DataValidator:
    def validate_event(self, event: RawEvent) -> bool:
        """Multi-layer validation"""
        
        # 1. Basic validation
        if not event.content or len(event.content) < 10:
            return False
        
        # 2. Language filtering (Indian languages + English)
        if not self.is_relevant_language(event.content):
            return False
        
        # 3. Geographic relevance (India-related content)
        if not self.is_india_relevant(event.content):
            return False
        
        # 4. Content quality (not spam/ads)
        if not self.is_quality_content(event.content):
            return False
        
        return True
```

## 🔄 **Data Flow Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   Ingestion      │    │   Processing    │
│                 │    │   Coordinator    │    │   Pipeline      │
│ • RSS Feeds     │───▶│                  │───▶│                 │
│ • Web Crawlers  │    │ • Rate Limiting  │    │ • NLP Analysis  │
│ • APIs          │    │ • Deduplication  │    │ • Satellite Val │
│ • User Reports  │    │ • Validation     │    │ • Risk Scoring  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Pub/Sub Queue  │
                       │                  │
                       │ • Event Routing  │
                       │ • Load Balancing │
                       │ • Error Handling │
                       └──────────────────┘
```

## 🎯 **Recommendation: Start with Hybrid Approach**

For the **2-week production timeline**, I recommend:

### **Week 1: RSS + Basic Crawlers**
- **RSS feeds** for reliable, structured data (60% of sources)
- **Simple crawlers** for major news sites without RSS (30% of sources)
- **Manual input API** for testing and emergency use (10% of sources)

### **Future Expansion Path**
- **Month 2**: Add social media APIs (Twitter, Reddit)
- **Month 3**: Add messaging platforms (Telegram, WhatsApp groups)
- **Month 4**: Add user reporting system
- **Month 6**: Add AI-powered content discovery

## 🚀 **Ready to Implement?**

Should I start building this **modular data ingestion framework**? I'll begin with:

1. **Base connector architecture** - Plugin system foundation
2. **RSS connector implementation** - Immediate data source
3. **Configuration management** - Easy source addition
4. **Data validation pipeline** - Quality control

This approach gives you **immediate production capability** while ensuring **infinite extensibility** for future data sources!