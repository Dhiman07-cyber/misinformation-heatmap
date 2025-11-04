#!/usr/bin/env python3
"""
Ingestion coordinator for managing data source fetching and processing.
Orchestrates multiple data sources and handles event processing pipeline.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
import json
from dataclasses import asdict

from .base.base_connector import BaseDataConnector, RawEvent
from .base.data_validator import DataValidator
from .registry import DataSourceRegistry

logger = logging.getLogger(__name__)


class IngestionCoordinator:
    """Coordinates data ingestion from multiple sources."""
    
    def __init__(self, 
                 registry: DataSourceRegistry,
                 validator: Optional[DataValidator] = None,
                 event_processor: Optional[Callable] = None):
        """Initialize ingestion coordinator.
        
        Args:
            registry: Data source registry
            validator: Data validator instance
            event_processor: Function to process validated events
        """
        self.registry = registry
        self.validator = validator or DataValidator()
        self.event_processor = event_processor
        
        # Coordination settings
        self.batch_size = 100
        self.max_concurrent_sources = 10
        self.fetch_timeout = 300  # 5 minutes per source
        
        # State tracking
        self.last_fetch_times: Dict[str, datetime] = {}
        self.fetch_intervals: Dict[str, int] = {}
        self.running = False
        self.fetch_tasks: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self.stats = {
            'total_fetches': 0,
            'total_events': 0,
            'total_validated': 0,
            'total_processed': 0,
            'errors': 0,
            'last_run': None,
            'source_stats': {}
        }
    
    async def start_continuous_ingestion(self, 
                                       default_interval: int = 300,
                                       stagger_delay: int = 30):
        """Start continuous ingestion from all enabled sources.
        
        Args:
            default_interval: Default fetch interval in seconds
            stagger_delay: Delay between starting each source (seconds)
        """
        if self.running:
            logger.warning("Ingestion coordinator is already running")
            return
        
        self.running = True
        logger.info("Starting continuous data ingestion")
        
        # Get enabled connectors
        connectors = self.registry.get_enabled_connectors()
        if not connectors:
            logger.warning("No enabled connectors found")
            return
        
        # Start fetch tasks for each connector
        for i, connector in enumerate(connectors):
            # Stagger the start times to avoid overwhelming sources
            start_delay = i * stagger_delay
            
            # Get fetch interval from connector config or use default
            interval = getattr(connector, 'fetch_interval', default_interval)
            self.fetch_intervals[connector.source_id] = interval
            
            # Create and start fetch task
            task = asyncio.create_task(
                self._continuous_fetch_loop(connector, interval, start_delay)
            )
            self.fetch_tasks[connector.source_id] = task
            
            logger.info(f"Scheduled {connector.source_id} with {interval}s interval, {start_delay}s delay")
        
        logger.info(f"Started continuous ingestion for {len(connectors)} sources")
    
    async def stop_continuous_ingestion(self):
        """Stop continuous ingestion."""
        if not self.running:
            return
        
        logger.info("Stopping continuous data ingestion")
        self.running = False
        
        # Cancel all fetch tasks
        for source_id, task in self.fetch_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.debug(f"Cancelled fetch task for {source_id}")
        
        self.fetch_tasks.clear()
        logger.info("Stopped continuous data ingestion")
    
    async def _continuous_fetch_loop(self, 
                                   connector: BaseDataConnector, 
                                   interval: int,
                                   start_delay: int = 0):
        """Continuous fetch loop for a single connector."""
        
        # Initial delay to stagger starts
        if start_delay > 0:
            await asyncio.sleep(start_delay)
        
        source_id = connector.source_id
        logger.info(f"Starting continuous fetch for {source_id} (interval: {interval}s)")
        
        while self.running:
            try:
                # Fetch and process events
                await self.fetch_from_source(source_id)
                
                # Wait for next fetch
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info(f"Fetch loop cancelled for {source_id}")
                break
            except Exception as e:
                logger.error(f"Error in fetch loop for {source_id}: {e}")
                # Wait before retrying on error
                await asyncio.sleep(min(interval, 60))
    
    async def fetch_from_source(self, source_id: str) -> List[RawEvent]:
        """Fetch events from a specific source.
        
        Args:
            source_id: Source identifier
            
        Returns:
            List of processed events
        """
        connector = self.registry.get_connector(source_id)
        if not connector:
            raise ValueError(f"Source not found: {source_id}")
        
        if not connector.enabled:
            logger.debug(f"Skipping disabled source: {source_id}")
            return []
        
        try:
            # Determine since timestamp
            since = self.last_fetch_times.get(source_id)
            
            # Fetch events with timeout
            logger.debug(f"Fetching from {source_id} (since: {since})")
            
            events = await asyncio.wait_for(
                connector.fetch_events(since=since),
                timeout=self.fetch_timeout
            )
            
            # Update statistics
            self.stats['total_fetches'] += 1
            self.stats['total_events'] += len(events)
            self.last_fetch_times[source_id] = datetime.now(timezone.utc)
            
            # Initialize source stats if needed
            if source_id not in self.stats['source_stats']:
                self.stats['source_stats'][source_id] = {
                    'fetches': 0,
                    'events': 0,
                    'validated': 0,
                    'processed': 0,
                    'errors': 0,
                    'last_fetch': None
                }
            
            source_stats = self.stats['source_stats'][source_id]
            source_stats['fetches'] += 1
            source_stats['events'] += len(events)
            source_stats['last_fetch'] = datetime.now(timezone.utc).isoformat()
            
            if events:
                logger.info(f"Fetched {len(events)} events from {source_id}")
                
                # Process events in batches
                processed_events = await self._process_events_batch(events, source_id)
                return processed_events
            else:
                logger.debug(f"No new events from {source_id}")
                return []
                
        except asyncio.TimeoutError:
            error_msg = f"Fetch timeout for {source_id}"
            logger.error(error_msg)
            self._record_source_error(source_id, error_msg)
            return []
        except Exception as e:
            error_msg = f"Fetch error for {source_id}: {e}"
            logger.error(error_msg)
            self._record_source_error(source_id, error_msg)
            return []
    
    async def _process_events_batch(self, events: List[RawEvent], source_id: str) -> List[RawEvent]:
        """Process a batch of events through validation and processing pipeline."""
        
        processed_events = []
        source_stats = self.stats['source_stats'][source_id]
        
        for event in events:
            try:
                # Validate event
                is_valid, failure_reason = self.validator.validate_event(event)
                
                if is_valid:
                    self.stats['total_validated'] += 1
                    source_stats['validated'] += 1
                    
                    # Process event if processor is configured
                    if self.event_processor:
                        try:
                            await self.event_processor(event)
                            self.stats['total_processed'] += 1
                            source_stats['processed'] += 1
                            processed_events.append(event)
                        except Exception as e:
                            logger.error(f"Event processing failed for {event.event_id}: {e}")
                            self._record_source_error(source_id, f"processing_error: {e}")
                    else:
                        processed_events.append(event)
                else:
                    logger.debug(f"Event validation failed for {event.event_id}: {failure_reason}")
                    
            except Exception as e:
                logger.error(f"Error processing event from {source_id}: {e}")
                self._record_source_error(source_id, f"event_error: {e}")
        
        if processed_events:
            logger.info(f"Processed {len(processed_events)}/{len(events)} events from {source_id}")
        
        return processed_events
    
    async def fetch_from_all_sources(self, 
                                   max_concurrent: Optional[int] = None) -> Dict[str, List[RawEvent]]:
        """Fetch events from all enabled sources concurrently.
        
        Args:
            max_concurrent: Maximum concurrent fetches (defaults to configured limit)
            
        Returns:
            Dictionary mapping source_id to list of events
        """
        connectors = self.registry.get_enabled_connectors()
        if not connectors:
            logger.warning("No enabled connectors found")
            return {}
        
        max_concurrent = max_concurrent or self.max_concurrent_sources
        
        # Create semaphore to limit concurrent fetches
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(source_id: str) -> tuple[str, List[RawEvent]]:
            async with semaphore:
                events = await self.fetch_from_source(source_id)
                return source_id, events
        
        # Execute fetches concurrently
        tasks = [
            fetch_with_semaphore(connector.source_id) 
            for connector in connectors
        ]
        
        results = {}
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(completed_tasks):
            connector = connectors[i]
            if isinstance(result, Exception):
                logger.error(f"Fetch failed for {connector.source_id}: {result}")
                results[connector.source_id] = []
                self._record_source_error(connector.source_id, str(result))
            else:
                source_id, events = result
                results[source_id] = events
        
        self.stats['last_run'] = datetime.now(timezone.utc).isoformat()
        
        total_events = sum(len(events) for events in results.values())
        logger.info(f"Fetched {total_events} total events from {len(results)} sources")
        
        return results
    
    def _record_source_error(self, source_id: str, error: str):
        """Record an error for a specific source."""
        self.stats['errors'] += 1
        
        if source_id not in self.stats['source_stats']:
            self.stats['source_stats'][source_id] = {
                'fetches': 0, 'events': 0, 'validated': 0, 'processed': 0, 'errors': 0, 'last_fetch': None
            }
        
        self.stats['source_stats'][source_id]['errors'] += 1
    
    async def health_check_sources(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all registered sources."""
        return await self.registry.health_check_all_sources()
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        stats = self.stats.copy()
        
        # Add validator stats
        stats['validator_stats'] = self.validator.get_stats()
        
        # Add registry stats
        stats['registry_stats'] = self.registry.get_registry_stats()
        
        # Calculate rates
        if stats['total_fetches'] > 0:
            stats['avg_events_per_fetch'] = stats['total_events'] / stats['total_fetches']
            stats['validation_rate'] = stats['total_validated'] / stats['total_events'] if stats['total_events'] > 0 else 0
            stats['processing_rate'] = stats['total_processed'] / stats['total_validated'] if stats['total_validated'] > 0 else 0
        
        return stats
    
    def reset_stats(self):
        """Reset ingestion statistics."""
        self.stats = {
            'total_fetches': 0,
            'total_events': 0,
            'total_validated': 0,
            'total_processed': 0,
            'errors': 0,
            'last_run': None,
            'source_stats': {}
        }
        self.validator.reset_stats()
        logger.info("Reset ingestion statistics")
    
    def set_event_processor(self, processor: Callable):
        """Set the event processor function.
        
        Args:
            processor: Async function that takes a RawEvent and processes it
        """
        self.event_processor = processor
        logger.info("Set event processor function")
    
    def configure_source_intervals(self, intervals: Dict[str, int]):
        """Configure fetch intervals for specific sources.
        
        Args:
            intervals: Dictionary mapping source_id to interval in seconds
        """
        for source_id, interval in intervals.items():
            if source_id in self.fetch_intervals:
                self.fetch_intervals[source_id] = interval
                logger.info(f"Updated fetch interval for {source_id}: {interval}s")
    
    async def manual_fetch_all(self) -> Dict[str, List[RawEvent]]:
        """Manually trigger fetch from all sources (one-time operation)."""
        logger.info("Manual fetch triggered for all sources")
        return await self.fetch_from_all_sources()
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all sources including last fetch times and intervals."""
        status = {}
        
        for connector in self.registry.get_all_connectors().values():
            source_id = connector.source_id
            
            status[source_id] = {
                'enabled': connector.enabled,
                'source_type': connector.source_type,
                'last_fetch': self.last_fetch_times.get(source_id),
                'fetch_interval': self.fetch_intervals.get(source_id),
                'running': source_id in self.fetch_tasks and not self.fetch_tasks[source_id].done(),
                'stats': self.stats['source_stats'].get(source_id, {})
            }
        
        return status
    
    async def export_events_batch(self, 
                                events: List[RawEvent], 
                                format: str = 'json') -> str:
        """Export a batch of events to specified format.
        
        Args:
            events: List of events to export
            format: Export format ('json', 'csv', 'jsonl')
            
        Returns:
            Exported data as string
        """
        if format == 'json':
            return json.dumps([asdict(event) for event in events], indent=2, default=str)
        elif format == 'jsonl':
            return '\n'.join(json.dumps(asdict(event), default=str) for event in events)
        elif format == 'csv':
            # Basic CSV export (would need pandas for full implementation)
            import csv
            import io
            
            output = io.StringIO()
            if events:
                fieldnames = asdict(events[0]).keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for event in events:
                    writer.writerow(asdict(event))
            
            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Utility functions
async def create_coordinator_with_sources(sources_config: Dict[str, Dict[str, Any]]) -> IngestionCoordinator:
    """Create ingestion coordinator with sources from configuration.
    
    Args:
        sources_config: Dictionary mapping source_id to configuration
        
    Returns:
        Configured IngestionCoordinator instance
    """
    registry = DataSourceRegistry()
    registry.register_sources_from_config(sources_config)
    
    validator = DataValidator()
    coordinator = IngestionCoordinator(registry, validator)
    
    return coordinator