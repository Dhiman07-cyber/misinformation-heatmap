#!/usr/bin/env python3
"""
Integration test for the new data sources system.
Tests the complete flow from configuration to data ingestion.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from data_sources.config_manager import ConfigManager
from data_sources.registry import DataSourceRegistry
from data_sources.coordinator import IngestionCoordinator
from data_sources.base.data_validator import DataValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_configuration_loading():
    """Test configuration loading and parsing."""
    logger.info("Testing configuration loading...")
    
    try:
        # Load configuration
        config_manager = ConfigManager("config/data_sources.yaml")
        
        # Get statistics
        stats = config_manager.get_config_stats()
        logger.info(f"Loaded {stats['total_sources']} sources ({stats['enabled_sources']} enabled)")
        
        # Test source retrieval
        rss_sources = config_manager.get_sources_by_type('rss')
        logger.info(f"Found {len(rss_sources)} RSS sources")
        
        fact_check_sources = config_manager.get_sources_by_category('fact_check')
        logger.info(f"Found {len(fact_check_sources)} fact-checking sources")
        
        high_priority_sources = config_manager.get_sources_by_priority('critical')
        logger.info(f"Found {len(high_priority_sources)} critical priority sources")
        
        return True
        
    except Exception as e:
        logger.error(f"Configuration loading failed: {e}")
        return False


async def test_registry_integration():
    """Test data source registry integration."""
    logger.info("Testing registry integration...")
    
    try:
        # Load configuration
        config_manager = ConfigManager("config/data_sources.yaml")
        
        # Create registry and register sources
        registry = DataSourceRegistry()
        source_configs = config_manager.export_for_registry()
        
        connectors = registry.register_sources_from_config(source_configs)
        logger.info(f"Registered {len(connectors)} connectors")
        
        # Test connector retrieval
        enabled_connectors = registry.get_enabled_connectors()
        logger.info(f"Found {len(enabled_connectors)} enabled connectors")
        
        # Test specific connector
        times_of_india = registry.get_connector('times_of_india')
        if times_of_india:
            logger.info(f"Times of India connector: {times_of_india}")
            
            # Test health check
            health = await times_of_india.get_health_status()
            logger.info(f"Times of India health: {health['status']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Registry integration failed: {e}")
        return False


async def test_data_validation():
    """Test data validation system."""
    logger.info("Testing data validation...")
    
    try:
        from data_sources.base.base_connector import RawEvent
        from datetime import datetime, timezone
        
        validator = DataValidator()
        
        # Test valid event
        valid_event = RawEvent(
            source_id="test_source",
            source_type="test",
            content="This is a test news article about infrastructure development in Maharashtra, India. The government has announced new projects.",
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/test",
            title="Test News Article",
            language="en",
            location_hint="Maharashtra"
        )
        
        is_valid, reason = validator.validate_event(valid_event)
        logger.info(f"Valid event validation: {is_valid} ({reason})")
        
        # Test invalid event (too short)
        invalid_event = RawEvent(
            source_id="test_source",
            source_type="test",
            content="Short",
            timestamp=datetime.now(timezone.utc)
        )
        
        is_valid, reason = validator.validate_event(invalid_event)
        logger.info(f"Invalid event validation: {is_valid} ({reason})")
        
        # Get validation stats
        stats = validator.get_stats()
        logger.info(f"Validation stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"Data validation test failed: {e}")
        return False


async def test_single_source_fetch():
    """Test fetching from a single source."""
    logger.info("Testing single source fetch...")
    
    try:
        # Load configuration and create registry
        config_manager = ConfigManager("config/data_sources.yaml")
        registry = DataSourceRegistry()
        source_configs = config_manager.export_for_registry()
        registry.register_sources_from_config(source_configs)
        
        # Get a reliable source (PIB)
        pib_connector = registry.get_connector('pib_national')
        if not pib_connector:
            logger.warning("PIB connector not found, trying Times of India")
            pib_connector = registry.get_connector('times_of_india')
        
        if pib_connector:
            logger.info(f"Testing fetch from: {pib_connector.source_id}")
            
            # Fetch events (limit to avoid overwhelming)
            events = await pib_connector.fetch_events()
            logger.info(f"Fetched {len(events)} events from {pib_connector.source_id}")
            
            if events:
                sample_event = events[0]
                logger.info(f"Sample event: {sample_event.title[:100]}...")
                logger.info(f"Content length: {len(sample_event.content)}")
                logger.info(f"Language: {sample_event.language}")
                logger.info(f"Location hint: {sample_event.location_hint}")
        
        return True
        
    except Exception as e:
        logger.error(f"Single source fetch failed: {e}")
        return False


async def test_coordinator_integration():
    """Test ingestion coordinator."""
    logger.info("Testing coordinator integration...")
    
    try:
        # Setup components
        config_manager = ConfigManager("config/data_sources.yaml")
        registry = DataSourceRegistry()
        validator = DataValidator()
        
        # Register only a few sources for testing
        test_sources = {
            'pib_national': config_manager.get_source_config('pib_national'),
            'alt_news': config_manager.get_source_config('alt_news')
        }
        
        # Filter out None values
        test_sources = {k: v for k, v in test_sources.items() if v is not None}
        
        if test_sources:
            # Convert to registry format
            registry_configs = {}
            for source_id, config in test_sources.items():
                if config:
                    registry_configs[source_id] = config.to_dict()
            
            registry.register_sources_from_config(registry_configs)
            
            # Create coordinator
            coordinator = IngestionCoordinator(registry, validator)
            
            # Test manual fetch
            results = await coordinator.fetch_from_all_sources(max_concurrent=2)
            
            total_events = sum(len(events) for events in results.values())
            logger.info(f"Coordinator fetched {total_events} total events from {len(results)} sources")
            
            # Get coordinator stats
            stats = coordinator.get_ingestion_stats()
            logger.info(f"Coordinator stats: {stats['total_events']} events, {stats['total_validated']} validated")
        
        return True
        
    except Exception as e:
        logger.error(f"Coordinator integration failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    logger.info("Starting data sources integration tests...")
    
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("Registry Integration", test_registry_integration),
        ("Data Validation", test_data_validation),
        ("Single Source Fetch", test_single_source_fetch),
        ("Coordinator Integration", test_coordinator_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results[test_name] = result
            status = "PASSED" if result else "FAILED"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            logger.error(f"{test_name}: FAILED - {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All integration tests passed!")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())