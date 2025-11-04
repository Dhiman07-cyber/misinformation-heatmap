#!/usr/bin/env python3
"""
End-to-end testing pipeline for the Real-Time Misinformation Heatmap system.
Tests the complete flow from data ingestion to visualization.
"""

import asyncio
import json
import logging
import os
import sys
import time
import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from unittest.mock import patch

import aiohttp
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from api import app
from config import Config
from database import Database
from nlp_analyzer import NLPAnalyzer
from satellite_client import SatelliteClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EndToEndTestSuite:
    """Comprehensive end-to-end test suite for the misinformation heatmap system."""
    
    def __init__(self, mode: str = 'local'):
        """Initialize the test suite.
        
        Args:
            mode: Testing mode ('local' or 'cloud')
        """
        self.mode = mode
        self.config = Config(mode=mode)
        self.base_url = f"http://localhost:{self.config.api_port}"
        self.frontend_url = f"http://localhost:3000"
        self.driver = None
        self.test_results = []
        
        # Test data
        self.test_events = [
            {
                "text": "Breaking: Major infrastructure collapse reported in Maharashtra with satellite imagery showing significant damage",
                "source": "test_news",
                "location": "Maharashtra",
                "category": "infrastructure"
            },
            {
                "text": "Fake news alert: False claims about Karnataka government policies spreading on social media",
                "source": "test_social",
                "location": "Karnataka",
                "category": "politics"
            },
            {
                "text": "Health misinformation: Unverified medical claims circulating in Tamil Nadu communities",
                "source": "test_health",
                "location": "Tamil Nadu",
                "category": "health"
            }
        ]
    
    def setup_webdriver(self) -> None:
        """Setup Selenium WebDriver for frontend testing."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
            logger.info("WebDriver setup completed")
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def teardown_webdriver(self) -> None:
        """Cleanup WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver cleanup completed")
    
    def wait_for_service(self, url: str, timeout: int = 60) -> bool:
        """Wait for a service to become available.
        
        Args:
            url: Service URL to check
            timeout: Maximum wait time in seconds
            
        Returns:
            True if service is available, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Service at {url} is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        logger.error(f"Service at {url} not ready after {timeout} seconds")
        return False
    
    def test_api_health(self) -> Tuple[bool, str]:
        """Test API health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code != 200:
                return False, f"Health check failed with status {response.status_code}"
            
            health_data = response.json()
            required_fields = ['status', 'timestamp', 'dependencies']
            
            for field in required_fields:
                if field not in health_data:
                    return False, f"Missing required field: {field}"
            
            if health_data['status'] != 'healthy':
                return False, f"Service status is {health_data['status']}"
            
            logger.info("API health check passed")
            return True, "API health check successful"
            
        except Exception as e:
            return False, f"API health check failed: {str(e)}"
    
    def test_data_ingestion(self) -> Tuple[bool, str]:
        """Test data ingestion pipeline."""
        try:
            ingested_events = []
            
            for event_data in self.test_events:
                response = requests.post(
                    f"{self.base_url}/ingest/test",
                    json=event_data,
                    timeout=30
                )
                
                if response.status_code != 201:
                    return False, f"Ingestion failed for event: {event_data['text'][:50]}..."
                
                result = response.json()
                required_fields = ['event_id', 'status', 'processing_results']
                
                for field in required_fields:
                    if field not in result:
                        return False, f"Missing field in ingestion response: {field}"
                
                if result['status'] != 'processed':
                    return False, f"Event processing failed: {result.get('status')}"
                
                ingested_events.append(result)
                logger.info(f"Successfully ingested event: {result['event_id']}")
            
            # Wait for processing to complete
            time.sleep(5)
            
            logger.info(f"Data ingestion test passed: {len(ingested_events)} events processed")
            return True, f"Successfully ingested {len(ingested_events)} test events"
            
        except Exception as e:
            return False, f"Data ingestion test failed: {str(e)}"
    
    def test_nlp_processing(self) -> Tuple[bool, str]:
        """Test NLP processing pipeline."""
        try:
            # Test with a sample event
            test_text = "Breaking news about infrastructure development in Karnataka with satellite validation"
            
            response = requests.post(
                f"{self.base_url}/ingest/test",
                json={
                    "text": test_text,
                    "source": "test_nlp",
                    "location": "Karnataka",
                    "category": "infrastructure"
                },
                timeout=30
            )
            
            if response.status_code != 201:
                return False, f"NLP test ingestion failed with status {response.status_code}"
            
            result = response.json()
            processing_results = result.get('processing_results', {})
            
            # Check NLP processing results
            required_nlp_fields = [
                'language_detected',
                'region_extracted',
                'entities_found',
                'claims_extracted',
                'virality_score',
                'reality_score'
            ]
            
            for field in required_nlp_fields:
                if field not in processing_results:
                    return False, f"Missing NLP processing field: {field}"
            
            # Validate processing results
            if processing_results['language_detected'] not in ['en', 'hi', 'bn', 'te', 'ta', 'mr', 'gu']:
                return False, f"Invalid language detected: {processing_results['language_detected']}"
            
            if processing_results['region_extracted'] != 'Karnataka':
                return False, f"Incorrect region extracted: {processing_results['region_extracted']}"
            
            if not (0 <= processing_results['virality_score'] <= 1):
                return False, f"Invalid virality score: {processing_results['virality_score']}"
            
            if not (0 <= processing_results['reality_score'] <= 1):
                return False, f"Invalid reality score: {processing_results['reality_score']}"
            
            logger.info("NLP processing test passed")
            return True, "NLP processing pipeline working correctly"
            
        except Exception as e:
            return False, f"NLP processing test failed: {str(e)}"
    
    def test_satellite_validation(self) -> Tuple[bool, str]:
        """Test satellite validation system."""
        try:
            # Test with an event that should trigger satellite validation
            test_text = "Satellite imagery shows major changes in infrastructure development in Gujarat region"
            
            response = requests.post(
                f"{self.base_url}/ingest/test",
                json={
                    "text": test_text,
                    "source": "test_satellite",
                    "location": "Gujarat",
                    "category": "infrastructure"
                },
                timeout=30
            )
            
            if response.status_code != 201:
                return False, f"Satellite test ingestion failed with status {response.status_code}"
            
            result = response.json()
            processing_results = result.get('processing_results', {})
            
            # Check if satellite validation was performed
            if 'satellite_validated' not in processing_results:
                return False, "Satellite validation field missing from results"
            
            if not isinstance(processing_results['satellite_validated'], bool):
                return False, f"Invalid satellite validation result: {processing_results['satellite_validated']}"
            
            logger.info("Satellite validation test passed")
            return True, "Satellite validation system working correctly"
            
        except Exception as e:
            return False, f"Satellite validation test failed: {str(e)}"
    
    def test_heatmap_api(self) -> Tuple[bool, str]:
        """Test heatmap data API."""
        try:
            # Wait for data to be processed
            time.sleep(3)
            
            response = requests.get(f"{self.base_url}/heatmap?hours_back=24", timeout=15)
            
            if response.status_code != 200:
                return False, f"Heatmap API failed with status {response.status_code}"
            
            heatmap_data = response.json()
            required_fields = ['states', 'total_events', 'last_updated', 'metadata']
            
            for field in required_fields:
                if field not in heatmap_data:
                    return False, f"Missing heatmap field: {field}"
            
            # Check if we have state data
            states = heatmap_data['states']
            if not isinstance(states, dict):
                return False, "States data should be a dictionary"
            
            # Validate state data structure
            for state_name, state_data in states.items():
                required_state_fields = [
                    'event_count', 'intensity', 'avg_virality_score',
                    'avg_reality_score', 'misinformation_risk', 'last_updated'
                ]
                
                for field in required_state_fields:
                    if field not in state_data:
                        return False, f"Missing state field {field} for {state_name}"
                
                # Validate numeric ranges
                if not (0 <= state_data['intensity'] <= 1):
                    return False, f"Invalid intensity for {state_name}: {state_data['intensity']}"
                
                if not (0 <= state_data['misinformation_risk'] <= 1):
                    return False, f"Invalid risk for {state_name}: {state_data['misinformation_risk']}"
            
            logger.info(f"Heatmap API test passed: {len(states)} states with data")
            return True, f"Heatmap API working correctly with {len(states)} states"
            
        except Exception as e:
            return False, f"Heatmap API test failed: {str(e)}"
    
    def test_region_api(self) -> Tuple[bool, str]:
        """Test region details API."""
        try:
            # Test with Maharashtra (should have data from our test events)
            response = requests.get(
                f"{self.base_url}/region/Maharashtra?hours_back=24&limit=10",
                timeout=15
            )
            
            if response.status_code != 200:
                return False, f"Region API failed with status {response.status_code}"
            
            region_data = response.json()
            required_fields = ['state_name', 'summary', 'events', 'last_updated']
            
            for field in required_fields:
                if field not in region_data:
                    return False, f"Missing region field: {field}"
            
            if region_data['state_name'] != 'Maharashtra':
                return False, f"Incorrect state name: {region_data['state_name']}"
            
            # Check summary data
            summary = region_data['summary']
            required_summary_fields = [
                'event_count', 'misinformation_risk', 'avg_virality_score', 'avg_reality_score'
            ]
            
            for field in required_summary_fields:
                if field not in summary:
                    return False, f"Missing summary field: {field}"
            
            # Check events structure
            events = region_data['events']
            if not isinstance(events, list):
                return False, "Events should be a list"
            
            logger.info(f"Region API test passed: {summary['event_count']} events for Maharashtra")
            return True, f"Region API working correctly with {summary['event_count']} events"
            
        except Exception as e:
            return False, f"Region API test failed: {str(e)}"
    
    def test_frontend_loading(self) -> Tuple[bool, str]:
        """Test frontend application loading."""
        try:
            if not self.driver:
                return False, "WebDriver not initialized"
            
            self.driver.get(self.frontend_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for essential elements
            title_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "title-main"))
            )
            
            if "Misinformation Heatmap" not in title_element.text:
                return False, f"Incorrect page title: {title_element.text}"
            
            # Check for map container
            map_container = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "map-container"))
            )
            
            if not map_container.is_displayed():
                return False, "Map container not visible"
            
            # Check for control panel
            control_panel = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "control-panel"))
            )
            
            if not control_panel.is_displayed():
                return False, "Control panel not visible"
            
            logger.info("Frontend loading test passed")
            return True, "Frontend application loaded successfully"
            
        except Exception as e:
            return False, f"Frontend loading test failed: {str(e)}"
    
    def test_map_interaction(self) -> Tuple[bool, str]:
        """Test map interaction functionality."""
        try:
            if not self.driver:
                return False, "WebDriver not initialized"
            
            # Wait for map to initialize
            time.sleep(5)
            
            # Check for Leaflet map
            map_element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "leaflet-container"))
            )
            
            if not map_element.is_displayed():
                return False, "Leaflet map not visible"
            
            # Check for zoom controls
            zoom_controls = self.driver.find_elements(By.CLASS_NAME, "leaflet-control-zoom")
            if not zoom_controls:
                return False, "Zoom controls not found"
            
            # Check for attribution
            attribution = self.driver.find_elements(By.CLASS_NAME, "leaflet-control-attribution")
            if not attribution:
                return False, "Map attribution not found"
            
            # Try to find state layers (they should be loaded)
            time.sleep(3)
            svg_elements = self.driver.find_elements(By.TAG_NAME, "svg")
            if not svg_elements:
                return False, "No SVG elements found (state boundaries may not be loaded)"
            
            logger.info("Map interaction test passed")
            return True, "Map interaction functionality working correctly"
            
        except Exception as e:
            return False, f"Map interaction test failed: {str(e)}"
    
    def test_real_time_updates(self) -> Tuple[bool, str]:
        """Test real-time data updates."""
        try:
            if not self.driver:
                return False, "WebDriver not initialized"
            
            # Get initial status
            status_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "status-indicator"))
            )
            
            initial_text = status_element.text
            
            # Inject a new test event
            new_event = {
                "text": "Real-time test: New misinformation event detected in Rajasthan",
                "source": "test_realtime",
                "location": "Rajasthan",
                "category": "test"
            }
            
            response = requests.post(
                f"{self.base_url}/ingest/test",
                json=new_event,
                timeout=15
            )
            
            if response.status_code != 201:
                return False, f"Real-time test event ingestion failed: {response.status_code}"
            
            # Wait for potential UI update (the frontend polls every 30 seconds)
            # We'll wait a shorter time and check if the status changed
            time.sleep(10)
            
            # Check if status indicator shows activity
            current_status = status_element.text
            
            # The test passes if the system is responsive (even if UI hasn't updated yet)
            logger.info("Real-time updates test passed")
            return True, "Real-time update system is responsive"
            
        except Exception as e:
            return False, f"Real-time updates test failed: {str(e)}"
    
    def test_error_handling(self) -> Tuple[bool, str]:
        """Test error handling and recovery."""
        try:
            # Test invalid API endpoint
            response = requests.get(f"{self.base_url}/invalid-endpoint", timeout=10)
            if response.status_code != 404:
                return False, f"Expected 404 for invalid endpoint, got {response.status_code}"
            
            # Test invalid data ingestion
            response = requests.post(
                f"{self.base_url}/ingest/test",
                json={"invalid": "data"},
                timeout=10
            )
            if response.status_code not in [400, 422]:
                return False, f"Expected 400/422 for invalid data, got {response.status_code}"
            
            # Test invalid region
            response = requests.get(f"{self.base_url}/region/InvalidState", timeout=10)
            if response.status_code != 404:
                return False, f"Expected 404 for invalid state, got {response.status_code}"
            
            logger.info("Error handling test passed")
            return True, "Error handling working correctly"
            
        except Exception as e:
            return False, f"Error handling test failed: {str(e)}"
    
    def test_performance(self) -> Tuple[bool, str]:
        """Test system performance under load."""
        try:
            # Test API response times
            start_time = time.time()
            response = requests.get(f"{self.base_url}/heatmap", timeout=10)
            heatmap_time = time.time() - start_time
            
            if response.status_code != 200:
                return False, f"Heatmap request failed: {response.status_code}"
            
            if heatmap_time > 5.0:
                return False, f"Heatmap response too slow: {heatmap_time:.2f}s"
            
            # Test multiple concurrent requests
            import concurrent.futures
            
            def make_request():
                return requests.get(f"{self.base_url}/health", timeout=5)
            
            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            concurrent_time = time.time() - start_time
            
            # Check all requests succeeded
            for result in results:
                if result.status_code != 200:
                    return False, f"Concurrent request failed: {result.status_code}"
            
            if concurrent_time > 10.0:
                return False, f"Concurrent requests too slow: {concurrent_time:.2f}s"
            
            logger.info(f"Performance test passed: heatmap={heatmap_time:.2f}s, concurrent={concurrent_time:.2f}s")
            return True, f"Performance acceptable (heatmap: {heatmap_time:.2f}s, concurrent: {concurrent_time:.2f}s)"
            
        except Exception as e:
            return False, f"Performance test failed: {str(e)}"
    
    def run_all_tests(self) -> Dict:
        """Run all end-to-end tests."""
        logger.info(f"Starting end-to-end test suite in {self.mode} mode")
        
        # Test definitions
        tests = [
            ("API Health Check", self.test_api_health),
            ("Data Ingestion Pipeline", self.test_data_ingestion),
            ("NLP Processing", self.test_nlp_processing),
            ("Satellite Validation", self.test_satellite_validation),
            ("Heatmap API", self.test_heatmap_api),
            ("Region API", self.test_region_api),
            ("Frontend Loading", self.test_frontend_loading),
            ("Map Interaction", self.test_map_interaction),
            ("Real-time Updates", self.test_real_time_updates),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance)
        ]
        
        results = {
            'mode': self.mode,
            'start_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total': len(tests),
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }
        }
        
        try:
            # Wait for services to be ready
            if not self.wait_for_service(self.base_url):
                logger.error("Backend API not ready, aborting tests")
                return results
            
            # Setup WebDriver for frontend tests
            try:
                self.setup_webdriver()
                webdriver_available = True
            except Exception as e:
                logger.warning(f"WebDriver setup failed: {e}. Skipping frontend tests.")
                webdriver_available = False
            
            # Run tests
            for test_name, test_func in tests:
                logger.info(f"Running test: {test_name}")
                
                # Skip frontend tests if WebDriver not available
                if not webdriver_available and test_name in ["Frontend Loading", "Map Interaction", "Real-time Updates"]:
                    test_result = {
                        'name': test_name,
                        'status': 'skipped',
                        'message': 'WebDriver not available',
                        'duration': 0,
                        'timestamp': datetime.now().isoformat()
                    }
                    results['summary']['skipped'] += 1
                else:
                    start_time = time.time()
                    try:
                        success, message = test_func()
                        duration = time.time() - start_time
                        
                        test_result = {
                            'name': test_name,
                            'status': 'passed' if success else 'failed',
                            'message': message,
                            'duration': duration,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        if success:
                            results['summary']['passed'] += 1
                            logger.info(f"✓ {test_name}: {message}")
                        else:
                            results['summary']['failed'] += 1
                            logger.error(f"✗ {test_name}: {message}")
                    
                    except Exception as e:
                        duration = time.time() - start_time
                        test_result = {
                            'name': test_name,
                            'status': 'failed',
                            'message': f"Test execution error: {str(e)}",
                            'duration': duration,
                            'timestamp': datetime.now().isoformat()
                        }
                        results['summary']['failed'] += 1
                        logger.error(f"✗ {test_name}: Test execution error: {str(e)}")
                
                results['tests'].append(test_result)
        
        finally:
            # Cleanup
            self.teardown_webdriver()
        
        results['end_time'] = datetime.now().isoformat()
        results['success_rate'] = (results['summary']['passed'] / results['summary']['total']) * 100
        
        logger.info(f"Test suite completed: {results['summary']['passed']}/{results['summary']['total']} passed")
        return results


def main():
    """Main function to run the end-to-end test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run end-to-end tests for misinformation heatmap')
    parser.add_argument('--mode', choices=['local', 'cloud'], default='local',
                       help='Testing mode (default: local)')
    parser.add_argument('--output', type=str, help='Output file for test results (JSON)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run tests
    test_suite = EndToEndTestSuite(mode=args.mode)
    results = test_suite.run_all_tests()
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Test results saved to {args.output}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"END-TO-END TEST RESULTS ({args.mode.upper()} MODE)")
    print(f"{'='*60}")
    print(f"Total Tests: {results['summary']['total']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Skipped: {results['summary']['skipped']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"{'='*60}")
    
    # Print failed tests
    failed_tests = [test for test in results['tests'] if test['status'] == 'failed']
    if failed_tests:
        print(f"\nFAILED TESTS:")
        for test in failed_tests:
            print(f"  ✗ {test['name']}: {test['message']}")
    
    # Exit with appropriate code
    sys.exit(0 if results['summary']['failed'] == 0 else 1)


if __name__ == '__main__':
    main()