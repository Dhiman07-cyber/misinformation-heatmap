#!/usr/bin/env python3
"""
Health check script for the misinformation heatmap application.
Monitors service health and provides detailed status information.
"""

import argparse
import json
import logging
import requests
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Performs comprehensive health checks on application services."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 10):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results: Dict[str, Dict] = {}
        
    def check_api_health(self) -> Tuple[bool, Dict]:
        """Check backend API health."""
        logger.info("Checking backend API health...")
        
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                health_data = response.json()
                return True, {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "details": health_data
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "response_time_ms": round(response_time, 2),
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            return False, {
                "status": "unreachable",
                "error": "Connection refused - service may not be running"
            }
        except requests.exceptions.Timeout:
            return False, {
                "status": "timeout",
                "error": f"Request timed out after {self.timeout}s"
            }
        except Exception as e:
            return False, {
                "status": "error",
                "error": str(e)
            }
            
    def check_api_endpoints(self) -> Tuple[bool, Dict]:
        """Check critical API endpoints."""
        logger.info("Checking API endpoints...")
        
        endpoints = [
            ("/heatmap", "GET"),
            ("/region/Maharashtra", "GET"),
            ("/api/info", "GET")
        ]
        
        results = {}
        all_healthy = True
        
        for endpoint, method in endpoints:
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        timeout=self.timeout
                    )
                else:
                    response = requests.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        timeout=self.timeout
                    )
                    
                response_time = (time.time() - start_time) * 1000
                
                results[endpoint] = {
                    "status": "healthy" if response.status_code < 400 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time_ms": round(response_time, 2)
                }
                
                if response.status_code >= 400:
                    all_healthy = False
                    
            except Exception as e:
                results[endpoint] = {
                    "status": "error",
                    "error": str(e)
                }
                all_healthy = False
                
        return all_healthy, results
        
    def check_database_connectivity(self) -> Tuple[bool, Dict]:
        """Check database connectivity through API."""
        logger.info("Checking database connectivity...")
        
        try:
            # Try to get heatmap data which requires database access
            response = requests.get(
                f"{self.base_url}/heatmap",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return True, {
                    "status": "healthy",
                    "total_events": data.get("total_events", 0),
                    "states_count": len(data.get("states", {}))
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return False, {
                "status": "error",
                "error": str(e)
            }
            
    def check_nlp_service(self) -> Tuple[bool, Dict]:
        """Check NLP service functionality."""
        logger.info("Checking NLP service...")
        
        try:
            # Submit test data to check NLP processing
            test_data = {
                "text": "This is a test message for NLP processing in Maharashtra.",
                "source": "manual",
                "location": "Maharashtra"
            }
            
            response = requests.post(
                f"{self.base_url}/ingest/test",
                json=test_data,
                timeout=self.timeout * 2  # NLP processing may take longer
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                return True, {
                    "status": "healthy",
                    "processing_results": result.get("processing_results", {})
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return False, {
                "status": "error",
                "error": str(e)
            }
            
    def check_frontend_availability(self) -> Tuple[bool, Dict]:
        """Check frontend server availability."""
        logger.info("Checking frontend availability...")
        
        frontend_url = "http://localhost:3000"
        
        try:
            start_time = time.time()
            response = requests.get(frontend_url, timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return True, {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "content_length": len(response.content)
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "status_code": response.status_code
                }
                
        except requests.exceptions.ConnectionError:
            return False, {
                "status": "unreachable",
                "error": "Frontend server not running"
            }
        except Exception as e:
            return False, {
                "status": "error",
                "error": str(e)
            }
            
    def check_pubsub_emulator(self) -> Tuple[bool, Dict]:
        """Check Pub/Sub emulator (local mode only)."""
        logger.info("Checking Pub/Sub emulator...")
        
        pubsub_url = "http://localhost:8085"
        
        try:
            response = requests.get(pubsub_url, timeout=5)
            return True, {
                "status": "healthy",
                "emulator_running": True
            }
        except requests.exceptions.ConnectionError:
            return False, {
                "status": "unreachable",
                "error": "Pub/Sub emulator not running"
            }
        except Exception as e:
            return False, {
                "status": "error",
                "error": str(e)
            }
            
    def run_comprehensive_check(self) -> Dict:
        """Run all health checks and return comprehensive results."""
        logger.info("Starting comprehensive health check...")
        
        start_time = datetime.now()
        
        # Run all checks
        checks = [
            ("api_health", self.check_api_health),
            ("api_endpoints", self.check_api_endpoints),
            ("database", self.check_database_connectivity),
            ("nlp_service", self.check_nlp_service),
            ("frontend", self.check_frontend_availability),
            ("pubsub_emulator", self.check_pubsub_emulator)
        ]
        
        results = {}
        overall_healthy = True
        
        for check_name, check_func in checks:
            try:
                healthy, details = check_func()
                results[check_name] = {
                    "healthy": healthy,
                    **details
                }
                
                if not healthy:
                    overall_healthy = False
                    
            except Exception as e:
                results[check_name] = {
                    "healthy": False,
                    "status": "error",
                    "error": f"Check failed: {e}"
                }
                overall_healthy = False
                
        end_time = datetime.now()
        
        return {
            "timestamp": start_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "overall_healthy": overall_healthy,
            "checks": results,
            "summary": self._generate_summary(results)
        }
        
    def _generate_summary(self, results: Dict) -> Dict:
        """Generate a summary of health check results."""
        total_checks = len(results)
        healthy_checks = sum(1 for check in results.values() if check.get("healthy", False))
        
        critical_services = ["api_health", "database"]
        critical_healthy = all(
            results.get(service, {}).get("healthy", False) 
            for service in critical_services
        )
        
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "health_percentage": round((healthy_checks / total_checks) * 100, 1),
            "critical_services_healthy": critical_healthy,
            "status": "healthy" if critical_healthy else "degraded"
        }
        
    def print_results(self, results: Dict, format_type: str = "human") -> None:
        """Print health check results in specified format."""
        if format_type == "json":
            print(json.dumps(results, indent=2))
            return
            
        # Human-readable format
        print("\n" + "="*60)
        print("HEALTH CHECK RESULTS")
        print("="*60)
        
        summary = results["summary"]
        overall_status = "✅ HEALTHY" if results["overall_healthy"] else "❌ UNHEALTHY"
        
        print(f"Overall Status: {overall_status}")
        print(f"Timestamp: {results['timestamp']}")
        print(f"Duration: {results['duration_seconds']:.2f}s")
        print(f"Health Score: {summary['health_percentage']}% ({summary['healthy_checks']}/{summary['total_checks']})")
        
        print(f"\nDETAILED RESULTS:")
        print("-" * 40)
        
        for service, details in results["checks"].items():
            status_icon = "✅" if details["healthy"] else "❌"
            service_name = service.replace("_", " ").title()
            
            print(f"{status_icon} {service_name}")
            
            if "response_time_ms" in details:
                print(f"   Response Time: {details['response_time_ms']}ms")
                
            if "status" in details:
                print(f"   Status: {details['status']}")
                
            if "error" in details:
                print(f"   Error: {details['error']}")
                
            if service == "database" and "total_events" in details:
                print(f"   Total Events: {details['total_events']}")
                print(f"   States: {details['states_count']}")
                
            print()
            
        print("="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Health check for misinformation heatmap application"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL for the API server"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds"
    )
    parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        help="Output format"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous health checks"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Interval between continuous checks (seconds)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    checker = HealthChecker(base_url=args.url, timeout=args.timeout)
    
    try:
        if args.continuous:
            logger.info(f"Starting continuous health checks (interval: {args.interval}s)")
            while True:
                results = checker.run_comprehensive_check()
                checker.print_results(results, args.format)
                
                if not results["overall_healthy"]:
                    logger.warning("Health check failed - services may be degraded")
                    
                time.sleep(args.interval)
        else:
            results = checker.run_comprehensive_check()
            checker.print_results(results, args.format)
            
            # Exit with error code if unhealthy
            sys.exit(0 if results["overall_healthy"] else 1)
            
    except KeyboardInterrupt:
        logger.info("Health check interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()