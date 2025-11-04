#!/usr/bin/env python3
"""
Base connector class for all data source implementations.
Provides common interface and functionality for data ingestion plugins.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class RawEvent:
    """Standardized raw event format from any data source."""
    
    # Core fields
    source_id: str                    # Unique source identifier (e.g., "times_of_india")
    source_type: str                  # Type: 'rss', 'crawler', 'api', 'manual'
    content: str                      # Main text content
    timestamp: datetime               # When content was published
    
    # Optional fields
    url: Optional[str] = None         # Source URL if available
    title: Optional[str] = None       # Article/post title
    author: Optional[str] = None      # Author/publisher name
    language: Optional[str] = None    # Detected/specified language
    location_hint: Optional[str] = None  # Geographic hint if available
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)  # Source-specific metadata
    raw_data: Dict[str, Any] = field(default_factory=dict)  # Original raw data
    
    # Processing fields (set during ingestion)
    ingestion_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: Optional[str] = None    # Unique event ID (generated)
    
    def __post_init__(self):
        """Generate unique event ID after initialization."""
        if not self.event_id:
            self.event_id = self._generate_event_id()
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID based on content and source."""
        content_hash = hashlib.md5(
            f"{self.source_id}:{self.content}:{self.timestamp}".encode()
        ).hexdigest()
        return f"{self.source_type}_{self.source_id}_{content_hash[:12]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'event_id': self.event_id,
            'source_id': self.source_id,
            'source_type': self.source_type,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'title': self.title,
            'author': self.author,
            'language': self.language,
            'location_hint': self.location_hint,
            'metadata': self.metadata,
            'raw_data': self.raw_data,
            'ingestion_timestamp': self.ingestion_timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RawEvent':
        """Create RawEvent from dictionary."""
        # Parse datetime fields
        timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        ingestion_timestamp = datetime.fromisoformat(
            data.get('ingestion_timestamp', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')
        )
        
        return cls(
            event_id=data.get('event_id'),
            source_id=data['source_id'],
            source_type=data['source_type'],
            content=data['content'],
            timestamp=timestamp,
            url=data.get('url'),
            title=data.get('title'),
            author=data.get('author'),
            language=data.get('language'),
            location_hint=data.get('location_hint'),
            metadata=data.get('metadata', {}),
            raw_data=data.get('raw_data', {}),
            ingestion_timestamp=ingestion_timestamp
        )


class BaseDataConnector(ABC):
    """Abstract base class for all data source connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize connector with configuration.
        
        Args:
            config: Connector configuration dictionary
        """
        self.config = config
        self.source_id = config.get('source_id', 'unknown')
        self.source_type = config.get('source_type', 'unknown')
        self.enabled = config.get('enabled', True)
        self.fetch_interval = config.get('fetch_interval', 300)  # 5 minutes default
        self.rate_limit = config.get('rate_limit', 60)  # requests per minute
        self.max_events_per_fetch = config.get('max_events_per_fetch', 100)
        
        # Statistics
        self.stats = {
            'total_fetches': 0,
            'total_events': 0,
            'last_fetch_time': None,
            'last_fetch_count': 0,
            'errors': 0,
            'last_error': None
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def fetch_events(self, since: Optional[datetime] = None) -> List[RawEvent]:
        """Fetch new events from the data source.
        
        Args:
            since: Only fetch events newer than this timestamp
            
        Returns:
            List of RawEvent objects
            
        Raises:
            Exception: If fetching fails
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate connector configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the connector.
        
        Returns:
            Dictionary with health information
        """
        pass
    
    def preprocess_content(self, content: str) -> str:
        """Preprocess content before creating RawEvent.
        
        Args:
            content: Raw content string
            
        Returns:
            Preprocessed content
        """
        if not content:
            return ""
        
        # Basic preprocessing
        content = content.strip()
        
        # Remove excessive whitespace
        import re
        content = re.sub(r'\s+', ' ', content)
        
        # Remove control characters
        content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\t')
        
        return content
    
    def extract_location_hint(self, content: str, metadata: Dict = None) -> Optional[str]:
        """Extract location hint from content or metadata.
        
        Args:
            content: Text content to analyze
            metadata: Additional metadata that might contain location info
            
        Returns:
            Location hint string or None
        """
        # Indian states for location detection
        indian_states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
            'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
            'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
        ]
        
        # Major cities
        major_cities = [
            'Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata',
            'Pune', 'Ahmedabad', 'Surat', 'Jaipur', 'Lucknow', 'Kanpur',
            'Nagpur', 'Indore', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara'
        ]
        
        content_lower = content.lower()
        
        # Check for states
        for state in indian_states:
            if state.lower() in content_lower:
                return state
        
        # Check for cities
        for city in major_cities:
            if city.lower() in content_lower:
                return city
        
        # Check metadata for location info
        if metadata:
            location_fields = ['location', 'place', 'city', 'state', 'region']
            for field in location_fields:
                if field in metadata and metadata[field]:
                    return str(metadata[field])
        
        return None
    
    def detect_language(self, content: str) -> Optional[str]:
        """Detect language of the content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Language code (e.g., 'en', 'hi') or None
        """
        try:
            # Simple heuristic-based detection for common Indian languages
            
            # Check for English (Latin script)
            if all(ord(char) < 256 for char in content if char.isalpha()):
                return 'en'
            
            # Check for Hindi (Devanagari script)
            if any(0x0900 <= ord(char) <= 0x097F for char in content):
                return 'hi'
            
            # Check for Bengali (Bengali script)
            if any(0x0980 <= ord(char) <= 0x09FF for char in content):
                return 'bn'
            
            # Check for Tamil (Tamil script)
            if any(0x0B80 <= ord(char) <= 0x0BFF for char in content):
                return 'ta'
            
            # Check for Telugu (Telugu script)
            if any(0x0C00 <= ord(char) <= 0x0C7F for char in content):
                return 'te'
            
            # Check for Gujarati (Gujarati script)
            if any(0x0A80 <= ord(char) <= 0x0AFF for char in content):
                return 'gu'
            
            # Check for Marathi (Devanagari script, same as Hindi)
            # Would need more sophisticated detection
            
            # Default to English if uncertain
            return 'en'
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}")
            return 'en'  # Default to English
    
    async def fetch_with_retry(self, max_retries: int = 3, delay: float = 1.0) -> List[RawEvent]:
        """Fetch events with retry logic.
        
        Args:
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            List of RawEvent objects
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"Fetch attempt {attempt + 1}/{max_retries + 1}")
                events = await self.fetch_events()
                
                # Update statistics
                self.stats['total_fetches'] += 1
                self.stats['total_events'] += len(events)
                self.stats['last_fetch_time'] = datetime.now(timezone.utc)
                self.stats['last_fetch_count'] = len(events)
                
                self.logger.info(f"Successfully fetched {len(events)} events from {self.source_id}")
                return events
                
            except Exception as e:
                last_exception = e
                self.stats['errors'] += 1
                self.stats['last_error'] = str(e)
                
                if attempt < max_retries:
                    self.logger.warning(f"Fetch attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.logger.error(f"All fetch attempts failed for {self.source_id}: {e}")
        
        raise last_exception
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connector statistics.
        
        Returns:
            Dictionary with connector statistics
        """
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'enabled': self.enabled,
            'stats': self.stats.copy(),
            'config': {
                'fetch_interval': self.fetch_interval,
                'rate_limit': self.rate_limit,
                'max_events_per_fetch': self.max_events_per_fetch
            }
        }
    
    def __str__(self) -> str:
        """String representation of the connector."""
        return f"{self.__class__.__name__}(source_id='{self.source_id}', enabled={self.enabled})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the connector."""
        return (f"{self.__class__.__name__}("
                f"source_id='{self.source_id}', "
                f"source_type='{self.source_type}', "
                f"enabled={self.enabled}, "
                f"fetch_interval={self.fetch_interval})")


class ConnectorError(Exception):
    """Base exception for connector-related errors."""
    pass


class ConfigurationError(ConnectorError):
    """Exception raised for configuration-related errors."""
    pass


class FetchError(ConnectorError):
    """Exception raised for data fetching errors."""
    pass


class ValidationError(ConnectorError):
    """Exception raised for data validation errors."""
    pass