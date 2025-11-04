"""
Unit tests for satellite validation components including Google Earth Engine client,
stub system, reality score calculation, and anomaly detection.
"""

import pytest
import asyncio
import os
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Set environment for testing
os.environ["MODE"] = "local"

# Import satellite validation components
from satellite_client import (
    GoogleEarthEngineClient, SatelliteValidator, SatelliteImagery, 
    BaselineData, satellite_validator
)
from satellite_stub import SatelliteStubManager, satellite_stub_manager
from satellite_analysis import (
    SatelliteAnalyzer, RealityScoreCalculator, ChangeAnalysis, ChangeType,
    satellite_analyzer, reality_score_calculator
)
from models import SatelliteResult, ClaimCategory
from config import Config


class TestSatelliteStubManager:
    """Test cases for satellite stub system"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.stub_manager = SatelliteStubManager()
    
    def test_scenario_determination(self):
        """Test determination of appropriate scenarios based on claim text"""
        # Test disaster scenarios
        flood_claim = "Major flooding reported in Mumbai after heavy rains"
        assert self.stub_manager._determine_scenario(flood_claim) == "flood"
        
        earthquake_claim = "Earthquake hits Delhi, buildings damaged"
        assert self.stub_manager._determine_scenario(earthquake_claim) == "earthquake"
        
        fire_claim = "Wildfire spreads across forest areas"
        assert self.stub_manager._determine_scenario(fire_claim) == "fire"
        
        # Test development scenarios
        construction_claim = "New construction project started in Bangalore"
        assert self.stub_manager._determine_scenario(construction_claim) == "construction"
        
        deforestation_claim = "Deforestation reported in Western Ghats"
        assert self.stub_manager._determine_scenario(deforestation_claim) == "deforestation"
        
        # Test misinformation scenarios
        fake_claim = "Fake news about tsunami warning"
        assert self.stub_manager._determine_scenario(fake_claim) == "fake_disaster"
        
        # Test normal scenario
        normal_claim = "Weather conditions are normal"
        assert self.stub_manager._determine_scenario(normal_claim) == "normal"
    
    def test_stub_result_generation(self):
        """Test generation of realistic stub satellite results"""
        lat, lon = 19.0760, 72.8777  # Mumbai coordinates
        date = "2023-06-15"
        claim_text = "Flooding reported in Mumbai"
        
        result = self.stub_manager.generate_stub_result(lat, lon, date, claim_text)
        
        assert isinstance(result, SatelliteResult)
        assert 0.0 <= result.similarity <= 1.0
        assert 0.0 <= result.reality_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.analysis_metadata["stub_mode"] == True
        assert result.analysis_metadata["scenario"] == "flood"
        assert result.processing_time_ms > 0
    
    def test_deterministic_results(self):
        """Test that stub results are deterministic for same inputs"""
        lat, lon = 28.6139, 77.2090  # Delhi coordinates
        date = "2023-05-10"
        claim_text = "Construction activity in Delhi"
        
        result1 = self.stub_manager.generate_stub_result(lat, lon, date, claim_text)
        result2 = self.stub_manager.generate_stub_result(lat, lon, date, claim_text)
        
        # Results should be identical for same inputs
        assert result1.similarity == result2.similarity
        assert result1.reality_score == result2.reality_score
        assert result1.confidence == result2.confidence
        assert result1.analysis_metadata["seed"] == result2.analysis_metadata["seed"]
    
    def test_scenario_configuration(self):
        """Test that scenario configurations are properly loaded"""
        scenarios = self.stub_manager.scenario_config
        
        # Check that all required scenario categories exist
        assert "disaster_scenarios" in scenarios
        assert "development_scenarios" in scenarios
        assert "normal_scenarios" in scenarios
        assert "misinformation_scenarios" in scenarios
        
        # Check specific scenarios
        assert "flood" in scenarios["disaster_scenarios"]
        assert "construction" in scenarios["development_scenarios"]
        assert "fake_disaster" in scenarios["misinformation_scenarios"]
        
        # Validate scenario structure
        flood_config = scenarios["disaster_scenarios"]["flood"]
        assert "similarity_range" in flood_config
        assert "reality_score_range" in flood_config
        assert "confidence_range" in flood_config
        assert "keywords" in flood_config
    
    def test_cached_responses(self):
        """Test caching functionality for stub responses"""
        lat, lon = 12.9716, 77.5946  # Bangalore coordinates
        date = "2023-07-20"
        claim_text = "Development project in Bangalore"
        
        # Clear any existing cache
        self.stub_manager.clear_cache()
        
        # First call should generate new result
        result1 = self.stub_manager.create_cached_response(lat, lon, date, claim_text)
        
        # Second call should return cached result
        result2 = self.stub_manager.create_cached_response(lat, lon, date, claim_text)
        
        # Results should be identical (from cache)
        assert result1.similarity == result2.similarity
        assert result1.reality_score == result2.reality_score
        
        # Check cache stats
        stats = self.stub_manager.get_cache_stats()
        assert stats["total_cached_responses"] >= 1
    
    def test_scenario_examples(self):
        """Test generation of scenario examples"""
        examples = self.stub_manager.get_scenario_examples()
        
        assert isinstance(examples, dict)
        assert "disaster_scenarios" in examples
        
        flood_example = examples["disaster_scenarios"]["flood"]
        assert "description" in flood_example
        assert "keywords" in flood_example
        assert "expected_similarity" in flood_example
        assert "expected_reality_score" in flood_example
        assert "example_claim" in flood_example


class TestSatelliteAnalyzer:
    """Test cases for satellite analysis algorithms"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.analyzer = SatelliteAnalyzer()
    
    def test_spectral_changes_calculation(self):
        """Test calculation of spectral band changes"""
        # Create mock embeddings (6 bands × 4 stats + 2 indices = 26 values)
        current = np.random.rand(26).astype(np.float32)
        baseline = np.random.rand(26).astype(np.float32)
        
        spectral_changes = self.analyzer._calculate_spectral_changes(current, baseline)
        
        assert isinstance(spectral_changes, dict)
        assert "blue" in spectral_changes
        assert "green" in spectral_changes
        assert "red" in spectral_changes
        assert "nir" in spectral_changes
        assert "swir1" in spectral_changes
        assert "swir2" in spectral_changes
        assert "ndvi" in spectral_changes
        
        # All changes should be non-negative
        for change in spectral_changes.values():
            assert change >= 0.0
    
    def test_change_type_classification(self):
        """Test classification of different change types"""
        # Test vegetation loss pattern
        veg_loss_changes = {
            'nir': 0.3,      # Decreased NIR
            'red': 0.2,      # Increased Red
            'ndvi': 0.4,     # Decreased NDVI
            'blue': 0.1,
            'green': 0.1,
            'swir1': 0.1,
            'swir2': 0.1
        }
        
        change_type = self.analyzer._classify_change_type(veg_loss_changes, {})
        assert change_type == ChangeType.VEGETATION_LOSS
        
        # Test water increase pattern
        water_changes = {
            'blue': 0.2,     # Increased Blue
            'green': 0.2,    # Increased Green
            'nir': 0.3,      # Decreased NIR
            'swir1': 0.3,    # Decreased SWIR
            'red': 0.1,
            'swir2': 0.1,
            'ndvi': 0.1
        }
        
        change_type = self.analyzer._classify_change_type(water_changes, {})
        assert change_type == ChangeType.WATER_INCREASE
        
        # Test no change pattern
        no_changes = {band: 0.02 for band in ['blue', 'green', 'red', 'nir', 'swir1', 'swir2']}
        
        change_type = self.analyzer._classify_change_type(no_changes, {})
        assert change_type == ChangeType.NO_CHANGE
        
        # Test cloud interference
        cloud_metadata = {'cloud_cover': 0.5}
        change_type = self.analyzer._classify_change_type({}, cloud_metadata)
        assert change_type == ChangeType.CLOUD_INTERFERENCE
    
    def test_change_magnitude_calculation(self):
        """Test calculation of overall change magnitude"""
        # Test high change scenario
        high_changes = {
            'nir': 0.5,
            'red': 0.4,
            'ndvi': 0.6,
            'blue': 0.3,
            'green': 0.3,
            'swir1': 0.4
        }
        
        magnitude = self.analyzer._calculate_change_magnitude(high_changes)
        assert 0.3 <= magnitude <= 1.0  # Should be high
        
        # Test low change scenario
        low_changes = {band: 0.05 for band in high_changes.keys()}
        
        magnitude = self.analyzer._calculate_change_magnitude(low_changes)
        assert 0.0 <= magnitude <= 0.2  # Should be low
        
        # Test empty changes
        magnitude = self.analyzer._calculate_change_magnitude({})
        assert magnitude == 0.0
    
    def test_affected_area_estimation(self):
        """Test estimation of affected area percentage"""
        # Test minimal change
        area = self.analyzer._estimate_affected_area({}, 0.05)
        assert 0.0 <= area <= 5.0
        
        # Test moderate change
        area = self.analyzer._estimate_affected_area({'ndvi_variability': 0.1}, 0.2)
        assert 5.0 <= area <= 20.0
        
        # Test significant change
        area = self.analyzer._estimate_affected_area({'ndvi_variability': 0.2}, 0.5)
        assert 15.0 <= area <= 100.0
    
    def test_complete_change_analysis(self):
        """Test complete change analysis pipeline"""
        # Create realistic embeddings
        current = np.random.rand(26).astype(np.float32)
        baseline = np.random.rand(26).astype(np.float32)
        
        # Make current different from baseline to simulate change
        current[12:16] *= 0.5  # Reduce NIR (vegetation loss)
        current[8:12] *= 1.5   # Increase Red
        
        metadata = {
            'cloud_cover': 0.1,
            'baseline_samples': 10
        }
        
        analysis = self.analyzer.analyze_change(current, baseline, metadata)
        
        assert isinstance(analysis, ChangeAnalysis)
        assert isinstance(analysis.change_type, ChangeType)
        assert 0.0 <= analysis.change_magnitude <= 1.0
        assert 0.0 <= analysis.confidence <= 1.0
        assert 0.0 <= analysis.affected_area_percent <= 100.0
        assert 0.0 <= analysis.temporal_consistency <= 1.0
        assert isinstance(analysis.spectral_changes, dict)
        assert isinstance(analysis.metadata, dict)


