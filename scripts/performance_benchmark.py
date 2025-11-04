#!/usr/bin/env python3
"""
Performance benchmarking script for the misinformation heatmap application.
Tests API response times, database performance, and system resource usage.
"""

import asyncio
import json
import logging
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Tuple

import requests
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Performance benchmarking suite for the application."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.results = {}
        
    def benchmark_api_endpoints(self) -> Dict:
        """Benchmark API endpoint response times."""
        logger.info("Benchmarking API endpoints...")
        
        endpoints = [
            ("/health", "GET"),
            ("/heatmap", "GET"),
            ("/region/Maharashtra", "GET"),
            ("/api/info", "GET")
        ]
        
        results = {}
        
        for endpoint, method in endpoints:
            logger.info(f"Testing {method} {endpoint}")
            
            response_times = []
            success_count = 0
            
            # Run 50 requests per endpoint
            for i in range(50):
                start_time = time.time()
                
                try:
                    if method == "GET":
                        response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    else:
                        response = requests.request(method, f"{self.base_url}{endpoint}", timeout=10)
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000  # Convert to ms
                    
                    if response.status_code < 400:
                        response_times.append(response_time)
                        success_count += 1
                        
                except Exception as e:
                    logger.warning(f"Request failed: {e}")
                    
                # Small delay between requests
                time.sleep(0.1)
            
            if response_times:
                results[f"{method} {endpoint}"] = {
                    "avg_response_time_ms": round(statistics.mean(response_times), 2),
                    "min_response_time_ms": round(min(response_times), 2),
                    "max_response_time_ms": round(max(response_times), 2),
                    "p95_response_time_ms": round(statistics.quantiles(response_times, n=20)[18], 2),
                    "success_rate": round((success_count / 50) * 100, 2),
                    "total_requests": 50
                }
            else:
                results[f"{method} {endpoint}"] = {
                    "error": "All requests failed",
                    "success_rate": 0,
                    "total_requests": 50
                }
        
        return results
    
    def benchmark_concurrent_load(self) -> Dict:
        """Benchmark API under concurrent load."""
        logger.info("Benchmarking concurrent load...")
        
        def make_request():
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}/heatmap", timeout=10)
                end_time = time.time()
                
                return {
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "success": response.status_code < 400
                }
            except Exception as e:
                return {
                    "response_time": None,
                    "status_code": None,
                    "success": False,
                    "error": str(e)
                }
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        results = {}
        
        for concurrency in concurrency_levels:
            logger.info(f"Testing with {concurrency} concurrent requests")
            
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(make_request) for _ in range(concurrency * 10)]
                request_results = [future.result() for future in futures]
            
            end_time = time.time()
            
            # Analyze results
            successful_requests = [r for r in request_results if r["success"]]
            response_times = [r["response_time"] for r in successful_requests if r["response_time"]]
            
            results[f"concurrency_{concurrency}"] = {
                "total_requests": len(request_results),
                "successful_requests": len(successful_requests),
                "success_rate": round((len(successful_requests) / len(request_results)) * 100, 2),
                "total_time_seconds": round(end_time - start_time, 2),
                "requests_per_second": round(len(request_results) / (end_time - start_time), 2),
                "avg_response_time_ms": round(statistics.mean(response_times), 2) if response_times else None,
                "p95_response_time_ms": round(statistics.quantiles(response_times, n=20)[18], 2) if len(response_times) > 20 else None
            }
        
        return results
    
    def benchmark_data_ingestion(self) -> Dict:
        """Benchmark data ingestion performance."""
        logger.info("Benchmarking data ingestion...")
        
        test_payloads = [
            {
                "text": f"Test misinformation event {i} in Maharashtra with satellite validation.",
                "source": "manual",
                "location": "Maharashtra",
                "category": "test"
            }
            for i in range(20)
        ]
        
        ingestion_times = []
        success_count = 0
        
        for payload in test_payloads:
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.base_url}/ingest/test",
                    json=payload,
                    timeout=30
                )
                
                end_time = time.time()
                ingestion_time = (end_time - start_time) * 1000
                
                if response.status_code in [200, 201]:
                    ingestion_times.append(ingestion_time)
                    success_count += 1
                    
            except Exception as e:
                logger.warning(f"Ingestion request failed: {e}")
            
            time.sleep(0.5)  # Delay between ingestions
        
        if ingestion_times:
            return {
                "avg_ingestion_time_ms": round(statistics.mean(ingestion_times), 2),
                "min_ingestion_time_ms": round(min(ingestion_times), 2),
                "max_ingestion_time_ms": round(max(ingestion_times), 2),
                "success_rate": round((success_count / len(test_payloads)) * 100, 2),
                "total_events": len(test_payloads)
            }
        else:
            return {
                "error": "All ingestion requests failed",
                "success_rate": 0,
                "total_events": len(test_payloads)
            }
    
    def benchmark_system_resources(self) -> Dict:
        """Monitor system resource usage during testing."""
        logger.info("Monitoring system resources...")
        
        # Get initial readings
        initial_cpu = psutil.cpu_percent(interval=1)
        initial_memory = psutil.virtual_memory()
        initial_disk = psutil.disk_usage('/')
        
        # Run a load test while monitoring
        start_time = time.time()
        
        def load_test():
            for _ in range(100):
                try:
                    requests.get(f"{self.base_url}/heatmap", timeout=5)
                except:
                    pass
                time.sleep(0.1)
        
        # Monitor resources during load test
        cpu_readings = []
        memory_readings = []
        
        load_thread = ThreadPoolExecutor(max_workers=1)
        load_future = load_thread.submit(load_test)
        
        while not load_future.done():
            cpu_readings.append(psutil.cpu_percent())
            memory_readings.append(psutil.virtual_memory().percent)
            time.sleep(0.5)
        
        load_thread.shutdown()
        end_time = time.time()
        
        # Get final readings
        final_cpu = psutil.cpu_percent(interval=1)
        final_memory = psutil.virtual_memory()
        
        return {
            "test_duration_seconds": round(end_time - start_time, 2),
            "cpu_usage": {
                "initial_percent": initial_cpu,
                "final_percent": final_cpu,
                "avg_during_test": round(statistics.mean(cpu_readings), 2),
                "max_during_test": round(max(cpu_readings), 2)
            },
            "memory_usage": {
                "initial_percent": initial_memory.percent,
                "final_percent": final_memory.percent,
                "avg_during_test": round(statistics.mean(memory_readings), 2),
                "max_during_test": round(max(memory_readings), 2)
            },
            "disk_usage": {
                "total_gb": round(initial_disk.total / (1024**3), 2),
                "used_gb": round(initial_disk.used / (1024**3), 2),
                "free_gb": round(initial_disk.free / (1024**3), 2),
                "used_percent": round((initial_disk.used / initial_disk.total) * 100, 2)
            }
        }
    
    def run_all_benchmarks(self) -> Dict:
        """Run all performance benchmarks."""
        logger.info("Starting comprehensive performance benchmarks...")
        
        start_time = datetime.now()
        
        # Test API connectivity first
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code != 200:
                raise Exception(f"API health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Cannot connect to API: {e}")
            return {"error": "API not accessible", "details": str(e)}
        
        results = {
            "benchmark_info": {
                "start_time": start_time.isoformat(),
                "base_url": self.base_url,
                "system_info": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "python_version": sys.version
                }
            }
        }
        
        try:
            # Run individual benchmarks
            results["api_endpoints"] = self.benchmark_api_endpoints()
            results["concurrent_load"] = self.benchmark_concurrent_load()
            results["data_ingestion"] = self.benchmark_data_ingestion()
            results["system_resources"] = self.benchmark_system_resources()
            
            end_time = datetime.now()
            results["benchmark_info"]["end_time"] = end_time.isoformat()
            results["benchmark_info"]["total_duration_seconds"] = (end_time - start_time).total_seconds()
            
            # Generate performance summary
            results["summary"] = self.generate_performance_summary(results)
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def generate_performance_summary(self, results: Dict) -> Dict:
        """Generate a performance summary with pass/fail criteria."""
        summary = {
            "overall_status": "PASS",
            "issues": [],
            "recommendations": []
        }
        
        # Check API endpoint performance
        if "api_endpoints" in results:
            for endpoint, metrics in results["api_endpoints"].items():
                if "avg_response_time_ms" in metrics:
                    if metrics["avg_response_time_ms"] > 1000:  # 1 second threshold
                        summary["issues"].append(f"{endpoint} average response time is high: {metrics['avg_response_time_ms']}ms")
                        summary["overall_status"] = "FAIL"
                    
                    if metrics["success_rate"] < 95:  # 95% success rate threshold
                        summary["issues"].append(f"{endpoint} success rate is low: {metrics['success_rate']}%")
                        summary["overall_status"] = "FAIL"
        
        # Check concurrent load performance
        if "concurrent_load" in results:
            for test, metrics in results["concurrent_load"].items():
                if "success_rate" in metrics and metrics["success_rate"] < 90:
                    summary["issues"].append(f"Low success rate under {test}: {metrics['success_rate']}%")
                    summary["overall_status"] = "FAIL"
        
        # Check system resources
        if "system_resources" in results:
            cpu_max = results["system_resources"]["cpu_usage"]["max_during_test"]
            memory_max = results["system_resources"]["memory_usage"]["max_during_test"]
            
            if cpu_max > 80:
                summary["issues"].append(f"High CPU usage during testing: {cpu_max}%")
                summary["recommendations"].append("Consider optimizing CPU-intensive operations")
            
            if memory_max > 80:
                summary["issues"].append(f"High memory usage during testing: {memory_max}%")
                summary["recommendations"].append("Consider implementing memory optimization strategies")
        
        # Add general recommendations
        if summary["overall_status"] == "PASS":
            summary["recommendations"].extend([
                "Performance is within acceptable limits",
                "Consider implementing caching for frequently accessed data",
                "Monitor performance in production environment"
            ])
        
        return summary
    
    def save_results(self, results: Dict, filename: str = None) -> str:
        """Save benchmark results to a JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_benchmark_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to: {filename}")
        return filename


def main():
    """Main function to run performance benchmarks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance benchmark for misinformation heatmap")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run benchmarks
    benchmark = PerformanceBenchmark(base_url=args.url)
    results = benchmark.run_all_benchmarks()
    
    # Save results
    output_file = benchmark.save_results(results, args.output)
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("="*60)
    
    if "error" in results:
        print(f"❌ Benchmark failed: {results['error']}")
        sys.exit(1)
    
    summary = results.get("summary", {})
    status = summary.get("overall_status", "UNKNOWN")
    
    if status == "PASS":
        print("✅ Overall Status: PASS")
    else:
        print("❌ Overall Status: FAIL")
    
    if "issues" in summary and summary["issues"]:
        print(f"\n⚠️  Issues Found ({len(summary['issues'])}):")
        for issue in summary["issues"]:
            print(f"  - {issue}")
    
    if "recommendations" in summary and summary["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in summary["recommendations"]:
            print(f"  - {rec}")
    
    print(f"\n📊 Detailed results saved to: {output_file}")
    print("="*60)
    
    # Exit with appropriate code
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()