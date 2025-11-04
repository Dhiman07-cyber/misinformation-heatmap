#!/usr/bin/env python3
"""
Data source registry for managing and discovering data connectors.
Provides centralized registration and configuration management.
"""

import logging
from typing import Dict, List, Type, Any, Optional
import importlib
import inspect

from .base.base_connector import BaseDataConnector
from .rss.rss_connector import RSSConnector

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """Registry for data source connectors."""
    
    def __init__(self):
        """Initialize the data source registry."""
        self._connectors: Dict[str, Type[BaseDataConnector]] = {}
        self._instances: Dict[str, BaseDataConnector] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in connectors
        self._register_builtin_connectors()
    
    def _register_builtin_connectors(self):
        """Register built-in connector types."""
        self.register_connector_type('rss', RSSConnector)
        
        # Register crawler types
        try:
            from .crawlers.web_crawler import WebCrawler
            from .crawlers.news_crawler import NewsCrawler
            self.register_connector_type('crawler', WebCrawler)
            self.register_connector_type('news_crawler', NewsCrawler)
        except ImportError as e:
            logger.warning(f"Could not register crawler connectors: {e}")
        
        logger.info("Registered built-in connectors")
    
    def register_connector_type(self, connector_type: str, connector_class: Type[BaseDataConnector]):
        """Register a connector type.
        
        Args:
            connector_type: Type identifier (e.g., 'rss', 'crawler', 'api')
            connector_class: Connector class that inherits from BaseDataConnector
        """
        if not issubclass(connector_class, BaseDataConnector):
            raise ValueError(f"Connector class must inherit from BaseDataConnector")
        
        self._connectors[connector_type] = connector_class
        logger.info(f"Registered connector type: {connector_type}")
    
    def register_source(self, source_id: str, config: Dict[str, Any]) -> BaseDataConnector:
        """Register a data source with configuration.
        
        Args:
            source_id: Unique source identifier
            config: Source configuration dictionary
            
        Returns:
            Configured connector instance
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate configuration
        if 'source_type' not in config:
            raise ValueError("Configuration must include 'source_type'")
        
        source_type = config['source_type']
        if source_type not in self._connectors:
            raise ValueError(f"Unknown connector type: {source_type}")
        
        # Add source_id to config if not present
        config = config.copy()
        config['source_id'] = source_id
        
        # Create connector instance
        connector_class = self._connectors[source_type]
        try:
            connector = connector_class(config)
            
            # Validate configuration
            connector.validate_config()
            
            # Store instance and configuration
            self._instances[source_id] = connector
            self._configurations[source_id] = config
            
            logger.info(f"Registered data source: {source_id} ({source_type})")
            return connector
            
        except Exception as e:
            logger.error(f"Failed to register source {source_id}: {e}")
            raise ValueError(f"Failed to register source {source_id}: {e}")
    
    def register_sources_from_config(self, sources_config: Dict[str, Dict[str, Any]]) -> Dict[str, BaseDataConnector]:
        """Register multiple sources from configuration dictionary.
        
        Args:
            sources_config: Dictionary mapping source_id to configuration
            
        Returns:
            Dictionary mapping source_id to connector instances
        """
        connectors = {}
        errors = []
        
        for source_id, config in sources_config.items():
            try:
                connector = self.register_source(source_id, config)
                connectors[source_id] = connector
            except Exception as e:
                errors.append(f"{source_id}: {e}")
                logger.error(f"Failed to register source {source_id}: {e}")
        
        if errors:
            logger.warning(f"Failed to register {len(errors)} sources: {errors}")
        
        logger.info(f"Successfully registered {len(connectors)} data sources")
        return connectors
    
    def get_connector(self, source_id: str) -> Optional[BaseDataConnector]:
        """Get connector instance by source ID.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Connector instance or None if not found
        """
        return self._instances.get(source_id)
    
    def get_connectors_by_type(self, source_type: str) -> List[BaseDataConnector]:
        """Get all connectors of a specific type.
        
        Args:
            source_type: Connector type (e.g., 'rss', 'crawler')
            
        Returns:
            List of connector instances
        """
        return [
            connector for connector in self._instances.values()
            if connector.source_type == source_type
        ]
    
    def get_enabled_connectors(self) -> List[BaseDataConnector]:
        """Get all enabled connectors.
        
        Returns:
            List of enabled connector instances
        """
        return [
            connector for connector in self._instances.values()
            if connector.enabled
        ]
    
    def get_all_connectors(self) -> Dict[str, BaseDataConnector]:
        """Get all registered connectors.
        
        Returns:
            Dictionary mapping source_id to connector instances
        """
        return self._instances.copy()
    
    def unregister_source(self, source_id: str) -> bool:
        """Unregister a data source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            True if source was unregistered, False if not found
        """
        if source_id in self._instances:
            del self._instances[source_id]
            del self._configurations[source_id]
            logger.info(f"Unregistered data source: {source_id}")
            return True
        return False
    
    def update_source_config(self, source_id: str, config_updates: Dict[str, Any]) -> bool:
        """Update configuration for a registered source.
        
        Args:
            source_id: Source identifier
            config_updates: Configuration updates to apply
            
        Returns:
            True if updated successfully, False if source not found
        """
        if source_id not in self._configurations:
            return False
        
        # Update configuration
        old_config = self._configurations[source_id].copy()
        new_config = old_config.copy()
        new_config.update(config_updates)
        
        try:
            # Re-register with new configuration
            self.register_source(source_id, new_config)
            logger.info(f"Updated configuration for source: {source_id}")
            return True
            
        except Exception as e:
            # Restore old configuration on failure
            self._configurations[source_id] = old_config
            logger.error(f"Failed to update source {source_id}: {e}")
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
    
    def get_source_config(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            Configuration dictionary or None if not found
        """
        return self._configurations.get(source_id, {}).copy()
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics.
        
        Returns:
            Dictionary with registry statistics
        """
        total_sources = len(self._instances)
        enabled_sources = len(self.get_enabled_connectors())
        
        # Count by type
        type_counts = {}
        for connector in self._instances.values():
            source_type = connector.source_type
            type_counts[source_type] = type_counts.get(source_type, 0) + 1
        
        # Get connector statistics
        connector_stats = {}
        for source_id, connector in self._instances.items():
            try:
                connector_stats[source_id] = connector.get_stats()
            except Exception as e:
                logger.warning(f"Failed to get stats for {source_id}: {e}")
                connector_stats[source_id] = {'error': str(e)}
        
        return {
            'total_sources': total_sources,
            'enabled_sources': enabled_sources,
            'registered_types': list(self._connectors.keys()),
            'type_counts': type_counts,
            'connector_stats': connector_stats
        }
    
    def validate_all_sources(self) -> Dict[str, List[str]]:
        """Validate all registered sources.
        
        Returns:
            Dictionary mapping source_id to list of validation errors
        """
        validation_results = {}
        
        for source_id, connector in self._instances.items():
            try:
                connector.validate_config()
                validation_results[source_id] = []  # No errors
            except Exception as e:
                validation_results[source_id] = [str(e)]
        
        return validation_results
    
    async def health_check_all_sources(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all registered sources.
        
        Returns:
            Dictionary mapping source_id to health status
        """
        health_results = {}
        
        for source_id, connector in self._instances.items():
            try:
                health_status = await connector.get_health_status()
                health_results[source_id] = health_status
            except Exception as e:
                health_results[source_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return health_results
    
    def discover_connectors(self, package_path: str = None) -> List[str]:
        """Discover and register connector classes from a package.
        
        Args:
            package_path: Python package path to search for connectors
            
        Returns:
            List of discovered connector type names
        """
        discovered = []
        
        if not package_path:
            # Default discovery paths
            discovery_paths = [
                'backend.data_sources.rss',
                'backend.data_sources.crawlers',
                'backend.data_sources.apis'
            ]
        else:
            discovery_paths = [package_path]
        
        for path in discovery_paths:
            try:
                module = importlib.import_module(path)
                
                # Find connector classes in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseDataConnector) and 
                        obj != BaseDataConnector):
                        
                        # Register the connector type
                        connector_type = name.lower().replace('connector', '')
                        if connector_type not in self._connectors:
                            self.register_connector_type(connector_type, obj)
                            discovered.append(connector_type)
                            
            except ImportError as e:
                logger.debug(f"Could not import {path}: {e}")
            except Exception as e:
                logger.warning(f"Error discovering connectors in {path}: {e}")
        
        return discovered
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export all source configurations.
        
        Returns:
            Dictionary with all source configurations
        """
        return {
            'connector_types': list(self._connectors.keys()),
            'sources': self._configurations.copy()
        }
    
    def import_configuration(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Import source configurations.
        
        Args:
            config: Configuration dictionary with 'sources' key
            
        Returns:
            Dictionary mapping source_id to import status
        """
        results = {}
        
        sources_config = config.get('sources', {})
        for source_id, source_config in sources_config.items():
            try:
                self.register_source(source_id, source_config)
                results[source_id] = 'success'
            except Exception as e:
                results[source_id] = f'error: {e}'
        
        return results


# Global registry instance
_global_registry = None


def get_registry() -> DataSourceRegistry:
    """Get the global data source registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = DataSourceRegistry()
    return _global_registry


def register_source(source_id: str, config: Dict[str, Any]) -> BaseDataConnector:
    """Register a data source using the global registry."""
    return get_registry().register_source(source_id, config)


def get_connector(source_id: str) -> Optional[BaseDataConnector]:
    """Get a connector from the global registry."""
    return get_registry().get_connector(source_id)


def get_enabled_connectors() -> List[BaseDataConnector]:
    """Get all enabled connectors from the global registry."""
    return get_registry().get_enabled_connectors()