class TestRealityScoreCalculator:
    """Test cases for reality score calculation"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.calculator = RealityScoreCalculator()
    
    def test_disaster_claim_analysis(self):
        """Test reality score calculation for disaster claims"""
        # Create satellite result showing significant change (low similarity)
        satellite_result = SatelliteResult(
            similarity=0.2,  # Low similarity suggests change
            reality_score=0.6,
            confidence=0.8,
            analysis_metadata={'cloud_cover': 0.1}
        )
        
        flood_claim = "Major flooding reported in Mumbai"
        
        enhanced_score = self.calculator.calculate_reality_score(
            satellite_result, flood_claim, ClaimCategory.DISASTER
        )
        
        # For disaster claims with low similarity, score should be boosted
        assert enhanced_score >= satellite_result.reality_score
        assert 0.0 <= enhanced_score <= 1.0
    
    def test_conspiracy_claim_analysis(self):
        """Test reality score calculation for conspiracy claims"""
        # Create satellite result showing no change (high similarity)
        satellite_result = SatelliteResult(
            similarity=0.9,  # High similarity suggests no change
            reality_score=0.5,
            confidence=0.8,
            analysis_metadata={'cloud_cover': 0.1}
        )
        
        conspiracy_claim = "Government is hiding secret construction project"
        
        enhanced_score = self.calculator.calculate_reality_score(
            satellite_result, conspiracy_claim
        )
        
        # For conspiracy claims with high similarity, score should be reduced
        assert enhanced_score <= satellite_result.reality_score
        assert 0.0 <= enhanced_score <= 1.0
    
    def test_environmental_claim_analysis(self):
        """Test reality score calculation for environmental claims"""
        satellite_result = SatelliteResult(
            similarity=0.5,  # Moderate similarity
            reality_score=0.6,
            confidence=0.7,
            analysis_metadata={'cloud_cover': 0.15}
        )
        
        env_claim = "Deforestation in Western Ghats forest area"
        
        enhanced_score = self.calculator.calculate_reality_score(
            satellite_result, env_claim, ClaimCategory.ENVIRONMENT
        )
        
        # Environmental claims with moderate similarity should get appropriate scoring
        assert 0.0 <= enhanced_score <= 1.0
    
    def test_claim_type_detection(self):
        """Test detection of different claim types"""
        # Test disaster claim detection
        assert self.calculator._is_disaster_claim("Flood in Mumbai", ClaimCategory.DISASTER)
        assert self.calculator._is_disaster_claim("Earthquake hits Delhi", None)
        
        # Test environmental claim detection
        assert self.calculator._is_environmental_claim("Deforestation reported", ClaimCategory.ENVIRONMENT)
        assert self.calculator._is_environmental_claim("Forest clearing in area", None)
        
        # Test infrastructure claim detection
        assert self.calculator._is_infrastructure_claim("New construction project", None)
        assert self.calculator._is_infrastructure_claim("Bridge development started", None)
        
        # Test conspiracy claim detection
        assert self.calculator._is_conspiracy_claim("Government cover-up of incident")
        assert self.calculator._is_conspiracy_claim("Fake news about disaster")
    
    def test_validation_checks(self):
        """Test final validation checks on reality scores"""
        base_score = 0.7
        
        # Test with error message (should reduce score)
        satellite_result_error = SatelliteResult(
            similarity=0.5,
            reality_score=0.7,
            confidence=0.8,
            error_message="Some error occurred",
            analysis_metadata={}
        )
        
        adjusted_score = self.calculator._apply_validation_checks(
            base_score, satellite_result_error, ""
        )
        assert adjusted_score < base_score
        
        # Test with high cloud cover (should reduce score)
        satellite_result_cloudy = SatelliteResult(
            similarity=0.5,
            reality_score=0.7,
            confidence=0.8,
            analysis_metadata={'cloud_cover': 0.7}
        )
        
        adjusted_score = self.calculator._apply_validation_checks(
            base_score, satellite_result_cloudy, ""
        )
        assert adjusted_score < base_score
        
        # Test with high confidence (should boost score)
        satellite_result_confident = SatelliteResult(
            similarity=0.5,
            reality_score=0.7,
            confidence=0.9,
            analysis_metadata={'cloud_cover': 0.1}
        )
        
        adjusted_score = self.calculator._apply_validation_checks(
            base_score, satellite_result_confident, ""
        )
        assert adjusted_score >= base_score


class TestSatelliteValidator:
    """Test cases for main satellite validator"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.validator = SatelliteValidator()
    
    @pytest.mark.asyncio
    async def test_validator_initialization(self):
        """Test satellite validator initialization"""
        # Should initialize successfully in local mode (stub mode)
        success = await self.validator.initialize()
        assert success == True
        assert self.validator.initialized == True
    
    @pytest.mark.asyncio
    async def test_claim_validation_stub_mode(self):
        """Test claim validation in stub mode"""
        await self.validator.initialize()
        
        # Test with Mumbai coordinates
        lat, lon = 19.0760, 72.8777
        date = "2023-06-15"
        claim_text = "Flooding reported in Mumbai after heavy rains"
        
        result = await self.validator.validate_claim(lat, lon, date, claim_text)
        
        assert isinstance(result, SatelliteResult)
        assert 0.0 <= result.similarity <= 1.0
        assert 0.0 <= result.reality_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert result.processing_time_ms > 0
        assert result.analysis_metadata is not None
        assert "coordinates" in result.analysis_metadata
    
    @pytest.mark.asyncio
    async def test_invalid_coordinates(self):
        """Test validation with coordinates outside India"""
        await self.validator.initialize()
        
        # Use coordinates outside India (New York)
        lat, lon = 40.7128, -74.0060
        date = "2023-06-15"
        claim_text = "Some claim about New York"
        
        result = await self.validator.validate_claim(lat, lon, date, claim_text)
        
        assert result.error_message is not None
        assert "outside India boundaries" in result.error_message
        assert result.confidence < 0.5  # Low confidence for invalid coordinates
    
    @pytest.mark.asyncio
    async def test_similarity_calculation(self):
        """Test similarity calculation between embeddings"""
        # Create test embeddings
        embedding1 = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        embedding2 = np.array([0.1, 0.2, 0.3, 0.4, 0.5])  # Identical
        embedding3 = np.array([0.9, 0.8, 0.7, 0.6, 0.5])  # Different
        
        # Test identical embeddings
        similarity1 = self.validator._calculate_similarity(embedding1, embedding2)
        assert similarity1 == 1.0  # Should be perfect similarity
        
        # Test different embeddings
        similarity2 = self.validator._calculate_similarity(embedding1, embedding3)
        assert 0.0 <= similarity2 < 1.0  # Should be less than perfect
        
        # Test with zero embeddings
        zero_embedding = np.zeros(5)
        similarity3 = self.validator._calculate_similarity(embedding1, zero_embedding)
        assert 0.0 <= similarity3 <= 1.0  # Should handle gracefully


