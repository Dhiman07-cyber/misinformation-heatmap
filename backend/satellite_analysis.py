"""
Advanced satellite analysis algorithms for reality score calculation,
anomaly detection, and change analysis for misinformation validation.
"""

import logging
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from models import SatelliteResult, ClaimCategory
from config import config

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes detectable in satellite imagery"""
    NO_CHANGE = "no_change"
    VEGETATION_LOSS = "vegetation_loss"
    WATER_INCREASE = "water_increase"
    URBAN_DEVELOPMENT = "urban_development"
    FIRE_DAMAGE = "fire_damage"
    SEASONAL_CHANGE = "seasonal_change"
    CLOUD_INTERFERENCE = "cloud_interference"
    UNKNOWN_CHANGE = "unknown_change"


@dataclass
class ChangeAnalysis:
    """Results of satellite imagery change analysis"""
    change_type: ChangeType
    change_magnitude: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    affected_area_percent: float  # 0.0 - 100.0
    spectral_changes: Dict[str, float]  # Band-wise changes
    temporal_consistency: float  # How consistent the change is over time
    metadata: Dict[str, Any]


class SatelliteAnalyzer:
    """
    Advanced satellite imagery analysis for misinformation detection.
    Implements sophisticated algorithms for change detection and reality scoring.
    """
    
    def __init__(self):
        self.similarity_threshold = config.get_satellite_config().similarity_threshold
        self.spectral_bands = {
            'blue': 0, 'green': 1, 'red': 2, 'nir': 3, 'swir1': 4, 'swir2': 5
        }
        
    def analyze_change(self, current_embeddings: np.ndarray, 
                      baseline_embeddings: np.ndarray,
                      metadata: Dict[str, Any] = None) -> ChangeAnalysis:
        """
        Perform comprehensive change analysis between current and baseline imagery.
        
        Args:
            current_embeddings: Current satellite imagery embeddings
            baseline_embeddings: Historical baseline embeddings
            metadata: Additional metadata for context
            
        Returns:
            ChangeAnalysis with detailed change information
        """
        try:
            if metadata is None:
                metadata = {}
            
            # Calculate spectral band changes
            spectral_changes = self._calculate_spectral_changes(
                current_embeddings, baseline_embeddings
            )
            
            # Determine change type based on spectral patterns
            change_type = self._classify_change_type(spectral_changes, metadata)
            
            # Calculate change magnitude
            change_magnitude = self._calculate_change_magnitude(spectral_changes)
            
            # Estimate affected area (simplified model)
            affected_area = self._estimate_affected_area(spectral_changes, change_magnitude)
            
            # Calculate temporal consistency (if multiple observations available)
            temporal_consistency = self._calculate_temporal_consistency(
                spectral_changes, metadata
            )
            
            # Calculate confidence in change detection
            confidence = self._calculate_change_confidence(
                spectral_changes, change_magnitude, temporal_consistency
            )
            
            return ChangeAnalysis(
                change_type=change_type,
                change_magnitude=change_magnitude,
                confidence=confidence,
                affected_area_percent=affected_area,
                spectral_changes=spectral_changes,
                temporal_consistency=temporal_consistency,
                metadata={
                    "analysis_method": "spectral_comparison",
                    "bands_analyzed": len(spectral_changes),
                    "similarity_threshold": self.similarity_threshold,
                    **metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Change analysis failed: {e}")
            
            # Return neutral analysis on error
            return ChangeAnalysis(
                change_type=ChangeType.UNKNOWN_CHANGE,
                change_magnitude=0.5,
                confidence=0.2,
                affected_area_percent=0.0,
                spectral_changes={},
                temporal_consistency=0.5,
                metadata={"error": str(e)}
            )
    
    def _calculate_spectral_changes(self, current: np.ndarray, 
                                  baseline: np.ndarray) -> Dict[str, float]:
        """Calculate changes in individual spectral bands"""
        spectral_changes = {}
        
        try:
            # Ensure arrays are same length
            min_length = min(len(current), len(baseline))
            current = current[:min_length]
            baseline = baseline[:min_length]
            
            # Calculate changes for each spectral band (assuming 6 bands × 4 stats each)
            bands_per_stat = 6
            stats_per_band = 4  # mean, stddev, min, max
            
            for band_name, band_idx in self.spectral_bands.items():
                if band_idx * stats_per_band + stats_per_band <= len(current):
                    # Extract statistics for this band
                    start_idx = band_idx * stats_per_band
                    end_idx = start_idx + stats_per_band
                    
                    current_band = current[start_idx:end_idx]
                    baseline_band = baseline[start_idx:end_idx]
                    
                    # Calculate normalized difference
                    band_change = np.mean(np.abs(current_band - baseline_band))
                    spectral_changes[band_name] = float(band_change)
            
            # Calculate derived indices changes (NDVI, etc.)
            if len(current) >= 26:  # Full embedding with indices
                ndvi_change = abs(current[24] - baseline[24])  # NDVI mean change
                spectral_changes['ndvi'] = float(ndvi_change)
                
                ndvi_std_change = abs(current[25] - baseline[25])  # NDVI std change
                spectral_changes['ndvi_variability'] = float(ndvi_std_change)
            
        except Exception as e:
            logger.warning(f"Spectral change calculation failed: {e}")
        
        return spectral_changes
    
    def _classify_change_type(self, spectral_changes: Dict[str, float], 
                            metadata: Dict[str, Any]) -> ChangeType:
        """Classify the type of change based on spectral patterns"""
        try:
            # Get cloud cover information
            cloud_cover = metadata.get('cloud_cover', 0.0)
            if cloud_cover > 0.3:  # High cloud cover
                return ChangeType.CLOUD_INTERFERENCE
            
            # Check for vegetation changes (NIR and Red band changes)
            nir_change = spectral_changes.get('nir', 0.0)
            red_change = spectral_changes.get('red', 0.0)
            ndvi_change = spectral_changes.get('ndvi', 0.0)
            
            # Vegetation loss pattern (decreased NIR, increased Red, decreased NDVI)
            if nir_change > 0.2 and red_change > 0.1 and ndvi_change > 0.3:
                return ChangeType.VEGETATION_LOSS
            
            # Water increase pattern (decreased NIR and SWIR, increased Blue/Green)
            blue_change = spectral_changes.get('blue', 0.0)
            green_change = spectral_changes.get('green', 0.0)
            swir1_change = spectral_changes.get('swir1', 0.0)
            
            if (blue_change > 0.15 and green_change > 0.15 and 
                nir_change > 0.2 and swir1_change > 0.2):
                return ChangeType.WATER_INCREASE
            
            # Urban development pattern (increased all visible bands, decreased NIR)
            visible_change = np.mean([
                spectral_changes.get('blue', 0.0),
                spectral_changes.get('green', 0.0),
                spectral_changes.get('red', 0.0)
            ])
            
            if visible_change > 0.15 and nir_change > 0.1:
                return ChangeType.URBAN_DEVELOPMENT
            
            # Fire damage pattern (increased Red and SWIR, decreased NIR and NDVI)
            swir2_change = spectral_changes.get('swir2', 0.0)
            if (red_change > 0.2 and swir1_change > 0.2 and swir2_change > 0.2 and
                nir_change > 0.15 and ndvi_change > 0.2):
                return ChangeType.FIRE_DAMAGE
            
            # Check for seasonal changes (moderate, consistent changes across bands)
            all_changes = [v for v in spectral_changes.values() if isinstance(v, float)]
            if all_changes:
                avg_change = np.mean(all_changes)
                change_std = np.std(all_changes)
                
                if 0.05 <= avg_change <= 0.15 and change_std < 0.05:
                    return ChangeType.SEASONAL_CHANGE
            
            # Determine if significant change occurred
            max_change = max(spectral_changes.values()) if spectral_changes else 0.0
            if max_change < 0.05:
                return ChangeType.NO_CHANGE
            else:
                return ChangeType.UNKNOWN_CHANGE
                
        except Exception as e:
            logger.warning(f"Change type classification failed: {e}")
            return ChangeType.UNKNOWN_CHANGE
    
    def _calculate_change_magnitude(self, spectral_changes: Dict[str, float]) -> float:
        """Calculate overall magnitude of change"""
        try:
            if not spectral_changes:
                return 0.0
            
            # Weight different bands based on their importance for change detection
            band_weights = {
                'nir': 0.25,      # Very important for vegetation
                'red': 0.20,      # Important for vegetation and fire
                'swir1': 0.20,    # Important for water and fire
                'green': 0.15,    # Moderate importance
                'blue': 0.10,     # Lower importance
                'swir2': 0.10,    # Lower importance
                'ndvi': 0.30,     # Very important vegetation index
                'ndvi_variability': 0.10
            }
            
            weighted_change = 0.0
            total_weight = 0.0
            
            for band, change in spectral_changes.items():
                weight = band_weights.get(band, 0.05)  # Default small weight
                weighted_change += change * weight
                total_weight += weight
            
            if total_weight > 0:
                magnitude = weighted_change / total_weight
            else:
                magnitude = np.mean(list(spectral_changes.values()))
            
            return float(np.clip(magnitude, 0.0, 1.0))
            
        except Exception as e:
            logger.warning(f"Change magnitude calculation failed: {e}")
            return 0.5
    
    def _estimate_affected_area(self, spectral_changes: Dict[str, float], 
                              change_magnitude: float) -> float:
        """Estimate percentage of area affected by changes"""
        try:
            # Simple model based on change magnitude and variability
            # In reality, this would require pixel-level analysis
            
            # Higher variability suggests more localized changes
            ndvi_variability = spectral_changes.get('ndvi_variability', 0.1)
            
            if change_magnitude < 0.1:
                # Minimal change
                affected_area = change_magnitude * 10  # 0-1%
            elif change_magnitude < 0.3:
                # Moderate change
                base_area = 5 + (change_magnitude - 0.1) * 25  # 5-10%
                affected_area = base_area * (1 + ndvi_variability)
            else:
                # Significant change
                base_area = 15 + (change_magnitude - 0.3) * 50  # 15-50%
                affected_area = base_area * (1 + ndvi_variability * 2)
            
            return float(np.clip(affected_area, 0.0, 100.0))
            
        except Exception as e:
            logger.warning(f"Affected area estimation failed: {e}")
            return 0.0
    
    def _calculate_temporal_consistency(self, spectral_changes: Dict[str, float],
                                      metadata: Dict[str, Any]) -> float:
        """Calculate temporal consistency of changes"""
        try:
            # In a full implementation, this would analyze multiple time points
            # For now, use metadata to estimate consistency
            
            baseline_samples = metadata.get('baseline_samples', 1)
            
            # More baseline samples suggest better temporal understanding
            consistency_base = min(0.9, baseline_samples / 12)  # Max with 12+ samples
            
            # Adjust based on change magnitude variability
            changes = list(spectral_changes.values())
            if len(changes) > 1:
                change_std = np.std(changes)
                # Lower variability suggests more consistent change
                consistency_adjustment = 1.0 - min(0.3, change_std)
                consistency_base *= consistency_adjustment
            
            return float(np.clip(consistency_base, 0.1, 0.95))
            
        except Exception as e:
            logger.warning(f"Temporal consistency calculation failed: {e}")
            return 0.5
    
    def _calculate_change_confidence(self, spectral_changes: Dict[str, float],
                                   change_magnitude: float, 
                                   temporal_consistency: float) -> float:
        """Calculate confidence in change detection results"""
        try:
            confidence = 0.5  # Base confidence
            
            # Higher confidence with more spectral bands analyzed
            band_bonus = min(0.2, len(spectral_changes) / 10)
            confidence += band_bonus
            
            # Higher confidence with temporal consistency
            temporal_bonus = temporal_consistency * 0.3
            confidence += temporal_bonus
            
            # Adjust based on change magnitude (very low or very high reduces confidence)
            if 0.1 <= change_magnitude <= 0.8:
                magnitude_bonus = 0.2
            else:
                magnitude_bonus = 0.0
            confidence += magnitude_bonus
            
            return float(np.clip(confidence, 0.1, 0.95))
            
        except Exception as e:
            logger.warning(f"Change confidence calculation failed: {e}")
            return 0.5


class RealityScoreCalculator:
    """
    Calculates reality scores for misinformation claims based on satellite analysis
    and claim context. Implements multiple scoring algorithms and validation methods.
    """
    
    def __init__(self):
        self.analyzer = SatelliteAnalyzer()
        
    def calculate_reality_score(self, satellite_result: SatelliteResult,
                              claim_text: str = "", 
                              claim_category: Optional[ClaimCategory] = None) -> float:
        """
        Calculate comprehensive reality score combining satellite analysis with claim context.
        
        Args:
            satellite_result: Basic satellite validation result
            claim_text: Text of the claim being validated
            claim_category: Category of the claim (if known)
            
        Returns:
            Enhanced reality score (0.0 - 1.0)
        """
        try:
            # Start with base satellite reality score
            base_score = satellite_result.reality_score
            
            # Apply claim-specific adjustments
            context_adjustment = self._calculate_context_adjustment(
                claim_text, claim_category, satellite_result
            )
            
            # Apply confidence weighting
            confidence_weight = satellite_result.confidence
            
            # Combine scores
            enhanced_score = (base_score * confidence_weight + 
                            context_adjustment * (1 - confidence_weight))
            
            # Apply final validation checks
            final_score = self._apply_validation_checks(
                enhanced_score, satellite_result, claim_text
            )
            
            return float(np.clip(final_score, 0.0, 1.0))
            
        except Exception as e:
            logger.error(f"Reality score calculation failed: {e}")
            return satellite_result.reality_score  # Fallback to base score
    
    def _calculate_context_adjustment(self, claim_text: str, 
                                    claim_category: Optional[ClaimCategory],
                                    satellite_result: SatelliteResult) -> float:
        """Calculate adjustment based on claim context"""
        try:
            adjustment = 0.5  # Neutral adjustment
            
            if not claim_text:
                return adjustment
            
            claim_lower = claim_text.lower()
            similarity = satellite_result.similarity
            
            # Disaster claims analysis
            if self._is_disaster_claim(claim_text, claim_category):
                # For disaster claims, low similarity might support reality
                if similarity < 0.3:
                    adjustment = 0.7  # Disasters often cause visible changes
                elif similarity > 0.8:
                    adjustment = 0.3  # No change suggests false disaster claim
                else:
                    adjustment = 0.5  # Moderate change, uncertain
            
            # Environmental claims analysis
            elif self._is_environmental_claim(claim_text, claim_category):
                # Environmental changes should show moderate similarity changes
                if 0.3 <= similarity <= 0.7:
                    adjustment = 0.6  # Expected range for real environmental changes
                elif similarity > 0.9:
                    adjustment = 0.2  # No change suggests false environmental claim
                else:
                    adjustment = 0.4  # Extreme changes might be exaggerated
            
            # Infrastructure/development claims
            elif self._is_infrastructure_claim(claim_text, claim_category):
                # Infrastructure changes should show clear but localized changes
                if 0.4 <= similarity <= 0.8:
                    adjustment = 0.7  # Expected range for infrastructure changes
                else:
                    adjustment = 0.4  # Outside expected range
            
            # Conspiracy/fake claims
            elif self._is_conspiracy_claim(claim_text):
                # Conspiracy claims often show normal conditions
                if similarity > 0.7:
                    adjustment = 0.2  # High similarity supports it being fake
                else:
                    adjustment = 0.6  # Unexpected changes, might be real issue
            
            return adjustment
            
        except Exception as e:
            logger.warning(f"Context adjustment calculation failed: {e}")
            return 0.5
    
    def _is_disaster_claim(self, claim_text: str, 
                          claim_category: Optional[ClaimCategory]) -> bool:
        """Check if claim is about disasters"""
        if claim_category == ClaimCategory.DISASTER:
            return True
        
        disaster_keywords = [
            'flood', 'flooding', 'earthquake', 'fire', 'wildfire', 'cyclone',
            'tsunami', 'landslide', 'drought', 'storm', 'hurricane', 'tornado'
        ]
        
        return any(keyword in claim_text.lower() for keyword in disaster_keywords)
    
    def _is_environmental_claim(self, claim_text: str,
                              claim_category: Optional[ClaimCategory]) -> bool:
        """Check if claim is about environmental changes"""
        if claim_category == ClaimCategory.ENVIRONMENT:
            return True
        
        env_keywords = [
            'deforestation', 'forest', 'trees', 'pollution', 'mining',
            'climate', 'environment', 'ecosystem', 'biodiversity', 'conservation'
        ]
        
        return any(keyword in claim_text.lower() for keyword in env_keywords)
    
    def _is_infrastructure_claim(self, claim_text: str,
                               claim_category: Optional[ClaimCategory]) -> bool:
        """Check if claim is about infrastructure/development"""
        infra_keywords = [
            'construction', 'building', 'development', 'infrastructure',
            'road', 'bridge', 'airport', 'railway', 'metro', 'project'
        ]
        
        return any(keyword in claim_text.lower() for keyword in infra_keywords)
    
    def _is_conspiracy_claim(self, claim_text: str) -> bool:
        """Check if claim contains conspiracy indicators"""
        conspiracy_keywords = [
            'conspiracy', 'cover-up', 'hidden', 'secret', 'fake', 'hoax',
            'lie', 'false flag', 'staged', 'propaganda', 'manipulation'
        ]
        
        return any(keyword in claim_text.lower() for keyword in conspiracy_keywords)
    
    def _apply_validation_checks(self, score: float, satellite_result: SatelliteResult,
                               claim_text: str) -> float:
        """Apply final validation checks to the reality score"""
        try:
            # Reduce score if satellite analysis had errors
            if satellite_result.error_message:
                score *= 0.7
            
            # Reduce score for very high cloud cover
            cloud_cover = satellite_result.analysis_metadata.get('cloud_cover', 0.0)
            if cloud_cover > 0.5:
                score *= (1.0 - cloud_cover * 0.3)
            
            # Boost score for high confidence satellite analysis
            if satellite_result.confidence > 0.8:
                score = min(0.95, score * 1.1)
            
            # Apply temporal validation (recent claims should have higher confidence)
            current_date = satellite_result.analysis_metadata.get('current_date', '')
            if current_date:
                try:
                    claim_date = datetime.fromisoformat(current_date)
                    days_old = (datetime.utcnow() - claim_date).days
                    
                    if days_old > 30:  # Old claims are harder to validate
                        score *= 0.9
                except:
                    pass
            
            return score
            
        except Exception as e:
            logger.warning(f"Validation checks failed: {e}")
            return score


# Global instances
satellite_analyzer = SatelliteAnalyzer()
reality_score_calculator = RealityScoreCalculator()