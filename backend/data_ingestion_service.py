#!/usr/bin/env python3
"""
Data ingestion service that integrates the new modular data sources
with the existing misinformation heatmap backend.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import json

from data_sources import DataSourceRegistry, IngestionCoordinator, RawEvent
from data_sources.config_manager import ConfigManager
from data_sources.base.data_validator import DataValidator

# Import existing backend components
from nlp_analyzer import NLPAnalyzer
from satellite_client import SatelliteClient
from database import Database
from config import Config

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Service that orchestrates data ingestion with existing backend components."""
    
    def __init__(self, config: Config):
        """Initialize the data ingestion service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        
        # Initialize existing components
        self.nlp_analyzer = NLPAnalyzer()
        self.satellite_client = SatelliteClient()
        self.database = Database()
        
        # Initialize new data source components
        self.config_manager = ConfigManager("config/data_sources.yaml")
        self.registry = DataSourceRegistry()
        self.validator = DataValidator()
        self.coordinator = None
        
        # Service state
        self.running = False
        self.stats = {
            'service_start_time': None,
            'total_events_processed': 0,
            'total_events_stored': 0,
            'processing_errors': 0,
            'last_processing_time': None
        }
        
        logger.info("Data ingestion service initialized")
    
    async def initialize(self):
        """Initialize the service and load configurations."""
        try:
            # Load data source configurations
            self.config_manager.load_config()
            
            # Register data sources with registry
            source_configs = self.config_manager.export_for_registry()
            self.registry.register_sources_from_config(source_configs)
            
            # Create ingestion coordinator with event processor
            self.coordinator = IngestionCoordinator(
                registry=self.registry,
                validator=self.validator,
                event_processor=self._process_raw_event
            )
            
            # Get global configuration
            global_config = self.config_manager.get_global_config()
            
            # Configure coordinator settings
            if global_config:
                self.coordinator.batch_size = global_config.get('batch_size', 100)
                self.coordinator.max_concurrent_sources = global_config.get('max_concurrent_sources', 10)
                self.coordinator.fetch_timeout = global_config.get('fetch_timeout', 300)
            
            logger.info("Data ingestion service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data ingestion service: {e}")
            raise
    
    async def start_continuous_ingestion(self):
        """Start continuous data ingestion."""
        if self.running:
            logger.warning("Data ingestion service is already running")
            return
        
        try:
            self.running = True
            self.stats['service_start_time'] = datetime.now(timezone.utc)
            
            # Start continuous ingestion with priority-based scheduling
            priority_config = self.config_manager.get_priority_scheduling_config()
            
            if priority_config:
                # Start with priority-based intervals
                await self._start_priority_based_ingestion(priority_config)
            else:
                # Start with default settings
                await self.coordinator.start_continuous_ingestion(
                    default_interval=300,  # 5 minutes
                    stagger_delay=30       # 30 seconds between sources
                )
            
            logger.info("Started continuous data ingestion")
            
        except Exception as e:
            logger.error(f"Failed to start continuous ingestion: {e}")
            self.running = False
            raise
    
    async def _start_priority_based_ingestion(self, priority_config: Dict[str, Any]):
        """Start ingestion with priority-based scheduling."""
        
        # Configure sources by priority
        for priority, config in priority_config.items():
            if priority in ['critical', 'high', 'medium', 'low']:
                sources = config.get('sources', [])
                interval = config.get('fetch_interval', 300)
                
                # Update fetch intervals for priority sources
                interval_updates = {source_id: interval for source_id in sources}
                self.coordinator.configure_source_intervals(interval_updates)
        
        # Start continuous ingestion
        await self.coordinator.start_continuous_ingestion(
            default_interval=600,  # 10 minutes default
            stagger_delay=15       # 15 seconds between sources
        )
    
    async def stop_continuous_ingestion(self):
        """Stop continuous data ingestion."""
        if not self.running:
            return
        
        try:
            await self.coordinator.stop_continuous_ingestion()
            self.running = False
            logger.info("Stopped continuous data ingestion")
            
        except Exception as e:
            logger.error(f"Error stopping continuous ingestion: {e}")
    
    async def _process_raw_event(self, raw_event: RawEvent):
        """Process a raw event through the existing backend pipeline.
        
        Args:
            raw_event: Raw event from data source
        """
        try:
            logger.debug(f"Processing raw event: {raw_event.event_id}")
            
            # Step 1: NLP Analysis
            nlp_result = await self._perform_nlp_analysis(raw_event)
            
            # Step 2: Satellite Validation (if applicable)
            satellite_result = await self._perform_satellite_validation(raw_event, nlp_result)
            
            # Step 3: Create processed event
            processed_event = self._create_processed_event(raw_event, nlp_result, satellite_result)
            
            # Step 4: Store in database
            await self._store_processed_event(processed_event)
            
            # Update statistics
            self.stats['total_events_processed'] += 1
            self.stats['total_events_stored'] += 1
            self.stats['last_processing_time'] = datetime.now(timezone.utc)
            
            logger.debug(f"Successfully processed event: {raw_event.event_id}")
            
        except Exception as e:
            logger.error(f"Failed to process event {raw_event.event_id}: {e}")
            self.stats['processing_errors'] += 1
            raise
    
    async def _perform_nlp_analysis(self, raw_event: RawEvent) -> Dict[str, Any]:
        """Perform NLP analysis on raw event content."""
        try:
            # Use existing NLP analyzer
            analysis_result = self.nlp_analyzer.analyze(raw_event.content)
            
            # Convert to dictionary format
            nlp_result = {
                'language': analysis_result.get('language', raw_event.language),
                'entities': analysis_result.get('entities', []),
                'sentiment_score': analysis_result.get('sentiment_score', 0.0),
                'confidence_score': analysis_result.get('confidence_score', 0.0),
                'virality_score': analysis_result.get('virality_score', 0.0),
                'reality_score': analysis_result.get('reality_score', 0.0),
                'misinformation_risk': analysis_result.get('misinformation_risk', 0.0),
                'claims': analysis_result.get('claims', []),
                'categories': analysis_result.get('categories', []),
                'dominant_category': analysis_result.get('dominant_category', 'unknown')
            }
            
            # Update location hint if NLP found better location
            if analysis_result.get('location') and not raw_event.location_hint:
                raw_event.location_hint = analysis_result['location']
            
            return nlp_result
            
        except Exception as e:
            logger.error(f"NLP analysis failed for event {raw_event.event_id}: {e}")
            # Return default values on failure
            return {
                'language': raw_event.language or 'en',
                'entities': [],
                'sentiment_score': 0.0,
                'confidence_score': 0.0,
                'virality_score': 0.5,  # Default moderate virality
                'reality_score': 0.5,   # Default moderate reality
                'misinformation_risk': 0.5,  # Default moderate risk
                'claims': [],
                'categories': ['unknown'],
                'dominant_category': 'unknown'
            }
    
    async def _perform_satellite_validation(self, raw_event: RawEvent, nlp_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Perform satellite validation if applicable."""
        try:
            # Check if satellite validation is relevant
            if not self._should_perform_satellite_validation(raw_event, nlp_result):
                return None
            
            # Extract coordinates (simplified - in practice, you'd use geocoding)
            location = raw_event.location_hint or nlp_result.get('location')
            if not location:
                return None
            
            # Get coordinates for location (this would need a geocoding service)
            coordinates = self._get_coordinates_for_location(location)
            if not coordinates:
                return None
            
            lat, lon = coordinates
            
            # Perform satellite validation
            satellite_result = self.satellite_client.validate_location(lat, lon)
            
            return {
                'similarity': satellite_result.get('similarity', 0.0),
                'anomaly': satellite_result.get('anomaly', False),
                'confidence': satellite_result.get('confidence', 0.0),
                'baseline_date': satellite_result.get('baseline_date'),
                'coordinates': {'lat': lat, 'lon': lon}
            }
            
        except Exception as e:
            logger.error(f"Satellite validation failed for event {raw_event.event_id}: {e}")
            return None
    
    def _should_perform_satellite_validation(self, raw_event: RawEvent, nlp_result: Dict[str, Any]) -> bool:
        """Determine if satellite validation should be performed."""
        
        # Check if content mentions infrastructure, development, or physical changes
        infrastructure_keywords = [
            'infrastructure', 'construction', 'building', 'road', 'bridge', 'development',
            'demolition', 'project', 'site', 'facility', 'structure', 'expansion'
        ]
        
        content_lower = raw_event.content.lower()
        
        # Check for infrastructure-related content
        has_infrastructure_content = any(keyword in content_lower for keyword in infrastructure_keywords)
        
        # Check categories from NLP
        infrastructure_categories = ['infrastructure', 'development', 'construction']
        has_infrastructure_category = any(
            cat in infrastructure_categories 
            for cat in nlp_result.get('categories', [])
        )
        
        return has_infrastructure_content or has_infrastructure_category
    
    def _get_coordinates_for_location(self, location: str) -> Optional[tuple[float, float]]:
        """Get coordinates for a location name (simplified implementation)."""
        
        # Simplified coordinate mapping for major Indian cities/states
        # In production, you'd use a proper geocoding service
        location_coordinates = {
            'mumbai': (19.0760, 72.8777),
            'delhi': (28.7041, 77.1025),
            'bangalore': (12.9716, 77.5946),
            'chennai': (13.0827, 80.2707),
            'kolkata': (22.5726, 88.3639),
            'hyderabad': (17.3850, 78.4867),
            'pune': (18.5204, 73.8567),
            'ahmedabad': (23.0225, 72.5714),
            'maharashtra': (19.7515, 75.7139),
            'karnataka': (15.3173, 75.7139),
            'tamil nadu': (11.1271, 78.6569),
            'gujarat': (23.0225, 72.5714),
            'west bengal': (22.9868, 87.8550),
            'rajasthan': (27.0238, 74.2179),
            'uttar pradesh': (26.8467, 80.9462)
        }
        
        location_lower = location.lower()
        
        # Direct match
        if location_lower in location_coordinates:
            return location_coordinates[location_lower]
        
        # Partial match
        for loc, coords in location_coordinates.items():
            if loc in location_lower or location_lower in loc:
                return coords
        
        return None
    
    def _create_processed_event(self, raw_event: RawEvent, nlp_result: Dict[str, Any], satellite_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create processed event for database storage."""
        
        processed_event = {
            # Original event data
            'event_id': raw_event.event_id,
            'source': raw_event.source_id,
            'source_type': raw_event.source_type,
            'original_text': raw_event.content,
            'processed_text': raw_event.content,  # Could be cleaned/processed
            'timestamp': raw_event.timestamp,
            'url': raw_event.url,
            'title': raw_event.title,
            'author': raw_event.author,
            
            # NLP analysis results
            'lang': nlp_result['language'],
            'region_hint': raw_event.location_hint,
            'entities': nlp_result['entities'],
            'sentiment_score': nlp_result['sentiment_score'],
            'confidence_score': nlp_result['confidence_score'],
            'virality_score': nlp_result['virality_score'],
            'reality_score': nlp_result['reality_score'],
            'misinformation_risk': nlp_result['misinformation_risk'],
            'claims': nlp_result['claims'],
            'categories': nlp_result['categories'],
            'dominant_category': nlp_result['dominant_category'],
            
            # Metadata
            'metadata': {
                'raw_event_metadata': raw_event.metadata,
                'processing_timestamp': datetime.now(timezone.utc).isoformat(),
                'nlp_version': getattr(self.nlp_analyzer, 'version', '1.0'),
                'reliability_score': raw_event.metadata.get('reliability_score', 0.7)
            }
        }
        
        # Add satellite validation results if available
        if satellite_result:
            processed_event['satellite_data'] = satellite_result
            processed_event['metadata']['satellite_validated'] = True
        else:
            processed_event['metadata']['satellite_validated'] = False
        
        # Add coordinates if available
        if satellite_result and 'coordinates' in satellite_result:
            coords = satellite_result['coordinates']
            processed_event['lat'] = coords['lat']
            processed_event['lon'] = coords['lon']
        
        return processed_event
    
    async def _store_processed_event(self, processed_event: Dict[str, Any]):
        """Store processed event in database."""
        try:
            # Use existing database interface
            await self.database.store_event(processed_event)
            logger.debug(f"Stored processed event: {processed_event['event_id']}")
            
        except Exception as e:
            logger.error(f"Failed to store event {processed_event['event_id']}: {e}")
            raise
    
    async def manual_fetch_all_sources(self) -> Dict[str, List[RawEvent]]:
        """Manually trigger fetch from all sources."""
        if not self.coordinator:
            raise RuntimeError("Service not initialized")
        
        logger.info("Manual fetch triggered for all sources")
        return await self.coordinator.manual_fetch_all()
    
    async def fetch_from_source(self, source_id: str) -> List[RawEvent]:
        """Fetch events from a specific source."""
        if not self.coordinator:
            raise RuntimeError("Service not initialized")
        
        return await self.coordinator.fetch_from_source(source_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the ingestion service."""
        try:
            # Check service status
            service_status = {
                'running': self.running,
                'initialized': self.coordinator is not None,
                'start_time': self.stats['service_start_time'].isoformat() if self.stats['service_start_time'] else None
            }
            
            # Check data source health
            source_health = {}
            if self.coordinator:
                source_health = await self.coordinator.health_check_sources()
            
            # Check component health
            component_health = {
                'nlp_analyzer': 'healthy',  # Could add actual health check
                'satellite_client': 'healthy',  # Could add actual health check
                'database': 'healthy'  # Could add actual health check
            }
            
            # Overall health determination
            unhealthy_sources = sum(1 for status in source_health.values() if status.get('status') != 'healthy')
            total_sources = len(source_health)
            
            if total_sources == 0:
                overall_status = 'no_sources'
            elif unhealthy_sources == 0:
                overall_status = 'healthy'
            elif unhealthy_sources / total_sources < 0.5:
                overall_status = 'degraded'
            else:
                overall_status = 'unhealthy'
            
            return {
                'status': overall_status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': service_status,
                'sources': source_health,
                'components': component_health,
                'statistics': self.get_service_stats()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'error',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        stats = self.stats.copy()
        
        # Add coordinator stats if available
        if self.coordinator:
            coordinator_stats = self.coordinator.get_ingestion_stats()
            stats.update(coordinator_stats)
        
        # Add configuration stats
        config_stats = self.config_manager.get_config_stats()
        stats['configuration'] = config_stats
        
        return stats
    
    def get_source_status(self) -> Dict[str, Any]:
        """Get status of all data sources."""
        if not self.coordinator:
            return {}
        
        return self.coordinator.get_source_status()
    
    async def reload_configuration(self) -> bool:
        """Reload data source configuration."""
        try:
            # Stop current ingestion
            if self.running:
                await self.stop_continuous_ingestion()
            
            # Reload configuration
            self.config_manager.load_config()
            
            # Re-register sources
            source_configs = self.config_manager.export_for_registry()
            self.registry = DataSourceRegistry()  # Create new registry
            self.registry.register_sources_from_config(source_configs)
            
            # Recreate coordinator
            self.coordinator = IngestionCoordinator(
                registry=self.registry,
                validator=self.validator,
                event_processor=self._process_raw_event
            )
            
            logger.info("Configuration reloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def enable_source(self, source_id: str) -> bool:
        """Enable a data source."""
        return self.config_manager.enable_source(source_id)
    
    def disable_source(self, source_id: str) -> bool:
        """Disable a data source."""
        return self.config_manager.disable_source(source_id)


# Global service instance
_ingestion_service = None


def get_ingestion_service(config: Optional[Config] = None) -> DataIngestionService:
    """Get the global data ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        if config is None:
            from config import Config
            config = Config()
        _ingestion_service = DataIngestionService(config)
    return _ingestion_service


async def initialize_ingestion_service(config: Optional[Config] = None) -> DataIngestionService:
    """Initialize the global data ingestion service."""
    service = get_ingestion_service(config)
    await service.initialize()
    return service