class TestSatelliteIntegration:
    """Integration tests for satellite validation system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation(self):
        """Test complete end-to-end satellite validation"""
        # Initialize validator
        validator = SatelliteValidator()
        await validator.initialize()
        
        # Test different types of claims
        test_cases = [
            {
                "lat": 19.0760, "lon": 72.8777,  # Mumbai
                "date": "2023-06-15",
                "claim": "Flooding in Mumbai after monsoon rains",
                "expected_scenario": "flood"
            },
            {
                "lat": 28.6139, "lon": 77.2090,  # Delhi
                "date": "2023-05-10",
                "claim": "Earthquake hits Delhi, no damage reported",
                "expected_scenario": "earthquake"
            },
            {
                "lat": 12.9716, "lon": 77.5946,  # Bangalore
                "date": "2023-07-20",
                "claim": "New tech park construction in Bangalore",
                "expected_scenario": "construction"
            }
        ]
        
        for test_case in test_cases:
            result = await validator.validate_claim(
                test_case["lat"], test_case["lon"], 
                test_case["date"], test_case["claim"]
            )
            
            # Validate result structure
            assert isinstance(result, SatelliteResult)
            assert 0.0 <= result.similarity <= 1.0
            assert 0.0 <= result.reality_score <= 1.0
            assert 0.0 <= result.confidence <= 1.0
            assert result.processing_time_ms > 0
            
            # Check that appropriate scenario was detected (in stub mode)
            if "stub_mode" in result.analysis_metadata:
                scenario = result.analysis_metadata.get("scenario", "")
                # Scenario should be related to claim type
                assert scenario != ""
    
    def test_error_handling(self):
        """Test error handling in satellite validation"""
        validator = SatelliteValidator()
        
        # Test validation without initialization
        import asyncio
        
        async def test_uninitialized():
            result = await validator.validate_claim(19.0760, 72.8777, "2023-06-15", "test")
            assert result.error_message is not None
            assert "not initialized" in result.error_message
        
        asyncio.run(test_uninitialized())
    
    def test_configuration_integration(self):
        """Test integration with configuration system"""
        # Test that satellite config is properly loaded
        config = Config()
        satellite_config = config.get_satellite_config()
        
        assert satellite_config.use_stub == True  # Should be True in local mode
        assert 0.0 <= satellite_config.similarity_threshold <= 1.0
        assert satellite_config.cache_duration_hours > 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])