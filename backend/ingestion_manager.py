"""
Unified ingestion manager that coordinates local and cloud data sources.
Provides a single interface for event ingestion, processing, and routing
with automatic fallback and error handling capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass
from enum import Enum
import json

# Local imports
from config import config
from models import EventSource, ProcessedEvent
from processor import RawEvent, event_processor
from database import database
from satellite_client import satellite_validator

# Import ingestion modules
from ingest_local import local_ingestion_manager
from watson_client import cloud_ingestion_manager

# Configure logging
logger = logging.getLogger(__name__)


class IngestionMode(Enum):
    """Ingestion operation modes"""
    LOCAL_ONLY = "local_only"
    CLOUD_ONLY = "cloud_only"
    HYBRID = "hybrid"
    AUTO = "auto"


@dataclass
class IngestionStats:
    """Statistics for ingestion operations"""
    total_events_ingested: int = 0
    events_processed: int = 0
    events_stored: int = 0
    processing_errors: int = 0
    ingestion_errors: int = 0
    average_processing_time_ms: float = 0.0
    last_ingestion_time: Optional[datetime] = None
    sources_active: List[str] = None
    
    def __post_init__(self):
        if self.sources_active is None:
            self.sources_active = []


class UnifiedIngestionManager:
    """
    Main ingestion manager that coordinates all data sources and processing.
    Handles both local and cloud modes with automatic fallback capabilities.
    """
    
    def __init__(self):
        self.config = config
        self.mode = IngestionMode.AUTO
        self.initialized = False
        self.stats = IngestionStats()
        
        # Processing components
        self.event_processor = event_processor
        self.satellite_validator = satellite_validator
        self.database = database
        
        # Ingestion managers
        self.local_manager = local_ingestion_manager
        self.cloud_manager = cloud_ingestion_manager
        
        # Processing queue and workers
        self.processing_queue = asyncio.Queue()
        self.worker_tasks = []
        self.running = False
        
        # Event deduplication
        self.processed_event_ids = set()
        self.dedup_window_hours = 24
        
    async def initialize(self) -> bool:
        """Initialize the unified ingestion manager"""
        try:
            logger.info("Initializing unified ingestion manager...")
            
            # Initialize core components
            processor_success = await self.event_processor.initialize()
            satellite_success = await self.satellite_validator.initialize()
            database_success = await self.database.initialize()
            
            if not all([processor_success, satellite_success, database_success]):
                logger.error("Failed to initialize core components")
                return False
            
            # Initialize ingestion managers based on mode
            if self.config.is_cloud_mode():
                cloud_success = await self.cloud_manager.initialize()
                if cloud_success:
                    self.mode = IngestionMode.CLOUD_ONLY
                    logger.info("Initialized in cloud mode")
                else:
                    logger.warning("Cloud initialization failed, falling back to local mode")
                    self.mode = IngestionMode.LOCAL_ONLY
            else:
                self.mode = IngestionMode.LOCAL_ONLY
                logger.info("Initialized in local mode")
            
            # Start processing workers
            await self._start_processing_workers()
            
            self.initialized = True
            logger.info(f"Unified ingestion manager initialized in {self.mode.value} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize unified ingestion manager: {e}")
            return False
    
    async def start_continuous_ingestion(self, interval_seconds: int = 300):
        """
        Start continuous ingestion from all available sources.
        
        Args:
            interval_seconds: Interval between ingestion cycles (default: 5 minutes)
        """
        if not self.initialized:
            logger.error("Ingestion manager not initialized")
            return
        
        self.running = True
        logger.info(f"Starting continuous ingestion (interval: {interval_seconds}s)")
        
        try:
            while self.running:
                try:
                    # Perform ingestion cycle
                    await self._ingestion_cycle()
                    
                    # Wait for next cycle
                    await asyncio.sleep(interval_seconds)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in ingestion cycle: {e}")
                    self.stats.ingestion_errors += 1
                    
                    # Wait before retrying
                    await asyncio.sleep(min(interval_seconds, 60))
        
        finally:
            self.running = False
            logger.info("Continuous ingestion stopped")
    
    async def stop_continuous_ingestion(self):
        """Stop continuous ingestion"""
        self.running = False
        
        # Stop processing workers
        await self._stop_processing_workers()
        
        logger.info("Ingestion manager stopped")
    
    async def ingest_batch(self, max_events: int = 100, 
                          sources: Optional[List[str]] = None) -> List[ProcessedEvent]:
        """
        Perform a single batch ingestion from specified sources.
        
        Args:
            max_events: Maximum number of events to ingest
            sources: List of source types to ingest from (None = all sources)
            
        Returns:
            List of processed events
        """
        if not self.initialized:
            logger.error("Ingestion manager not initialized")
            return []
        
        try:
            # Ingest raw events
            raw_events = await self._ingest_raw_events(max_events, sources)
            
            if not raw_events:
                logger.info("No new events to process")
                return []
            
            # Process events
            processed_events = await self._process_events_batch(raw_events)
            
            # Update statistics
            self.stats.total_events_ingested += len(raw_events)
            self.stats.events_processed += len(processed_events)
            self.stats.last_ingestion_time = datetime.utcnow()
            
            logger.info(f"Batch ingestion completed: {len(raw_events)} ingested, {len(processed_events)} processed")
            return processed_events
            
        except Exception as e:
            logger.error(f"Batch ingestion failed: {e}")
            self.stats.ingestion_errors += 1
            return []
    
    async def ingest_single_event(self, source_type: str, **kwargs) -> Optional[ProcessedEvent]:
        """
        Ingest and process a single event from a specific source.
        
        Args:
            source_type: Type of source (rss, social, file, test, custom)
            **kwargs: Source-specific parameters
            
        Returns:
            Processed event or None if failed
        """
        if not self.initialized:
            logger.error("Ingestion manager not initialized")
            return None
        
        try:
            # Ingest single raw event
            if self.mode in [IngestionMode.LOCAL_ONLY, IngestionMode.HYBRID]:
                raw_events = await self.local_manager.ingest_from_source(source_type, **kwargs)
            else:
                # For cloud mode, enhance with Watson if available
                raw_events = await self.local_manager.ingest_from_source(source_type, **kwargs)
                if raw_events:
                    raw_events = await self.cloud_manager.ingest_and_enhance_content(raw_events)
            
            if not raw_events:
                return None
            
            # Process the first event
            raw_event = raw_events[0]
            processed_event = await self._process_single_event(raw_event)
            
            if processed_event:
                self.stats.total_events_ingested += 1
                self.stats.events_processed += 1
                logger.info(f"Single event processed: {processed_event.event_id}")
            
            return processed_event
            
        except Exception as e:
            logger.error(f"Single event ingestion failed: {e}")
            self.stats.ingestion_errors += 1
            return None
    
    async def _ingestion_cycle(self):
        """Perform a single ingestion cycle"""
        try:
            # Determine batch size based on mode
            if self.mode == IngestionMode.CLOUD_ONLY:
                batch_size = 50  # Smaller batches for cloud processing
            else:
                batch_size = 100
            
            # Ingest raw events
            raw_events = await self._ingest_raw_events(batch_size)
            
            if not raw_events:
                logger.debug("No new events in this cycle")
                return
            
            # Add events to processing queue
            for event in raw_events:
                await self.processing_queue.put(event)
            
            self.stats.total_events_ingested += len(raw_events)
            logger.info(f"Ingestion cycle: {len(raw_events)} events queued for processing")
            
        except Exception as e:
            logger.error(f"Ingestion cycle failed: {e}")
            raise
    
    async def _ingest_raw_events(self, max_events: int, 
                                sources: Optional[List[str]] = None) -> List[RawEvent]:
        """Ingest raw events from available sources"""
        raw_events = []
        
        try:
            if self.mode in [IngestionMode.LOCAL_ONLY, IngestionMode.HYBRID]:
                # Use local ingestion
                if sources:
                    # Ingest from specific sources
                    for source in sources:
                        try:
                            events = await self.local_manager.ingest_from_source(
                                source, max_articles=max_events // len(sources)
                            )
                            raw_events.extend(events)
                        except Exception as e:
                            logger.warning(f"Failed to ingest from source {source}: {e}")
                else:
                    # Ingest from all sources
                    events = await self.local_manager.ingest_all_sources(max_events)
                    raw_events.extend(events)
            
            if self.mode in [IngestionMode.CLOUD_ONLY, IngestionMode.HYBRID]:
                # Enhance with cloud services
                if raw_events:
                    try:
                        enhanced_events = await self.cloud_manager.ingest_and_enhance_content(raw_events)
                        raw_events = enhanced_events
                    except Exception as e:
                        logger.warning(f"Cloud enhancement failed: {e}")
                        # Continue with unenhanced events
            
            # Remove duplicates
            raw_events = self._deduplicate_events(raw_events)
            
            return raw_events[:max_events]
            
        except Exception as e:
            logger.error(f"Raw event ingestion failed: {e}")
            return []
    
    async def _process_events_batch(self, raw_events: List[RawEvent]) -> List[ProcessedEvent]:
        """Process a batch of raw events"""
        processed_events = []
        
        for raw_event in raw_events:
            try:
                processed_event = await self._process_single_event(raw_event)
                if processed_event:
                    processed_events.append(processed_event)
            except Exception as e:
                logger.error(f"Failed to process event: {e}")
                self.stats.processing_errors += 1
        
        return processed_events
    
    async def _process_single_event(self, raw_event: RawEvent) -> Optional[ProcessedEvent]:
        """Process a single raw event through the complete pipeline"""
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Process through NLP pipeline
            processed_event = await self.event_processor.process_event(raw_event)
            if not processed_event:
                logger.warning("Event processing failed")
                return None
            
            # Step 2: Satellite validation (if coordinates available)
            if processed_event.lat != 0.0 and processed_event.lon != 0.0:
                try:
                    primary_claim = processed_event.get_primary_claim()
                    claim_text = primary_claim.text if primary_claim else processed_event.original_text
                    
                    satellite_result = await self.satellite_validator.validate_claim(
                        processed_event.lat,
                        processed_event.lon,
                        processed_event.timestamp.strftime('%Y-%m-%d'),
                        claim_text
                    )
                    
                    processed_event.satellite = satellite_result
                    
                except Exception as e:
                    logger.warning(f"Satellite validation failed: {e}")
                    # Continue without satellite validation
            
            # Step 3: Store in database
            try:
                success = await self.database.insert_event(processed_event)
                if success:
                    self.stats.events_stored += 1
                else:
                    logger.warning(f"Failed to store event {processed_event.event_id}")
            except Exception as e:
                logger.error(f"Database storage failed: {e}")
                # Continue even if storage fails
            
            # Update processing time statistics
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._update_processing_time_stats(processing_time)
            
            return processed_event
            
        except Exception as e:
            logger.error(f"Event processing pipeline failed: {e}")
            self.stats.processing_errors += 1
            return None
    
    def _deduplicate_events(self, raw_events: List[RawEvent]) -> List[RawEvent]:
        """Remove duplicate events based on content similarity"""
        unique_events = []
        
        for event in raw_events:
            # Create a simple hash of the event content
            event_hash = hash(f"{event.source.value}_{event.original_text[:100]}_{event.timestamp.date()}")
            
            if event_hash not in self.processed_event_ids:
                unique_events.append(event)
                self.processed_event_ids.add(event_hash)
        
        # Clean up old hashes (keep only last 24 hours)
        if len(self.processed_event_ids) > 10000:  # Arbitrary limit
            self.processed_event_ids.clear()
            logger.debug("Cleared event deduplication cache")
        
        return unique_events
    
    def _update_processing_time_stats(self, processing_time_ms: float):
        """Update average processing time statistics"""
        if self.stats.events_processed == 0:
            self.stats.average_processing_time_ms = processing_time_ms
        else:
            # Calculate running average
            total_time = self.stats.average_processing_time_ms * (self.stats.events_processed - 1)
            self.stats.average_processing_time_ms = (total_time + processing_time_ms) / self.stats.events_processed
    
    async def _start_processing_workers(self, num_workers: int = 3):
        """Start background workers for event processing"""
        self.worker_tasks = []
        
        for i in range(num_workers):
            task = asyncio.create_task(self._processing_worker(f"worker-{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"Started {num_workers} processing workers")
    
    async def _stop_processing_workers(self):
        """Stop background processing workers"""
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        self.worker_tasks = []
        logger.info("Stopped processing workers")
    
    async def _processing_worker(self, worker_name: str):
        """Background worker for processing events from the queue"""
        logger.debug(f"Processing worker {worker_name} started")
        
        try:
            while self.running:
                try:
                    # Get event from queue with timeout
                    raw_event = await asyncio.wait_for(
                        self.processing_queue.get(), 
                        timeout=5.0
                    )
                    
                    # Process the event
                    processed_event = await self._process_single_event(raw_event)
                    
                    if processed_event:
                        self.stats.events_processed += 1
                        logger.debug(f"Worker {worker_name} processed event {processed_event.event_id}")
                    
                    # Mark task as done
                    self.processing_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No events in queue, continue
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_name} error: {e}")
                    self.stats.processing_errors += 1
        
        finally:
            logger.debug(f"Processing worker {worker_name} stopped")
    
    def get_stats(self) -> IngestionStats:
        """Get current ingestion statistics"""
        # Update active sources
        active_sources = []
        if self.mode in [IngestionMode.LOCAL_ONLY, IngestionMode.HYBRID]:
            active_sources.extend(["rss", "social", "manual"])
        if self.mode in [IngestionMode.CLOUD_ONLY, IngestionMode.HYBRID]:
            active_sources.extend(["watson", "pubsub"])
        
        self.stats.sources_active = active_sources
        return self.stats
    
    def reset_stats(self):
        """Reset ingestion statistics"""
        self.stats = IngestionStats()
        logger.info("Ingestion statistics reset")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components"""
        health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "mode": self.mode.value,
            "initialized": self.initialized,
            "components": {}
        }
        
        try:
            # Check core components
            health["components"]["event_processor"] = "healthy" if self.event_processor.initialized else "unhealthy"
            health["components"]["satellite_validator"] = "healthy" if self.satellite_validator.initialized else "unhealthy"
            health["components"]["database"] = "healthy"  # Assume healthy if no exception
            
            # Check ingestion managers
            if self.mode in [IngestionMode.LOCAL_ONLY, IngestionMode.HYBRID]:
                health["components"]["local_ingestion"] = "healthy"
            
            if self.mode in [IngestionMode.CLOUD_ONLY, IngestionMode.HYBRID]:
                health["components"]["cloud_ingestion"] = "healthy" if self.cloud_manager.initialized else "degraded"
            
            # Check processing queue
            queue_size = self.processing_queue.qsize()
            health["components"]["processing_queue"] = f"healthy (size: {queue_size})"
            
            # Check worker status
            active_workers = sum(1 for task in self.worker_tasks if not task.done())
            health["components"]["processing_workers"] = f"healthy ({active_workers}/{len(self.worker_tasks)} active)"
            
            # Overall status
            unhealthy_components = [k for k, v in health["components"].items() if "unhealthy" in v]
            if unhealthy_components:
                health["status"] = "degraded"
                health["issues"] = unhealthy_components
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health


# Global unified ingestion manager
unified_ingestion_manager = UnifiedIngestionManager()