"""
Satellite validation stub system for local development mode.
Provides realistic but deterministic satellite validation responses
without requiring Google Earth Engine credentials or internet access.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import numpy as np

from config import config
from models import SatelliteResult

logger = logging.getLogger(__name__)


class SatelliteStubManager:
    """
    Manages stub satellite validation responses for local development.
    Provides consistent, realistic responses based on location and date.
    """
    
    def __init__(self):
        self.cache_dir = Path(config.data_dir) / "satellite_stubs"
        self.cache_dir.mkdir(exist_ok=True)
        self.scenario_config = self._load_scenario_config()
        
    def _load_scenario_config(self) -> Dict[str, Any]:
        """Load predefined scenarios for different types of claims"""
        return {
            "disaster_scenarios": {
                # Flood scenarios - should show significant changes
                "flood": {
                    "similarity_range": (0.1, 0.3),
                    "reality_score_range": (0.6, 0.8),  # Floods are often real
                    "confidence_range": (0.7, 0.9),
                    "keywords": ["flood", "flooding", "water", "inundation", "deluge"]
                },
                # Earthquake scenarios - minimal satellite changes
                "earthquake": {
                    "similarity_range": (0.7, 0.9),
                    "reality_score_range": (0.5, 0.7),
                    "confidence_range": (0.6, 0.8),
                    "keywords": ["earthquake", "quake", "tremor", "seismic"]
                },
                # Fire scenarios - should show clear changes
                "fire": {
                    "similarity_range": (0.2, 0.4),
                    "reality_score_range": (0.6, 0.8),
                    "confidence_range": (0.8, 0.9),
                    "keywords": ["fire", "wildfire", "burning", "smoke", "blaze"]
                }
            },
            "development_scenarios": {
                # Construction/development - moderate changes
                "construction": {
                    "similarity_range": (0.4, 0.6),
                    "reality_score_range": (0.7, 0.9),
                    "confidence_range": (0.8, 0.9),
                    "keywords": ["construction", "building", "development", "infrastructure"]
                },
                # Deforestation - significant changes
                "deforestation": {
                    "similarity_range": (0.2, 0.4),
                    "reality_score_range": (0.3, 0.5),  # Often concerning/real
                    "confidence_range": (0.7, 0.9),
                    "keywords": ["deforestation", "logging", "clearing", "forest loss"]
                }
            },
            "normal_scenarios": {
                # Normal conditions - high similarity
                "normal": {
                    "similarity_range": (0.7, 0.9),
                    "reality_score_range": (0.8, 0.9),
                    "confidence_range": (0.7, 0.9),
                    "keywords": []
                }
            },
            "misinformation_scenarios": {
                # Fake claims - should show normal conditions (high similarity)
                "fake_disaster": {
                    "similarity_range": (0.8, 0.95),
                    "reality_score_range": (0.1, 0.3),  # Low reality for fake claims
                    "confidence_range": (0.7, 0.9),
                    "keywords": ["fake", "hoax", "false", "conspiracy"]
                }
            }
        }
    
    def generate_stub_result(self, lat: float, lon: float, date: str, 
                           claim_text: str = "") -> SatelliteResult:
        """
        Generate a realistic stub satellite validation result.
        
        Args:
            lat: Latitude
            lon: Longitude
            date: Date in ISO format
            claim_text: Text of the claim for context-aware responses
            
        Returns:
            SatelliteResult with realistic stub data
        """
        try:
            # Create deterministic seed from inputs
            seed_str = f"{lat:.4f}_{lon:.4f}_{date}_{claim_text[:50]}"
            seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
            np.random.seed(seed % (2**32))
            
            # Determine scenario based on claim text
            scenario = self._determine_scenario(claim_text)
            scenario_config = self._get_scenario_config(scenario)
            
            # Generate values within scenario ranges
            similarity = np.random.uniform(*scenario_config["similarity_range"])
            reality_score = np.random.uniform(*scenario_config["reality_score_range"])
            confidence = np.random.uniform(*scenario_config["confidence_range"])
            
            # Add some location-based variation
            location_factor = (abs(lat) + abs(lon)) / 100
            similarity += np.random.uniform(-0.05, 0.05) * location_factor
            reality_score += np.random.uniform(-0.03, 0.03) * location_factor
            
            # Ensure values are within valid ranges
            similarity = np.clip(similarity, 0.0, 1.0)
            reality_score = np.clip(reality_score, 0.0, 1.0)
            confidence = np.clip(confidence, 0.0, 1.0)
            
            # Determine anomaly based on similarity threshold
            anomaly = similarity < config.get_satellite_config().similarity_threshold
            
            # Generate realistic processing time
            processing_time = np.random.randint(100, 800)
            
            # Create baseline date (1-3 years ago)
            baseline_days_ago = np.random.randint(365, 365 * 3)
            baseline_date = (datetime.utcnow() - timedelta(days=baseline_days_ago)).strftime('%Y-%m-%d')
            
            # Generate metadata
            metadata = {
                "stub_mode": True,
                "scenario": scenario,
                "seed": seed,
                "coordinates": [lat, lon],
                "current_date": date,
                "baseline_date": baseline_date,
                "cloud_cover": np.random.uniform(0.0, 0.2),  # Generally low cloud cover
                "collection": "STUB_LANDSAT8",
                "baseline_samples": np.random.randint(6, 16),
                "claim_context": claim_text[:100] if claim_text else "",
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return SatelliteResult(
                similarity=float(similarity),
                anomaly=anomaly,
                reality_score=float(reality_score),
                confidence=float(confidence),
                baseline_date=baseline_date,
                analysis_metadata=metadata,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Failed to generate stub satellite result: {e}")
            
            # Return default neutral result on error
            return SatelliteResult(
                similarity=0.5,
                anomaly=False,
                reality_score=0.5,
                confidence=0.3,
                baseline_date="2022-01-01",
                analysis_metadata={
                    "stub_mode": True,
                    "error": str(e),
                    "coordinates": [lat, lon]
                },
                processing_time_ms=200
            )
    
    def _determine_scenario(self, claim_text: str) -> str:
        """Determine the appropriate scenario based on claim text"""
        if not claim_text:
            return "normal"
        
        claim_lower = claim_text.lower()
        
        # Check for misinformation indicators first
        fake_indicators = ["fake", "hoax", "false", "conspiracy", "lie", "untrue"]
        if any(indicator in claim_lower for indicator in fake_indicators):
            return "fake_disaster"
        
        # Check for disaster scenarios
        for scenario_name, config in self.scenario_config["disaster_scenarios"].items():
            if any(keyword in claim_lower for keyword in config["keywords"]):
                return scenario_name
        
        # Check for development scenarios
        for scenario_name, config in self.scenario_config["development_scenarios"].items():
            if any(keyword in claim_lower for keyword in config["keywords"]):
                return scenario_name
        
        # Default to normal scenario
        return "normal"
    
    def _get_scenario_config(self, scenario: str) -> Dict[str, Any]:
        """Get configuration for a specific scenario"""
        # Search through all scenario categories
        for category in self.scenario_config.values():
            if scenario in category:
                return category[scenario]
        
        # Return normal scenario as fallback
        return self.scenario_config["normal_scenarios"]["normal"]
    
    def create_cached_response(self, lat: float, lon: float, date: str, 
                             claim_text: str = "") -> SatelliteResult:
        """
        Create and cache a satellite validation response.
        Subsequent calls with same parameters will return cached result.
        """
        # Create cache key
        cache_key = hashlib.md5(f"{lat:.4f}_{lon:.4f}_{date}_{claim_text}".encode()).hexdigest()
        cache_file = self.cache_dir / f"stub_{cache_key}.json"
        
        # Try to load from cache
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if cache is still valid (not older than 1 hour for testing)
                cache_time = datetime.fromisoformat(cached_data['cached_at'])
                if (datetime.utcnow() - cache_time).seconds < 3600:
                    return SatelliteResult.from_dict(cached_data['result'])
                    
            except Exception as e:
                logger.warning(f"Failed to load cached stub result: {e}")
        
        # Generate new result
        result = self.generate_stub_result(lat, lon, date, claim_text)
        
        # Cache the result
        try:
            cache_data = {
                "result": result.to_dict(),
                "cached_at": datetime.utcnow().isoformat(),
                "parameters": {
                    "lat": lat,
                    "lon": lon,
                    "date": date,
                    "claim_text": claim_text[:100]
                }
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to cache stub result: {e}")
        
        return result
    
    def get_scenario_examples(self) -> Dict[str, Dict[str, Any]]:
        """Get example scenarios for testing and documentation"""
        examples = {}
        
        for category_name, category in self.scenario_config.items():
            examples[category_name] = {}
            for scenario_name, scenario_config in category.items():
                examples[category_name][scenario_name] = {
                    "description": f"Scenario for {scenario_name} claims",
                    "keywords": scenario_config["keywords"],
                    "expected_similarity": f"{scenario_config['similarity_range'][0]:.1f} - {scenario_config['similarity_range'][1]:.1f}",
                    "expected_reality_score": f"{scenario_config['reality_score_range'][0]:.1f} - {scenario_config['reality_score_range'][1]:.1f}",
                    "example_claim": self._generate_example_claim(scenario_name, scenario_config)
                }
        
        return examples
    
    def _generate_example_claim(self, scenario_name: str, scenario_config: Dict[str, Any]) -> str:
        """Generate example claim text for a scenario"""
        keywords = scenario_config["keywords"]
        
        if scenario_name == "flood":
            return f"Major flooding reported in Mumbai after heavy rains"
        elif scenario_name == "earthquake":
            return f"Earthquake of magnitude 6.5 hits Delhi, buildings damaged"
        elif scenario_name == "fire":
            return f"Wildfire spreads across forest areas in Karnataka"
        elif scenario_name == "construction":
            return f"New infrastructure development project started in Bangalore"
        elif scenario_name == "deforestation":
            return f"Large scale deforestation reported in Western Ghats"
        elif scenario_name == "fake_disaster":
            return f"Fake news: Tsunami warning issued for Chennai coast"
        else:
            return f"Normal conditions reported in the area"
    
    def clear_cache(self) -> int:
        """Clear all cached stub responses"""
        try:
            cache_files = list(self.cache_dir.glob("stub_*.json"))
            for cache_file in cache_files:
                cache_file.unlink()
            
            logger.info(f"Cleared {len(cache_files)} cached stub responses")
            return len(cache_files)
            
        except Exception as e:
            logger.error(f"Failed to clear stub cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached stub responses"""
        try:
            cache_files = list(self.cache_dir.glob("stub_*.json"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "total_cached_responses": len(cache_files),
                "total_cache_size_bytes": total_size,
                "cache_directory": str(self.cache_dir),
                "oldest_cache": min((f.stat().st_mtime for f in cache_files), default=0),
                "newest_cache": max((f.stat().st_mtime for f in cache_files), default=0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}


# Global stub manager instance
satellite_stub_manager = SatelliteStubManager()