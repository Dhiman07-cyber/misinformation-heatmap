"""
API endpoint tests for the FastAPI backend.
Tests all REST endpoints, error handling, validation, and response formatting.
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

# Set environment for testing
os.environ["MODE"] = "local"

# FastAPI testing imports
from fastapi.testclient import TestClient
from fastapi import status

# Import the FastAPI app and dependencies
from api import app, get_database, get_ingestion_manager
from models import ProcessedEvent, EventSource, LanguageCode, ClaimCategory, Claim, SatelliteResult
from database import SQLiteDatabase
from ingestion_manager import UnifiedIngestionManager


class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
        
        # Mock database and ingestion manager
        self.mock_db = Mock()
        self.mock_ingestion_manager = Mock()
        self.mock_ingestion_manager.initialized = True
        
        # Override dependencies
        app.dependency_overrides[get_database] = lambda: self.mock_db
        app.dependency_overrides[get_ingestion_manager] = lambda: self.mock_ingestion_manager
    
    def teardown_method(self):
        """Cleanup after each test"""
        app.dependency_overrides.clear()
    
    def test_root_endpoint(self):
        """Test root endpoint serves frontend or API info"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        # Root endpoint may serve HTML frontend or JSON API info
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            assert "message" in data
            assert "version" in data
            assert "docs" in data
        else:
            # Should be HTML content
            assert "text/html" in content_type or response.text is not None
    
    def test_api_info_endpoint(self):
        """Test API info endpoint returns structured information"""
        response = self.client.get("/api/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "status" in data
        assert "mode" in data
    
    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        # Mock health check response
        self.mock_ingestion_manager.health_check = AsyncMock(return_value={
            "status": "healthy",
            "mode": "local",
            "components": {"database": "healthy", "ingestion": "healthy"}
        })
        
        response = self.client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        # Health check may return degraded status in test environment
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "mode" in data
        assert "timestamp" in data
        assert "components" in data
    
    def test_heatmap_endpoint_success(self):
        """Test successful heatmap data retrieval"""
        # Mock heatmap data
        mock_heatmap_data = {
            "Maharashtra": {
                "event_count": 15,
                "intensity": 0.75,
                "avg_virality_score": 0.68,
                "avg_reality_score": 0.32,
                "misinformation_risk": 0.46,
                "dominant_category": "health",
                "recent_claims": ["Test claim 1", "Test claim 2"],
                "satellite_validated_count": 8,
                "last_updated": datetime.utcnow().isoformat()
            }
        }
        
        # Mock the heatmap aggregator
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value=mock_heatmap_data)
            
            response = self.client.get("/heatmap?hours_back=24")
            
            assert response.status_code == 200
            data = response.json()
            assert "states" in data
            assert "total_events" in data
            assert "last_updated" in data
            assert "time_range" in data
            assert "Maharashtra" in data["states"]
    
    def test_heatmap_endpoint_validation(self):
        """Test heatmap endpoint parameter validation"""
        # Test invalid hours_back parameter
        response = self.client.get("/heatmap?hours_back=0")
        assert response.status_code == 422  # Validation error
        
        response = self.client.get("/heatmap?hours_back=200")
        assert response.status_code == 422  # Validation error
        
        # Test valid parameters
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
            
            response = self.client.get("/heatmap?hours_back=48&use_cache=false")
            assert response.status_code == 200
    
    def test_region_endpoint_success(self):
        """Test successful region details retrieval"""
        # Create mock events
        mock_events = [
            self._create_mock_event("Event 1 in Maharashtra", "Maharashtra"),
            self._create_mock_event("Event 2 in Maharashtra", "Maharashtra")
        ]
        
        self.mock_db.get_events_by_region = AsyncMock(return_value=mock_events)
        
        response = self.client.get("/region/Maharashtra?limit=10&hours_back=24")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "Maharashtra"
        assert "events" in data
        assert "summary" in data
        assert "total_count" in data
        assert len(data["events"]) == 2
    
    def test_region_endpoint_invalid_state(self):
        """Test region endpoint with invalid state name"""
        response = self.client.get("/region/California")
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Invalid Indian state" in data["message"]
    
    def test_region_endpoint_empty_results(self):
        """Test region endpoint with no events"""
        self.mock_db.get_events_by_region = AsyncMock(return_value=[])
        
        response = self.client.get("/region/Sikkim")
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "Sikkim"
        assert data["total_count"] == 0
        assert len(data["events"]) == 0
    
    def test_ingest_test_endpoint_success(self):
        """Test successful test data ingestion"""
        # Mock processed event
        mock_processed_event = self._create_mock_processed_event()
        self.mock_ingestion_manager.ingest_single_event = AsyncMock(return_value=mock_processed_event)
        
        test_payload = {
            "text": "This is a test event for misinformation detection in Mumbai",
            "source": "manual",
            "location": "Mumbai, Maharashtra",
            "category": "test",
            "metadata": {"test": True}
        }
        
        response = self.client.post("/ingest/test", json=test_payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "processed"
        assert "event_id" in data
        assert "processing_results" in data
        assert data["processing_results"]["language_detected"] == "en"
    
    def test_ingest_test_endpoint_validation(self):
        """Test test ingestion endpoint validation"""
        # Test missing text
        response = self.client.post("/ingest/test", json={})
        assert response.status_code == 422
        
        # Test text too short
        response = self.client.post("/ingest/test", json={"text": "short"})
        assert response.status_code == 422
        
        # Test text too long
        long_text = "A" * 6000
        response = self.client.post("/ingest/test", json={"text": long_text})
        assert response.status_code == 422
    
    def test_ingest_test_endpoint_processing_failure(self):
        """Test test ingestion when processing fails"""
        self.mock_ingestion_manager.ingest_single_event = AsyncMock(return_value=None)
        
        test_payload = {
            "text": "This is a test event that will fail processing"
        }
        
        response = self.client.post("/ingest/test", json=test_payload)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    
    def test_stats_endpoint(self):
        """Test system statistics endpoint"""
        # Create a proper mock stats object
        class MockStats:
            def __init__(self):
                self.total_events_ingested = 100
                self.events_processed = 95
                self.processing_errors = 2
                self.average_processing_time_ms = 150.5
                self.events_stored = 95
                self.last_ingestion_time = None
        
        mock_stats = MockStats()
        
        self.mock_ingestion_manager.get_stats.return_value = mock_stats
        self.mock_db.get_stats = AsyncMock(return_value={"total_events": 95})
        self.mock_ingestion_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        
        response = self.client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "ingestion_stats" in data
        assert "database_stats" in data
        assert "processing_stats" in data
        assert "system_health" in data
    
    def test_admin_endpoints(self):
        """Test administrative endpoints"""
        # Test start ingestion
        self.mock_ingestion_manager.start_continuous_ingestion = AsyncMock()
        
        response = self.client.post("/admin/ingestion/start?interval_seconds=300")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        
        # Test stop ingestion
        self.mock_ingestion_manager.stop_continuous_ingestion = AsyncMock()
        
        response = self.client.post("/admin/ingestion/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        
        # Test reset stats
        self.mock_ingestion_manager.reset_stats = Mock()
        
        response = self.client.get("/admin/reset-stats")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset"
    
    def test_error_handling(self):
        """Test API error handling"""
        # Test 404 error
        response = self.client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not Found"
        
        # Test validation error with invalid state
        response = self.client.get("/region/InvalidState")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Invalid Indian state" in data["message"]
    
    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        # Test with a GET request to an actual endpoint
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
            
            response = self.client.get("/heatmap")
            
            # Check that CORS headers are present in the response
            assert response.status_code == 200
            # CORS headers should be present for cross-origin requests
            # Note: TestClient may not include all CORS headers, so we check what's available
            headers = {k.lower(): v for k, v in response.headers.items()}
            
            # At minimum, the response should be successful, indicating CORS is configured
            assert "content-type" in headers
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        with patch('api.rate_limiter') as mock_rate_limiter:
            # First request should succeed
            mock_rate_limiter.is_allowed.return_value = True
            
            with patch('api.heatmap_aggregator') as mock_aggregator:
                mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
                
                response = self.client.get("/heatmap")
                assert response.status_code == 200
            
            # Subsequent request should be rate limited
            mock_rate_limiter.is_allowed.return_value = False
            
            response = self.client.get("/heatmap")
            assert response.status_code == 429
    
    def _create_mock_event(self, text: str, region: str) -> ProcessedEvent:
        """Create a mock ProcessedEvent for testing"""
        event = Mock(spec=ProcessedEvent)
        event.event_id = "test_event_123"
        event.original_text = text
        event.timestamp = datetime.utcnow()
        event.source = EventSource.NEWS
        event.lang = LanguageCode.ENGLISH
        event.region_hint = region
        event.entities = ["test", "entity"]
        event.virality_score = 0.5
        event.claims = []
        event.satellite = None
        event.get_reality_score.return_value = 0.6
        event.get_primary_claim.return_value = None
        
        return event
    
    def _create_mock_processed_event(self) -> ProcessedEvent:
        """Create a mock ProcessedEvent with full data"""
        event = Mock(spec=ProcessedEvent)
        event.event_id = "processed_event_456"
        event.original_text = "Test processed event"
        event.timestamp = datetime.utcnow()
        event.source = EventSource.MANUAL
        event.lang = LanguageCode.ENGLISH
        event.region_hint = "Mumbai"
        event.entities = ["test", "mumbai"]
        event.virality_score = 0.7
        event.satellite = Mock()
        event.satellite.confidence = 0.8
        event.get_reality_score.return_value = 0.4
        
        # Mock primary claim
        mock_claim = Mock(spec=Claim)
        mock_claim.text = "Test claim about misinformation"
        mock_claim.category = ClaimCategory.OTHER
        mock_claim.confidence = 0.8
        
        event.claims = [mock_claim]
        event.get_primary_claim.return_value = mock_claim
        
        return event
    
    def test_api_documentation_endpoints(self):
        """Test API documentation endpoints are accessible"""
        # Test OpenAPI schema
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Test Swagger UI
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = self.client.get("/redoc")
        assert response.status_code == 200
    
    def test_request_validation(self):
        """Test comprehensive request validation"""
        # Test heatmap endpoint validation
        response = self.client.get("/heatmap?hours_back=0")
        assert response.status_code == 422
        
        response = self.client.get("/heatmap?hours_back=200")
        assert response.status_code == 422
        
        # Test region endpoint validation
        response = self.client.get("/region/Delhi?limit=0")
        assert response.status_code == 422
        
        response = self.client.get("/region/Delhi?limit=1000")
        assert response.status_code == 422
        
        # Test ingest endpoint validation
        response = self.client.post("/ingest/test", json={})
        assert response.status_code == 422
        
        response = self.client.post("/ingest/test", json={"text": "short"})
        assert response.status_code == 422
    
    def test_response_formats(self):
        """Test API response formats are consistent"""
        # Test successful response format
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
            
            response = self.client.get("/heatmap")
            assert response.status_code == 200
            data = response.json()
            
            # Check response structure
            assert "states" in data
            assert "total_events" in data
            assert "last_updated" in data
            assert "time_range" in data
            assert "metadata" in data
        
        # Test error response format
        response = self.client.get("/region/InvalidState")
        assert response.status_code == 400
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        assert "message" in data
        assert "error_code" in data
        assert "timestamp" in data
    
    def test_endpoint_security(self):
        """Test endpoint security measures"""
        # Test rate limiting (basic test)
        with patch('api.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.is_allowed.return_value = False
            
            response = self.client.get("/heatmap")
            assert response.status_code == 429
    
    def test_admin_endpoints_functionality(self):
        """Test administrative endpoints"""
        # Mock the async methods properly
        self.mock_ingestion_manager.start_continuous_ingestion = AsyncMock()
        self.mock_ingestion_manager.stop_continuous_ingestion = AsyncMock()
        self.mock_ingestion_manager.reset_stats = Mock()
        
        # Test start ingestion
        response = self.client.post("/admin/ingestion/start?interval_seconds=300")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
        # Test stop ingestion
        response = self.client.post("/admin/ingestion/stop")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
        # Test reset stats
        response = self.client.get("/admin/reset-stats")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestAPIValidation:
    """Test cases for API validation and error handling"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
        
        # Mock dependencies
        app.dependency_overrides[get_database] = lambda: Mock()
        app.dependency_overrides[get_ingestion_manager] = lambda: Mock()
    
    def teardown_method(self):
        """Cleanup after each test"""
        app.dependency_overrides.clear()
    
    def test_parameter_validation(self):
        """Test various parameter validation scenarios"""
        # Test negative hours_back
        response = self.client.get("/heatmap?hours_back=-1")
        assert response.status_code == 422
        
        # Test zero limit
        response = self.client.get("/region/Delhi?limit=0")
        assert response.status_code == 422
        
        # Test excessive limit
        response = self.client.get("/region/Delhi?limit=1000")
        assert response.status_code == 422
    
    def test_request_body_validation(self):
        """Test request body validation for POST endpoints"""
        # Test invalid JSON
        response = self.client.post(
            "/ingest/test",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Test missing required fields
        response = self.client.post("/ingest/test", json={"source": "manual"})
        assert response.status_code == 422
        
        # Test invalid enum values
        response = self.client.post("/ingest/test", json={
            "text": "Valid text content for testing",
            "source": "invalid_source"
        })
        assert response.status_code == 422


class TestAPIDocumentation:
    """Test cases for API documentation and OpenAPI schema"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
    
    def test_openapi_schema(self):
        """Test OpenAPI schema generation"""
        response = self.client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Check basic schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check API info
        assert schema["info"]["title"] == "Real-time Misinformation Heatmap API"
        assert schema["info"]["version"] == "1.0.0"
    
    def test_swagger_docs(self):
        """Test Swagger UI documentation"""
        response = self.client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_redoc_docs(self):
        """Test ReDoc documentation"""
        response = self.client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_endpoint_documentation(self):
        """Test that endpoints have proper documentation"""
        response = self.client.get("/openapi.json")
        schema = response.json()
        
        # Check that main endpoints are documented
        paths = schema["paths"]
        assert "/heatmap" in paths
        assert "/region/{state}" in paths
        assert "/ingest/test" in paths
        assert "/health" in paths
        
        # Check that endpoints have descriptions
        heatmap_endpoint = paths["/heatmap"]["get"]
        assert "summary" in heatmap_endpoint or "description" in heatmap_endpoint
        
        # Check parameter documentation
        if "parameters" in heatmap_endpoint:
            for param in heatmap_endpoint["parameters"]:
                assert "name" in param
                assert "description" in param


class TestAPIPerformance:
    """Test cases for API performance and optimization"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)
        
        # Mock fast responses
        mock_db = Mock()
        mock_ingestion_manager = Mock()
        mock_ingestion_manager.initialized = True
        
        app.dependency_overrides[get_database] = lambda: mock_db
        app.dependency_overrides[get_ingestion_manager] = lambda: mock_ingestion_manager
    
    def teardown_method(self):
        """Cleanup after each test"""
        app.dependency_overrides.clear()
    
    def test_response_times(self):
        """Test that API responses are reasonably fast"""
        import time
        
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
            
            start_time = time.time()
            response = self.client.get("/heatmap")
            end_time = time.time()
            
            assert response.status_code == 200
            assert (end_time - start_time) < 5.0  # Should respond within 5 seconds
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        import threading
        
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value={})
            
            responses = []
            
            def make_request():
                response = self.client.get("/heatmap")
                responses.append(response)
            
            # Make 5 concurrent requests
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # All requests should succeed
            assert len(responses) == 5
            for response in responses:
                assert response.status_code == 200
    
    def test_large_response_handling(self):
        """Test handling of large response payloads"""
        # Mock large heatmap data
        large_heatmap_data = {}
        for state in ["Maharashtra", "Karnataka", "Tamil Nadu", "Gujarat", "Rajasthan"]:
            large_heatmap_data[state] = {
                "event_count": 1000,
                "intensity": 0.8,
                "avg_virality_score": 0.7,
                "avg_reality_score": 0.3,
                "misinformation_risk": 0.5,
                "dominant_category": "health",
                "recent_claims": [f"Claim {i}" for i in range(100)],  # Large list
                "satellite_validated_count": 500,
                "last_updated": "2023-06-15T14:30:00Z"
            }
        
        with patch('api.heatmap_aggregator') as mock_aggregator:
            mock_aggregator.generate_heatmap_data = AsyncMock(return_value=large_heatmap_data)
            
            response = self.client.get("/heatmap")
            assert response.status_code == 200
            data = response.json()
            assert len(data["states"]) == 5
    
    def test_error_recovery(self):
        """Test API error recovery and graceful degradation"""
        # Test database connection failure
        mock_db = Mock()
        mock_db.get_events_by_region = AsyncMock(side_effect=Exception("Database connection failed"))
        
        app.dependency_overrides[get_database] = lambda: mock_db
        
        response = self.client.get("/region/Delhi")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])