"""
Unit tests for data models and database operations.
Tests validation, serialization, and database functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Import our models and database classes
from models import (
    ProcessedEvent, SatelliteResult, Claim, EventSource, LanguageCode, ClaimCategory,
    validate_indian_state, normalize_state_name, INDIAN_STATES
)
from database import SQLiteDatabase, DatabaseManager
from config import Config


class TestClaim:
    """Test cases for Claim data model"""
    
    def test_claim_creation(self):
        """Test basic claim creation and validation"""
        claim = Claim(
            text="Vaccine causes autism",
            category=ClaimCategory.HEALTH,
            confidence=0.8,
            entities=["vaccine", "autism"],
            geographic_entities=["India"],
            keywords=["health", "medical"]
        )
        
        assert claim.text == "Vaccine causes autism"
        assert claim.category == ClaimCategory.HEALTH
        assert claim.confidence == 0.8
        assert len(claim.entities) == 2
        assert claim.claim_id is not None
    
    def test_claim_validation(self):
        """Test claim validation rules"""
        # Test invalid confidence score
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Claim(text="Test claim", confidence=1.5)
        
        # Test empty text
        with pytest.raises(ValueError, match="Claim text cannot be empty"):
            Claim(text="", confidence=0.5)
        
        with pytest.raises(ValueError, match="Claim text cannot be empty"):
            Claim(text="   ", confidence=0.5)
    
    def test_claim_serialization(self):
        """Test claim to/from dictionary conversion"""
        original_claim = Claim(
            text="Test claim",
            category=ClaimCategory.POLITICS,
            confidence=0.7,
            entities=["entity1", "entity2"]
        )
        
        # Test to_dict
        claim_dict = original_claim.to_dict()
        assert claim_dict["text"] == "Test claim"
        assert claim_dict["category"] == "politics"
        assert claim_dict["confidence"] == 0.7
        
        # Test from_dict
        restored_claim = Claim.from_dict(claim_dict)
        assert restored_claim.text == original_claim.text
        assert restored_claim.category == original_claim.category
        assert restored_claim.confidence == original_claim.confidence
        assert restored_claim.entities == original_claim.entities


class TestSatelliteResult:
    """Test cases for SatelliteResult data model"""
    
    def test_satellite_result_creation(self):
        """Test basic satellite result creation"""
        result = SatelliteResult(
            similarity=0.2,
            reality_score=0.8,
            confidence=0.9,
            baseline_date="2023-01-01",
            analysis_metadata={"source": "landsat8"}
        )
        
        assert result.similarity == 0.2
        assert result.anomaly == True  # Should be True since similarity < 0.3
        assert result.reality_score == 0.8
        assert result.confidence == 0.9
    
    def test_satellite_validation(self):
        """Test satellite result validation"""
        # Test invalid similarity score
        with pytest.raises(ValueError, match="similarity must be between 0.0 and 1.0"):
            SatelliteResult(similarity=1.5)
        
        # Test invalid reality score
        with pytest.raises(ValueError, match="reality_score must be between 0.0 and 1.0"):
            SatelliteResult(reality_score=-0.1)
    
    def test_anomaly_detection(self):
        """Test automatic anomaly detection based on similarity threshold"""
        # High similarity - no anomaly
        result1 = SatelliteResult(similarity=0.8)
        assert result1.anomaly == False
        
        # Low similarity - anomaly detected
        result2 = SatelliteResult(similarity=0.1)
        assert result2.anomaly == True
    
    def test_stub_creation(self):
        """Test creation of stub satellite results for local mode"""
        stub = SatelliteResult.create_stub(28.6139, 77.2090)  # New Delhi coordinates
        
        assert 0.0 <= stub.similarity <= 1.0
        assert 0.0 <= stub.reality_score <= 1.0
        assert 0.0 <= stub.confidence <= 1.0
        assert stub.analysis_metadata["stub_mode"] == True
        assert stub.analysis_metadata["coordinates"] == [28.6139, 77.2090]
    
    def test_satellite_serialization(self):
        """Test satellite result serialization"""
        original = SatelliteResult(
            similarity=0.4,
            reality_score=0.6,
            confidence=0.8,
            baseline_date="2023-01-01"
        )
        
        # Test to_dict
        result_dict = original.to_dict()
        assert result_dict["similarity"] == 0.4
        assert result_dict["reality_score"] == 0.6
        
        # Test from_dict
        restored = SatelliteResult.from_dict(result_dict)
        assert restored.similarity == original.similarity
        assert restored.reality_score == original.reality_score


class TestProcessedEvent:
    """Test cases for ProcessedEvent data model"""
    
    def test_event_creation(self):
        """Test basic event creation"""
        event = ProcessedEvent(
            source=EventSource.NEWS,
            original_text="Breaking news from Delhi",
            lang=LanguageCode.ENGLISH,
            region_hint="Delhi",
            lat=28.6139,
            lon=77.2090,
            virality_score=0.7
        )
        
        assert event.source == EventSource.NEWS
        assert event.original_text == "Breaking news from Delhi"
        assert event.region_hint == "Delhi"
        assert event.virality_score == 0.7
        assert event.event_id is not None
        assert event.satellite is not None  # Should be auto-created
    
    def test_event_validation(self):
        """Test event validation rules"""
        # Test empty text
        with pytest.raises(ValueError, match="Original text cannot be empty"):
            ProcessedEvent(original_text="")
        
        # Test invalid virality score
        with pytest.raises(ValueError, match="Virality score must be between 0.0 and 1.0"):
            ProcessedEvent(original_text="Test", virality_score=1.5)
        
        # Test coordinates outside India
        with pytest.raises(ValueError, match="outside India boundaries"):
            ProcessedEvent(
                original_text="Test",
                lat=40.7128,  # New York coordinates
                lon=-74.0060
            )
    
    def test_coordinate_validation(self):
        """Test India boundary validation"""
        # Valid India coordinates
        event1 = ProcessedEvent(
            original_text="Test",
            lat=28.6139,  # New Delhi
            lon=77.2090
        )
        assert event1.lat == 28.6139
        
        # Valid coordinates at boundary
        event2 = ProcessedEvent(
            original_text="Test",
            lat=8.0,  # Southern India
            lon=77.0
        )
        assert event2.lat == 8.0
    
    def test_reality_score_calculation(self):
        """Test reality score calculation logic"""
        # Event with satellite data
        satellite = SatelliteResult(reality_score=0.3)
        event1 = ProcessedEvent(
            original_text="Test",
            satellite=satellite
        )
        assert event1.get_reality_score() == 0.3
        
        # Event with claims but no satellite data
        claim = Claim(text="Test claim", confidence=0.8)
        event2 = ProcessedEvent(
            original_text="Test",
            claims=[claim],
            satellite=SatelliteResult()  # Empty satellite data
        )
        reality_score = event2.get_reality_score()
        assert 0.0 <= reality_score <= 1.0
    
    def test_event_serialization(self):
        """Test event JSON serialization"""
        claim = Claim(text="Test claim", confidence=0.7)
        satellite = SatelliteResult(similarity=0.5, reality_score=0.6)
        
        original_event = ProcessedEvent(
            source=EventSource.TWITTER,
            original_text="Test tweet",
            region_hint="Maharashtra",
            claims=[claim],
            satellite=satellite,
            virality_score=0.8
        )
        
        # Test to_json
        json_str = original_event.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        restored_event = ProcessedEvent.from_json(json_str)
        assert restored_event.source == original_event.source
        assert restored_event.original_text == original_event.original_text
        assert restored_event.region_hint == original_event.region_hint
        assert len(restored_event.claims) == 1
        assert restored_event.claims[0].text == "Test claim"


class TestIndianStatesValidation:
    """Test cases for Indian states validation"""
    
    def test_valid_states(self):
        """Test validation of valid Indian states"""
        assert validate_indian_state("Maharashtra") == True
        assert validate_indian_state("maharashtra") == True
        assert validate_indian_state("MAHARASHTRA") == True
        assert validate_indian_state("Delhi") == True
        assert validate_indian_state("Tamil Nadu") == True
    
    def test_invalid_states(self):
        """Test validation of invalid states"""
        assert validate_indian_state("California") == False
        assert validate_indian_state("Texas") == False
        assert validate_indian_state("") == False
        assert validate_indian_state("NonExistentState") == False
    
    def test_state_normalization(self):
        """Test state name normalization"""
        assert normalize_state_name("maharashtra") == "Maharashtra"
        assert normalize_state_name("DELHI") == "Delhi"
        assert normalize_state_name("  tamil nadu  ") == "Tamil Nadu"
        assert normalize_state_name("InvalidState") == "InvalidState"  # Returns original
    
    def test_states_completeness(self):
        """Test that all major Indian states are included"""
        major_states = [
            "maharashtra", "uttar pradesh", "bihar", "west bengal", "madhya pradesh",
            "tamil nadu", "rajasthan", "karnataka", "gujarat", "andhra pradesh",
            "odisha", "telangana", "kerala", "jharkhand", "assam", "punjab",
            "chhattisgarh", "haryana", "delhi", "jammu and kashmir"
        ]
        
        for state in major_states:
            assert state in INDIAN_STATES, f"Missing state: {state}"


@pytest.fixture
def temp_db():
    """Fixture to create temporary SQLite database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestSQLiteDatabase:
    """Test cases for SQLite database operations"""
    
    @pytest.mark.asyncio
    async def test_database_initialization(self, temp_db):
        """Test database initialization"""
        db = SQLiteDatabase(temp_db)
        success = await db.initialize()
        
        assert success == True
        assert Path(temp_db).exists()
    
    @pytest.mark.asyncio
    async def test_event_insertion_and_retrieval(self, temp_db):
        """Test inserting and retrieving events"""
        db = SQLiteDatabase(temp_db)
        await db.initialize()
        
        # Create test event
        event = ProcessedEvent(
            source=EventSource.NEWS,
            original_text="Test news from Mumbai",
            region_hint="Maharashtra",
            lat=19.0760,
            lon=72.8777,
            virality_score=0.6
        )
        
        # Insert event
        success = await db.insert_event(event)
        assert success == True
        
        # Retrieve event
        retrieved = await db.get_event(event.event_id)
        assert retrieved is not None
        assert retrieved.original_text == "Test news from Mumbai"
        assert retrieved.region_hint == "Maharashtra"
        assert retrieved.virality_score == 0.6
    
    @pytest.mark.asyncio
    async def test_events_by_region(self, temp_db):
        """Test retrieving events by region"""
        db = SQLiteDatabase(temp_db)
        await db.initialize()
        
        # Insert events for different regions
        event1 = ProcessedEvent(
            original_text="News from Delhi",
            region_hint="Delhi",
            virality_score=0.5
        )
        event2 = ProcessedEvent(
            original_text="News from Mumbai",
            region_hint="Maharashtra",
            virality_score=0.7
        )
        event3 = ProcessedEvent(
            original_text="More news from Delhi",
            region_hint="Delhi",
            virality_score=0.3
        )
        
        await db.insert_event(event1)
        await db.insert_event(event2)
        await db.insert_event(event3)
        
        # Get events for Delhi
        delhi_events = await db.get_events_by_region("Delhi")
        assert len(delhi_events) == 2
        
        # Get events for Maharashtra
        mh_events = await db.get_events_by_region("Maharashtra")
        assert len(mh_events) == 1
        assert mh_events[0].original_text == "News from Mumbai"
    
    @pytest.mark.asyncio
    async def test_heatmap_data_generation(self, temp_db):
        """Test heatmap data aggregation"""
        db = SQLiteDatabase(temp_db)
        await db.initialize()
        
        # Insert test events
        events = [
            ProcessedEvent(
                original_text="Event 1",
                region_hint="Delhi",
                virality_score=0.8,
                satellite=SatelliteResult(reality_score=0.2)
            ),
            ProcessedEvent(
                original_text="Event 2",
                region_hint="Delhi",
                virality_score=0.6,
                satellite=SatelliteResult(reality_score=0.3)
            ),
            ProcessedEvent(
                original_text="Event 3",
                region_hint="Maharashtra",
                virality_score=0.4,
                satellite=SatelliteResult(reality_score=0.7)
            )
        ]
        
        for event in events:
            await db.insert_event(event)
        
        # Get heatmap data
        heatmap_data = await db.get_heatmap_data(hours_back=24)
        
        assert "Delhi" in heatmap_data
        assert "Maharashtra" in heatmap_data
        
        delhi_data = heatmap_data["Delhi"]
        assert delhi_data["event_count"] == 2
        assert 0.0 <= delhi_data["avg_virality_score"] <= 1.0
        assert 0.0 <= delhi_data["avg_reality_score"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_database_stats(self, temp_db):
        """Test database statistics generation"""
        db = SQLiteDatabase(temp_db)
        await db.initialize()
        
        # Insert test events
        events = [
            ProcessedEvent(original_text="News event", source=EventSource.NEWS),
            ProcessedEvent(original_text="Twitter event", source=EventSource.TWITTER),
            ProcessedEvent(original_text="Manual event", source=EventSource.MANUAL)
        ]
        
        for event in events:
            await db.insert_event(event)
        
        # Get stats
        stats = await db.get_stats()
        
        assert stats["total_events"] == 3
        assert stats["database_type"] == "sqlite"
        assert "events_by_source" in stats
        assert stats["events_by_source"]["news"] == 1
        assert stats["events_by_source"]["twitter"] == 1


class TestDatabaseManager:
    """Test cases for DatabaseManager factory"""
    
    def test_sqlite_creation(self):
        """Test SQLite database creation"""
        # Mock local mode
        os.environ["MODE"] = "local"
        
        db = DatabaseManager.create_database()
        assert isinstance(db, SQLiteDatabase)
    
    def test_config_integration(self):
        """Test integration with configuration system"""
        # Test local mode
        os.environ["MODE"] = "local"
        config_local = Config()
        assert config_local.is_local_mode() == True
        
        db_config = config_local.get_database_config()
        assert db_config.type == "sqlite"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])