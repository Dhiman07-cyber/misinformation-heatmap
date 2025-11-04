#!/usr/bin/env python3
"""
Basic test for API functionality
"""

import sys
import os
sys.path.append('backend')

# Set environment for local mode
os.environ["MODE"] = "local"

from fastapi.testclient import TestClient
from backend.api import app

def test_api_basic():
    """Test basic API functionality"""
    print("Testing API basic functionality...")
    
    client = TestClient(app)
    
    # Test root endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    print("✅ Root endpoint working")
    
    # Test health check
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    print("✅ Health check endpoint working")
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert schema["info"]["title"] == "Real-time Misinformation Heatmap API"
    print("✅ OpenAPI schema generation working")
    
    # Test docs endpoint
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    print("✅ Swagger docs endpoint working")
    
    # Test parameter validation
    response = client.get("/heatmap?hours_back=0")
    assert response.status_code == 422  # Validation error
    print("✅ Parameter validation working")
    
    response = client.get("/heatmap?hours_back=200")
    assert response.status_code == 422  # Validation error
    print("✅ Parameter range validation working")
    
    # Test invalid state
    response = client.get("/region/California")
    assert response.status_code in [400, 422]  # Should be validation error
    print("✅ State validation working")
    
    # Test invalid JSON for POST
    response = client.post("/ingest/test", json={})
    assert response.status_code == 422  # Missing required field
    print("✅ POST validation working")
    
    print("\n🎉 All basic API tests passed!")

if __name__ == "__main__":
    try:
        test_api_basic()
    except Exception as e:
        print(f"❌ API test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)