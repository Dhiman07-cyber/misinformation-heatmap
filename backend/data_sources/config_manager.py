#!/usr/bin/env python3
"""
Configuration manager for data sources.
Handles loading, validation, and management of data source configurations.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import yaml
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DataSourceConfig:
    """Data source configuration structure."""
    source_id: str
    source_type: str
    enabled: bool = True
    fetch_interval: int = 300
    priority: str = "medium"
    reliability_score: float = 0.7
    category: str = "news"
    language: str = "en"
    
    # Type-specific configurations
    feed_url: Optional[str] = None  # For RSS
    base_url: Optional[str] = None  # For crawlers
    api_endpoint: Optional[str] = None  # For APIs
    
    # Additional metadata
    feed_title: Optional[str] = None
    authority: Optional[str] = None
    ministry: Optional[str] = None
    state: Optional[str] = None
    
    # Performance settings
    rate_limit: int = 60
    timeout: int = 30
    max_entries: int = 100
    
    # Custom configuration
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        config = {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'enabled': self.enabled,
            'fetch_interval': self.fetch_interval,
            'priority': self.priority,
            'reliability_score': self.reliability_score,
            'category': self.category,
            'language': self.language,
            'rate_limit': self.rate_limit,
            'timeout': self.timeout,
            'max_entries': self.max_entries
        }
        
        # Add optional fields if present
        optional_fields = [
            'feed_url', 'base_url', 'api_endpoint', 'feed_title',
            'authority', 'ministry', 'state'
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                config[field] = value
        
        # Add custom configuration
        config.update(self.custom_config)
        
        return config


class ConfigManager:
    """Manages data source configurations."""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file or directory
        """
        self.config_path = Path(config_path) if config_path else Path("config/data_sources.yaml")
        self.config_data: Dict[str, Any] = {}
        self.source_configs: Dict[str, DataSourceConfig] = {}
        
        # Load configuration if file exists
        if self.config_path.exists():
            self.load_config()
    
    def load_config(self, config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Optional path to configuration file
            
        Returns:
            Loaded configuration dictionary
        """
        if config_path:
            self.config_path = Path(config_path)
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                    self.config_data = yaml.safe_load(f)
                elif self.config_path.suffix.lower() == '.json':
                    self.config_data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")
            
            # Parse source configurations
            self._parse_source_configs()
            
            logger.info(f"Loaded configuration from {self.config_path}")
            logger.info(f"Found {len(self.source_configs)} data source configurations")
            
            return self.config_data
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_path}: {e}")
            raise
    
    def _parse_source_configs(self):
        """Parse source configurations from loaded config data."""
        self.source_configs.clear()
        
        # Parse RSS feeds
        rss_feeds = self.config_data.get('rss_feeds', {})
        if rss_feeds.get('enabled', True):
            self._parse_rss_configs(rss_feeds)
        
        # Parse government feeds
        gov_feeds = self.config_data.get('government_feeds', {})
        if gov_feeds.get('enabled', True):
            self._parse_government_configs(gov_feeds)
        
        # Parse web crawlers
        crawlers = self.config_data.get('web_crawlers', {})
        if crawlers.get('enabled', False):
            self._parse_crawler_configs(crawlers)
        
        # Parse API sources
        api_sources = self.config_data.get('api_sources', {})
        if api_sources.get('enabled', False):
            self._parse_api_configs(api_sources)
    
    def _parse_rss_configs(self, rss_config: Dict[str, Any]):
        """Parse RSS feed configurations."""
        categories = ['national_english', 'regional_english', 'hindi_news', 'fact_checking']
        
        for category in categories:
            if category in rss_config:
                for source_id, config in rss_config[category].items():
                    self._create_source_config(source_id, config, 'rss')
    
    def _parse_government_configs(self, gov_config: Dict[str, Any]):
        """Parse government feed configurations."""
        categories = ['central_government', 'state_governments']
        
        for category in categories:
            if category in gov_config:
                for source_id, config in gov_config[category].items():
                    self._create_source_config(source_id, config, 'rss')
    
    def _parse_crawler_configs(self, crawler_config: Dict[str, Any]):
        """Parse web crawler configurations."""
        categories = ['news_sites']
        
        for category in categories:
            if category in crawler_config:
                for source_id, config in crawler_config[category].items():
                    self._create_source_config(source_id, config, 'crawler')
    
    def _parse_api_configs(self, api_config: Dict[str, Any]):
        """Parse API source configurations."""
        categories = ['social_media']
        
        for category in categories:
            if category in api_config:
                for source_id, config in api_config[category].items():
                    self._create_source_config(source_id, config, 'api')
    
    def _create_source_config(self, source_id: str, config: Dict[str, Any], default_type: str):
        """Create DataSourceConfig from dictionary."""
        try:
            # Extract known fields
            source_config = DataSourceConfig(
                source_id=source_id,
                source_type=config.get('source_type', default_type),
                enabled=config.get('enabled', True),
                fetch_interval=config.get('fetch_interval', 300),
                priority=config.get('priority', 'medium'),
                reliability_score=config.get('reliability_score', 0.7),
                category=config.get('category', 'news'),
                language=config.get('language', 'en'),
                feed_url=config.get('feed_url'),
                base_url=config.get('base_url'),
                api_endpoint=config.get('api_endpoint'),
                feed_title=config.get('feed_title'),
                authority=config.get('authority'),
                ministry=config.get('ministry'),
                state=config.get('state'),
                rate_limit=config.get('rate_limit', 60),
                timeout=config.get('timeout', 30),
                max_entries=config.get('max_entries', 100)
            )
            
            # Store any additional configuration
            known_fields = {
                'source_type', 'enabled', 'fetch_interval', 'priority', 'reliability_score',
                'category', 'language', 'feed_url', 'base_url', 'api_endpoint', 'feed_title',
                'authority', 'ministry', 'state', 'rate_limit', 'timeout', 'max_entries'
            }
            
            custom_config = {k: v for k, v in config.items() if k not in known_fields}
            source_config.custom_config = custom_config
            
            self.source_configs[source_id] = source_config
            
        except Exception as e:
            logger.error(f"Failed to parse config for source {source_id}: {e}")
    
    def get_source_config(self, source_id: str) -> Optional[DataSourceConfig]:
        """Get configuration for a specific source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            DataSourceConfig or None if not found
        """
        return self.source_configs.get(source_id)
    
    def get_all_source_configs(self) -> Dict[str, DataSourceConfig]:
        """Get all source configurations.
        
        Returns:
            Dictionary mapping source_id to DataSourceConfig
        """
        return self.source_configs.copy()
    
    def get_enabled_source_configs(self) -> Dict[str, DataSourceConfig]:
        """Get only enabled source configurations.
        
        Returns:
            Dictionary mapping source_id to enabled DataSourceConfig
        """
        return {
            source_id: config 
            for source_id, config in self.source_configs.items() 
            if config.enabled
        }
    
    def get_sources_by_type(self, source_type: str) -> Dict[str, DataSourceConfig]:
        """Get sources filtered by type.
        
        Args:
            source_type: Source type (e.g., 'rss', 'crawler', 'api')
            
        Returns:
            Dictionary mapping source_id to DataSourceConfig
        """
        return {
            source_id: config 
            for source_id, config in self.source_configs.items() 
            if config.source_type == source_type
        }
    
    def get_sources_by_priority(self, priority: str) -> Dict[str, DataSourceConfig]:
        """Get sources filtered by priority.
        
        Args:
            priority: Priority level ('critical', 'high', 'medium', 'low')
            
        Returns:
            Dictionary mapping source_id to DataSourceConfig
        """
        return {
            source_id: config 
            for source_id, config in self.source_configs.items() 
            if config.priority == priority
        }
    
    def get_sources_by_category(self, category: str) -> Dict[str, DataSourceConfig]:
        """Get sources filtered by category.
        
        Args:
            category: Category (e.g., 'news', 'government', 'fact_check')
            
        Returns:
            Dictionary mapping source_id to DataSourceConfig
        """
        return {
            source_id: config 
            for source_id, config in self.source_configs.items() 
            if config.category == category
        }
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global configuration settings.
        
        Returns:
            Global configuration dictionary
        """
        return self.config_data.get('global', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration.
        
        Returns:
            Monitoring configuration dictionary
        """
        return self.config_data.get('monitoring', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration.
        
        Returns:
            Performance configuration dictionary
        """
        return self.config_data.get('performance', {})
    
    def get_priority_scheduling_config(self) -> Dict[str, Any]:
        """Get priority-based scheduling configuration.
        
        Returns:
            Priority scheduling configuration dictionary
        """
        return self.config_data.get('priority_scheduling', {})
    
    def update_source_config(self, source_id: str, updates: Dict[str, Any]) -> bool:
        """Update configuration for a specific source.
        
        Args:
            source_id: Source identifier
            updates: Configuration updates to apply
            
        Returns:
            True if updated successfully
        """
        if source_id not in self.source_configs:
            logger.error(f"Source not found: {source_id}")
            return False
        
        try:
            config = self.source_configs[source_id]
            
            # Update known fields
            for field, value in updates.items():
                if hasattr(config, field):
                    setattr(config, field, value)
                else:
                    # Add to custom config
                    config.custom_config[field] = value
            
            logger.info(f"Updated configuration for source: {source_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update config for {source_id}: {e}")
            return False
    
    def enable_source(self, source_id: str) -> bool:
        """Enable a data source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            True if enabled successfully
        """
        return self.update_source_config(source_id, {'enabled': True})
    
    def disable_source(self, source_id: str) -> bool:
        """Disable a data source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            True if disabled successfully
        """
        return self.update_source_config(source_id, {'enabled': False})
    
    def save_config(self, output_path: Optional[Union[str, Path]] = None) -> bool:
        """Save current configuration to file.
        
        Args:
            output_path: Optional output path (defaults to current config path)
            
        Returns:
            True if saved successfully
        """
        output_path = Path(output_path) if output_path else self.config_path
        
        try:
            # Rebuild config data from current source configs
            self._rebuild_config_data()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                if output_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config_data, f, default_flow_style=False, indent=2)
                elif output_path.suffix.lower() == '.json':
                    json.dump(self.config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported output format: {output_path.suffix}")
            
            logger.info(f"Saved configuration to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration to {output_path}: {e}")
            return False
    
    def _rebuild_config_data(self):
        """Rebuild config data from current source configurations."""
        # This is a simplified rebuild - in practice, you'd want to maintain
        # the original structure and just update the source configurations
        pass
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate all source configurations.
        
        Returns:
            Dictionary mapping source_id to list of validation errors
        """
        validation_results = {}
        
        for source_id, config in self.source_configs.items():
            errors = []
            
            # Basic validation
            if not config.source_id:
                errors.append("Missing source_id")
            
            if not config.source_type:
                errors.append("Missing source_type")
            
            if config.fetch_interval < 60:
                errors.append("fetch_interval must be at least 60 seconds")
            
            if not (0 <= config.reliability_score <= 1):
                errors.append("reliability_score must be between 0 and 1")
            
            # Type-specific validation
            if config.source_type == 'rss' and not config.feed_url:
                errors.append("RSS sources must have feed_url")
            
            if config.source_type == 'crawler' and not config.base_url:
                errors.append("Crawler sources must have base_url")
            
            if config.source_type == 'api' and not config.api_endpoint:
                errors.append("API sources must have api_endpoint")
            
            validation_results[source_id] = errors
        
        return validation_results
    
    def get_config_stats(self) -> Dict[str, Any]:
        """Get configuration statistics.
        
        Returns:
            Dictionary with configuration statistics
        """
        total_sources = len(self.source_configs)
        enabled_sources = len(self.get_enabled_source_configs())
        
        # Count by type
        type_counts = {}
        for config in self.source_configs.values():
            source_type = config.source_type
            type_counts[source_type] = type_counts.get(source_type, 0) + 1
        
        # Count by priority
        priority_counts = {}
        for config in self.source_configs.values():
            priority = config.priority
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Count by category
        category_counts = {}
        for config in self.source_configs.values():
            category = config.category
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by language
        language_counts = {}
        for config in self.source_configs.values():
            language = config.language
            language_counts[language] = language_counts.get(language, 0) + 1
        
        return {
            'total_sources': total_sources,
            'enabled_sources': enabled_sources,
            'disabled_sources': total_sources - enabled_sources,
            'type_counts': type_counts,
            'priority_counts': priority_counts,
            'category_counts': category_counts,
            'language_counts': language_counts,
            'avg_reliability_score': sum(
                config.reliability_score for config in self.source_configs.values()
            ) / total_sources if total_sources > 0 else 0,
            'config_file': str(self.config_path)
        }
    
    def export_for_registry(self) -> Dict[str, Dict[str, Any]]:
        """Export configurations in format suitable for DataSourceRegistry.
        
        Returns:
            Dictionary mapping source_id to configuration dictionary
        """
        return {
            source_id: config.to_dict() 
            for source_id, config in self.source_configs.items()
        }


# Utility functions
def load_config_from_file(config_path: Union[str, Path]) -> ConfigManager:
    """Load configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured ConfigManager instance
    """
    manager = ConfigManager(config_path)
    return manager


def create_default_config(output_path: Union[str, Path]) -> bool:
    """Create a default configuration file.
    
    Args:
        output_path: Path where to create the default config
        
    Returns:
        True if created successfully
    """
    try:
        # This would create a minimal default configuration
        default_config = {
            'global': {
                'enabled': True,
                'max_concurrent_sources': 10,
                'default_fetch_interval': 300
            },
            'rss_feeds': {
                'enabled': True,
                'national_english': {
                    'times_of_india': {
                        'source_type': 'rss',
                        'feed_url': 'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
                        'enabled': True,
                        'priority': 'high'
                    }
                }
            }
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created default configuration at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create default config: {e}")
        return False