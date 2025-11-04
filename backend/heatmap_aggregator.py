"""
Heatmap data aggregation logic for generating state-wise misinformation intensity maps.
Processes event data to create visualization-ready aggregations with caching and
real-time updates for the interactive frontend heatmap.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json
from pathlib import Path

# Local imports
from config import config
from models import ProcessedEvent, ClaimCategory, INDIAN_STATES
from database import database

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class StateHeatmapData:
    """Heatmap data for a single state"""
    state_name: str
    event_count: int
    intensity: float  # 0.0 - 1.0
    avg_virality_score: float
    avg_reality_score: float
    misinformation_risk: float
    dominant_category: Optional[str]
    recent_claims: List[str]
    satellite_validated_count: int
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "event_count": self.event_count,
            "intensity": round(self.intensity, 3),
            "avg_virality_score": round(self.avg_virality_score, 3),
            "avg_reality_score": round(self.avg_reality_score, 3),
            "misinformation_risk": round(self.misinformation_risk, 3),
            "dominant_category": self.dominant_category,
            "recent_claims": self.recent_claims[:3],  # Limit to top 3
            "satellite_validated_count": self.satellite_validated_count,
            "last_updated": self.last_updated.isoformat()
        }


class HeatmapAggregator:
    """
    Aggregates event data into heatmap visualization format.
    Provides state-wise intensity calculations, caching, and real-time updates.
    """
    
    def __init__(self):
        self.cache_dir = Path(config.data_dir) / "heatmap_cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration_minutes = 5  # Cache for 5 minutes
        
        # Intensity calculation parameters
        self.intensity_params = {
            "max_events_for_full_intensity": 50,  # Events needed for intensity = 1.0
            "virality_weight": 0.4,
            "reality_weight": 0.3,
            "volume_weight": 0.3
        }
    
    async def generate_heatmap_data(self, hours_back: int = 24, 
                                  use_cache: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Generate complete heatmap data for all Indian states.
        
        Args:
            hours_back: Hours of historical data to include
            use_cache: Whether to use cached data if available
            
        Returns:
            Dictionary mapping state names to heatmap data
        """
        try:
            # Check cache first
            if use_cache:
                cached_data = self._get_cached_heatmap(hours_back)
                if cached_data:
                    logger.debug("Using cached heatmap data")
                    return cached_data
            
            logger.info(f"Generating heatmap data for last {hours_back} hours")
            
            # Get events from database
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours_back)
            
            events = await database.get_events_by_timerange(start_time, end_time)
            
            # Group events by state
            state_events = self._group_events_by_state(events)
            
            # Generate heatmap data for each state
            heatmap_data = {}
            
            for state_name in INDIAN_STATES.keys():
                state_events_list = state_events.get(state_name, [])
                state_data = self._calculate_state_heatmap_data(
                    state_name, state_events_list, hours_back
                )
                
                if state_data.event_count > 0 or state_name in ["maharashtra", "delhi", "karnataka"]:
                    # Include major states even if no events (for visualization)
                    heatmap_data[state_name.title()] = state_data.to_dict()
            
            # Cache the results
            if use_cache:
                self._cache_heatmap_data(heatmap_data, hours_back)
            
            logger.info(f"Generated heatmap data for {len(heatmap_data)} states")
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Failed to generate heatmap data: {e}")
            return {}
    
    def _group_events_by_state(self, events: List[ProcessedEvent]) -> Dict[str, List[ProcessedEvent]]:
        """Group events by Indian state"""
        state_events = defaultdict(list)
        
        for event in events:
            if event.region_hint:
                # Normalize state name
                state_name = event.region_hint.lower().strip()
                
                # Map to standard state names
                if state_name in INDIAN_STATES:
                    state_events[state_name].append(event)
                else:
                    # Try to find partial matches
                    for standard_state in INDIAN_STATES.keys():
                        if (state_name in standard_state or 
                            standard_state in state_name or
                            any(word in standard_state for word in state_name.split())):
                            state_events[standard_state].append(event)
                            break
        
        return dict(state_events)
    
    def _calculate_state_heatmap_data(self, state_name: str, 
                                    events: List[ProcessedEvent],
                                    hours_back: int) -> StateHeatmapData:
        """Calculate heatmap data for a single state"""
        
        if not events:
            return StateHeatmapData(
                state_name=state_name,
                event_count=0,
                intensity=0.0,
                avg_virality_score=0.0,
                avg_reality_score=0.5,  # Neutral
                misinformation_risk=0.0,
                dominant_category=None,
                recent_claims=[],
                satellite_validated_count=0,
                last_updated=datetime.utcnow()
            )
        
        # Calculate basic statistics
        event_count = len(events)
        
        # Virality scores
        virality_scores = [event.virality_score for event in events]
        avg_virality = sum(virality_scores) / len(virality_scores)
        
        # Reality scores
        reality_scores = [event.get_reality_score() for event in events]
        avg_reality = sum(reality_scores) / len(reality_scores)
        
        # Calculate intensity (0.0 - 1.0)
        intensity = self._calculate_intensity(events, avg_virality, avg_reality)
        
        # Misinformation risk (high virality + low reality = high risk)
        misinformation_risk = avg_virality * (1.0 - avg_reality)
        
        # Find dominant category
        dominant_category = self._find_dominant_category(events)
        
        # Extract recent claims
        recent_claims = self._extract_recent_claims(events)
        
        # Count satellite validated events
        satellite_validated_count = sum(
            1 for event in events 
            if event.satellite and event.satellite.confidence > 0.5
        )
        
        return StateHeatmapData(
            state_name=state_name,
            event_count=event_count,
            intensity=intensity,
            avg_virality_score=avg_virality,
            avg_reality_score=avg_reality,
            misinformation_risk=misinformation_risk,
            dominant_category=dominant_category,
            recent_claims=recent_claims,
            satellite_validated_count=satellite_validated_count,
            last_updated=datetime.utcnow()
        )
    
    def _calculate_intensity(self, events: List[ProcessedEvent], 
                           avg_virality: float, avg_reality: float) -> float:
        """
        Calculate heatmap intensity based on multiple factors.
        Higher intensity indicates more misinformation activity.
        """
        # Volume component (normalized by max events)
        volume_component = min(1.0, len(events) / self.intensity_params["max_events_for_full_intensity"])
        
        # Virality component (higher virality = higher intensity)
        virality_component = avg_virality
        
        # Reality component (lower reality = higher intensity)
        reality_component = 1.0 - avg_reality
        
        # Weighted combination
        intensity = (
            volume_component * self.intensity_params["volume_weight"] +
            virality_component * self.intensity_params["virality_weight"] +
            reality_component * self.intensity_params["reality_weight"]
        )
        
        return min(1.0, max(0.0, intensity))
    
    def _find_dominant_category(self, events: List[ProcessedEvent]) -> Optional[str]:
        """Find the most common claim category in the events"""
        category_counts = defaultdict(int)
        
        for event in events:
            for claim in event.claims:
                category_counts[claim.category.value] += 1
        
        if not category_counts:
            return None
        
        # Return the most frequent category
        return max(category_counts.items(), key=lambda x: x[1])[0]
    
    def _extract_recent_claims(self, events: List[ProcessedEvent], limit: int = 5) -> List[str]:
        """Extract recent high-confidence claims"""
        claims_with_scores = []
        
        for event in events:
            for claim in event.claims:
                claims_with_scores.append((
                    claim.text,
                    claim.confidence,
                    event.timestamp
                ))
        
        # Sort by confidence and recency
        claims_with_scores.sort(key=lambda x: (x[1], x[2]), reverse=True)
        
        # Extract unique claim texts
        seen_claims = set()
        recent_claims = []
        
        for claim_text, confidence, timestamp in claims_with_scores:
            # Normalize claim text for deduplication
            normalized_claim = claim_text.lower().strip()
            
            if normalized_claim not in seen_claims and len(claim_text) > 20:
                seen_claims.add(normalized_claim)
                # Truncate long claims
                if len(claim_text) > 100:
                    claim_text = claim_text[:97] + "..."
                recent_claims.append(claim_text)
                
                if len(recent_claims) >= limit:
                    break
        
        return recent_claims
    
    def _get_cached_heatmap(self, hours_back: int) -> Optional[Dict[str, Dict[str, Any]]]:
        """Get cached heatmap data if available and fresh"""
        cache_file = self.cache_dir / f"heatmap_{hours_back}h.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cache is still fresh
            cache_time = datetime.fromisoformat(cached_data['cached_at'])
            if (datetime.utcnow() - cache_time).total_seconds() < self.cache_duration_minutes * 60:
                return cached_data['heatmap_data']
            
        except Exception as e:
            logger.warning(f"Failed to load cached heatmap data: {e}")
        
        return None
    
    def _cache_heatmap_data(self, heatmap_data: Dict[str, Dict[str, Any]], hours_back: int):
        """Cache heatmap data to disk"""
        cache_file = self.cache_dir / f"heatmap_{hours_back}h.json"
        
        try:
            cache_data = {
                "heatmap_data": heatmap_data,
                "cached_at": datetime.utcnow().isoformat(),
                "hours_back": hours_back
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(f"Cached heatmap data to {cache_file}")
            
        except Exception as e:
            logger.warning(f"Failed to cache heatmap data: {e}")
    
    async def get_state_trend_data(self, state_name: str, 
                                 days_back: int = 7) -> Dict[str, Any]:
        """
        Get trend data for a specific state over multiple days.
        Returns daily aggregations for trend visualization.
        """
        try:
            state_name_lower = state_name.lower()
            if state_name_lower not in INDIAN_STATES:
                raise ValueError(f"Invalid state name: {state_name}")
            
            # Get events for the specified period
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)
            
            events = await database.get_events_by_region(state_name, limit=1000)
            
            # Filter by time range
            filtered_events = [
                event for event in events 
                if start_time <= event.timestamp <= end_time
            ]
            
            # Group by day
            daily_data = defaultdict(list)
            for event in filtered_events:
                day_key = event.timestamp.date().isoformat()
                daily_data[day_key].append(event)
            
            # Calculate daily metrics
            trend_data = {}
            for day, day_events in daily_data.items():
                if day_events:
                    avg_virality = sum(e.virality_score for e in day_events) / len(day_events)
                    avg_reality = sum(e.get_reality_score() for e in day_events) / len(day_events)
                    
                    trend_data[day] = {
                        "event_count": len(day_events),
                        "avg_virality_score": round(avg_virality, 3),
                        "avg_reality_score": round(avg_reality, 3),
                        "misinformation_risk": round(avg_virality * (1 - avg_reality), 3)
                    }
            
            return {
                "state": state_name.title(),
                "period_days": days_back,
                "daily_trends": trend_data,
                "total_events": len(filtered_events)
            }
            
        except Exception as e:
            logger.error(f"Failed to get trend data for {state_name}: {e}")
            return {}
    
    def clear_cache(self):
        """Clear all cached heatmap data"""
        try:
            cache_files = list(self.cache_dir.glob("heatmap_*.json"))
            for cache_file in cache_files:
                cache_file.unlink()
            
            logger.info(f"Cleared {len(cache_files)} heatmap cache files")
            
        except Exception as e:
            logger.error(f"Failed to clear heatmap cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about heatmap cache"""
        try:
            cache_files = list(self.cache_dir.glob("heatmap_*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "cache_files": len(cache_files),
                "total_size_bytes": total_size,
                "cache_directory": str(self.cache_dir),
                "cache_duration_minutes": self.cache_duration_minutes
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


# Global heatmap aggregator instance
heatmap_aggregator = HeatmapAggregator()