"""
Database abstraction layer supporting both SQLite (local) and BigQuery (cloud).
Provides unified interface for CRUD operations across deployment modes.
"""

import sqlite3
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from contextlib import contextmanager
from pathlib import Path

from config import config
from models import ProcessedEvent, SatelliteResult, Claim, INDIAN_STATES

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseInterface(ABC):
    """Abstract interface for database operations"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize database connection and schema"""
        pass
    
    @abstractmethod
    async def insert_event(self, event: ProcessedEvent) -> bool:
        """Insert a processed event into the database"""
        pass
    
    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[ProcessedEvent]:
        """Retrieve a specific event by ID"""
        pass
    
    @abstractmethod
    async def get_events_by_region(self, region: str, limit: int = 100) -> List[ProcessedEvent]:
        """Get events for a specific Indian state/region"""
        pass
    
    @abstractmethod
    async def get_events_by_timerange(self, start_time: datetime, end_time: datetime) -> List[ProcessedEvent]:
        """Get events within a specific time range"""
        pass
    
    @abstractmethod
    async def get_heatmap_data(self, hours_back: int = 24) -> Dict[str, Dict[str, Any]]:
        """Get aggregated data for heatmap visualization"""
        pass
    
    @abstractmethod
    async def delete_old_events(self, days_old: int = 30) -> int:
        """Delete events older than specified days"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass


class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation for local development mode"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing SQLite database at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    async def initialize(self) -> bool:
        """Initialize SQLite database with schema"""
        try:
            with self.get_connection() as conn:
                # Create events table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        original_text TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        lang TEXT,
                        region_hint TEXT,
                        lat REAL,
                        lon REAL,
                        entities TEXT,  -- JSON array
                        virality_score REAL,
                        satellite_data TEXT,  -- JSON object
                        claims_data TEXT,  -- JSON array
                        processing_metadata TEXT,  -- JSON object
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_region ON events(region_hint)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at)")
                
                # Create aggregation table for faster heatmap queries
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS region_stats (
                        region TEXT PRIMARY KEY,
                        event_count INTEGER DEFAULT 0,
                        avg_virality_score REAL DEFAULT 0.0,
                        avg_reality_score REAL DEFAULT 0.0,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                logger.info("SQLite database initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")
            return False
    
    async def insert_event(self, event: ProcessedEvent) -> bool:
        """Insert a processed event into SQLite"""
        try:
            with self.get_connection() as conn:
                # Serialize complex fields to JSON
                entities_json = json.dumps(event.entities)
                satellite_json = json.dumps(event.satellite.to_dict() if event.satellite else {})
                claims_json = json.dumps([claim.to_dict() for claim in event.claims])
                metadata_json = json.dumps(event.processing_metadata)
                
                conn.execute("""
                    INSERT OR REPLACE INTO events (
                        event_id, source, original_text, timestamp, lang, region_hint,
                        lat, lon, entities, virality_score, satellite_data, claims_data,
                        processing_metadata, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.source.value, event.original_text,
                    event.timestamp.isoformat(), event.lang.value, event.region_hint,
                    event.lat, event.lon, entities_json, event.virality_score,
                    satellite_json, claims_json, metadata_json, event.created_at.isoformat()
                ))
                
                # Update region statistics
                await self._update_region_stats(conn, event)
                
                conn.commit()
                logger.debug(f"Inserted event {event.event_id} into SQLite")
                return True
                
        except Exception as e:
            logger.error(f"Failed to insert event into SQLite: {e}")
            return False
    
    async def _update_region_stats(self, conn, event: ProcessedEvent):
        """Update aggregated region statistics"""
        if not event.region_hint:
            return
        
        reality_score = event.get_reality_score()
        
        # Get current stats
        cursor = conn.execute(
            "SELECT event_count, avg_virality_score, avg_reality_score FROM region_stats WHERE region = ?",
            (event.region_hint,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing stats
            count = row[0] + 1
            new_virality = ((row[1] * row[0]) + event.virality_score) / count
            new_reality = ((row[2] * row[0]) + reality_score) / count
            
            conn.execute("""
                UPDATE region_stats 
                SET event_count = ?, avg_virality_score = ?, avg_reality_score = ?, last_updated = ?
                WHERE region = ?
            """, (count, new_virality, new_reality, datetime.utcnow().isoformat(), event.region_hint))
        else:
            # Insert new stats
            conn.execute("""
                INSERT INTO region_stats (region, event_count, avg_virality_score, avg_reality_score, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (event.region_hint, 1, event.virality_score, reality_score, datetime.utcnow().isoformat()))
    
    async def get_event(self, event_id: str) -> Optional[ProcessedEvent]:
        """Retrieve a specific event by ID from SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_event(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get event from SQLite: {e}")
            return None
    
    async def get_events_by_region(self, region: str, limit: int = 100) -> List[ProcessedEvent]:
        """Get events for a specific region from SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE region_hint = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (region, limit))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    if event:
                        events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get events by region from SQLite: {e}")
            return []
    
    async def get_events_by_timerange(self, start_time: datetime, end_time: datetime) -> List[ProcessedEvent]:
        """Get events within a time range from SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE timestamp BETWEEN ? AND ? 
                    ORDER BY timestamp DESC
                """, (start_time.isoformat(), end_time.isoformat()))
                
                events = []
                for row in cursor.fetchall():
                    event = self._row_to_event(row)
                    if event:
                        events.append(event)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to get events by timerange from SQLite: {e}")
            return []
    
    async def get_heatmap_data(self, hours_back: int = 24) -> Dict[str, Dict[str, Any]]:
        """Get aggregated heatmap data from SQLite"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        region_hint,
                        COUNT(*) as event_count,
                        AVG(virality_score) as avg_virality,
                        AVG(CASE 
                            WHEN satellite_data != '{}' AND satellite_data != '' 
                            THEN JSON_EXTRACT(satellite_data, '$.reality_score')
                            ELSE 0.5 
                        END) as avg_reality
                    FROM events 
                    WHERE timestamp >= ? AND region_hint IS NOT NULL AND region_hint != ''
                    GROUP BY region_hint
                """, (cutoff_time.isoformat(),))
                
                heatmap_data = {}
                for row in cursor.fetchall():
                    region = row[0]
                    if region and region.lower() in INDIAN_STATES:
                        heatmap_data[region] = {
                            "intensity": min(1.0, row[1] / 10.0),  # Normalize to 0-1
                            "event_count": row[1],
                            "avg_virality_score": round(row[2] or 0.0, 3),
                            "avg_reality_score": round(row[3] or 0.5, 3),
                            "misinformation_risk": round((row[2] or 0.0) * (1.0 - (row[3] or 0.5)), 3)
                        }
                
                return heatmap_data
                
        except Exception as e:
            logger.error(f"Failed to get heatmap data from SQLite: {e}")
            return {}
    
    async def delete_old_events(self, days_old: int = 30) -> int:
        """Delete old events from SQLite"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM events WHERE created_at < ?",
                    (cutoff_date.isoformat(),)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} old events from SQLite")
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to delete old events from SQLite: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics from SQLite"""
        try:
            with self.get_connection() as conn:
                # Total events
                cursor = conn.execute("SELECT COUNT(*) FROM events")
                total_events = cursor.fetchone()[0]
                
                # Events by source
                cursor = conn.execute("SELECT source, COUNT(*) FROM events GROUP BY source")
                events_by_source = dict(cursor.fetchall())
                
                # Recent events (last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM events WHERE timestamp >= ?",
                    (cutoff_time.isoformat(),)
                )
                recent_events = cursor.fetchone()[0]
                
                # Database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    "total_events": total_events,
                    "events_by_source": events_by_source,
                    "recent_events_24h": recent_events,
                    "database_size_bytes": db_size,
                    "database_type": "sqlite"
                }
                
        except Exception as e:
            logger.error(f"Failed to get stats from SQLite: {e}")
            return {}
    
    def _row_to_event(self, row) -> Optional[ProcessedEvent]:
        """Convert SQLite row to ProcessedEvent object"""
        try:
            # Parse JSON fields
            entities = json.loads(row["entities"]) if row["entities"] else []
            satellite_data = json.loads(row["satellite_data"]) if row["satellite_data"] else {}
            claims_data = json.loads(row["claims_data"]) if row["claims_data"] else []
            metadata = json.loads(row["processing_metadata"]) if row["processing_metadata"] else {}
            
            # Create satellite result
            satellite = SatelliteResult.from_dict(satellite_data) if satellite_data else None
            
            # Create claims
            claims = [Claim.from_dict(claim_data) for claim_data in claims_data]
            
            # Parse timestamps
            timestamp = datetime.fromisoformat(row["timestamp"])
            created_at = datetime.fromisoformat(row["created_at"])
            
            return ProcessedEvent(
                event_id=row["event_id"],
                source=row["source"],
                original_text=row["original_text"],
                timestamp=timestamp,
                lang=row["lang"],
                region_hint=row["region_hint"],
                lat=row["lat"] or 0.0,
                lon=row["lon"] or 0.0,
                entities=entities,
                virality_score=row["virality_score"] or 0.0,
                satellite=satellite,
                claims=claims,
                processing_metadata=metadata,
                created_at=created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to convert row to event: {e}")
            return None


class DatabaseManager:
    """Factory class for creating proper database implementation"""
    
    @staticmethod
    def create_database() -> DatabaseInterface:
        """Create database instance strictly for SQLite (cost-free)"""
        db_config = config.get_database_config()
        
        # Extract path from SQLite URL
        db_path = db_config.url.replace("sqlite:///", "")
        return SQLiteDatabase(db_path)


# Global database instance
database = DatabaseManager.create_database()