#!/usr/bin/env python3
"""
Performance optimization module for the Real-Time Misinformation Heatmap system.
Implements caching, query optimization, and monitoring capabilities.
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from collections import defaultdict, deque
import threading
from dataclasses import dataclass, asdict

# Performance monitoring
import psutil
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    active_connections: int
    cache_hit_rate: float
    avg_response_time: float
    requests_per_second: float
    error_rate: float
    database_query_time: float
    nlp_processing_time: float
    satellite_validation_time: float


class MemoryCache:
    """In-memory cache with TTL and size limits."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """Initialize cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = {}
        self._access_times = {}
        self._expiry_times = {}
        self._lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _cleanup_expired(self):
        """Remove expired items from cache."""
        now = time.time()
        expired_keys = [
            key for key, expiry in self._expiry_times.items()
            if expiry < now
        ]
        
        for key in expired_keys:
            self._remove_item(key)
    
    def _remove_item(self, key: str):
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]
            del self._access_times[key]
            del self._expiry_times[key]
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
        self._remove_item(lru_key)
        self.evictions += 1
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            self._cleanup_expired()
            
            if key in self._cache:
                self._access_times[key] = time.time()
                self.hits += 1
                return self._cache[key]
            
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set item in cache."""
        with self._lock:
            self._cleanup_expired()
            
            # Evict items if cache is full
            while len(self._cache) >= self.max_size:
                self._evict_lru()
            
            ttl = ttl or self.default_ttl
            now = time.time()
            
            self._cache[key] = value
            self._access_times[key] = now
            self._expiry_times[key] = now + ttl
    
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self._lock:
            if key in self._cache:
                self._remove_item(key)
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._expiry_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests) if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate,
                'memory_usage_mb': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage of cache in MB."""
        try:
            import sys
            total_size = 0
            for key, value in self._cache.items():
                total_size += sys.getsizeof(key) + sys.getsizeof(value)
            return total_size / (1024 * 1024)  # Convert to MB
        except:
            return 0.0


class QueryOptimizer:
    """Database query optimization utilities."""
    
    def __init__(self):
        self.query_stats = defaultdict(list)
        self.slow_query_threshold = 1.0  # seconds
        self._lock = threading.Lock()
    
    def record_query(self, query_type: str, duration: float, params: Dict = None):
        """Record query execution time."""
        with self._lock:
            self.query_stats[query_type].append({
                'duration': duration,
                'timestamp': datetime.now(),
                'params': params or {}
            })
            
            # Keep only recent queries (last 1000)
            if len(self.query_stats[query_type]) > 1000:
                self.query_stats[query_type] = self.query_stats[query_type][-1000:]
    
    def get_slow_queries(self) -> List[Dict]:
        """Get queries that exceed the slow query threshold."""
        slow_queries = []
        
        with self._lock:
            for query_type, queries in self.query_stats.items():
                for query in queries:
                    if query['duration'] > self.slow_query_threshold:
                        slow_queries.append({
                            'type': query_type,
                            'duration': query['duration'],
                            'timestamp': query['timestamp'],
                            'params': query['params']
                        })
        
        return sorted(slow_queries, key=lambda x: x['duration'], reverse=True)
    
    def get_query_stats(self) -> Dict[str, Dict]:
        """Get aggregated query statistics."""
        stats = {}
        
        with self._lock:
            for query_type, queries in self.query_stats.items():
                if not queries:
                    continue
                
                durations = [q['duration'] for q in queries]
                stats[query_type] = {
                    'count': len(queries),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'slow_queries': len([d for d in durations if d > self.slow_query_threshold])
                }
        
        return stats
    
    def optimize_heatmap_query(self, hours_back: int = 24) -> str:
        """Generate optimized heatmap query."""
        # Use indexed timestamp column and limit results
        return f"""
        SELECT 
            region_hint as state,
            COUNT(*) as event_count,
            AVG(virality_score) as avg_virality,
            AVG(reality_score) as avg_reality,
            AVG(misinformation_risk) as avg_risk,
            MAX(timestamp) as last_updated
        FROM events 
        WHERE timestamp >= datetime('now', '-{hours_back} hours')
            AND region_hint IS NOT NULL
        GROUP BY region_hint
        ORDER BY event_count DESC
        LIMIT 50
        """
    
    def optimize_region_query(self, state: str, hours_back: int = 24, limit: int = 50) -> str:
        """Generate optimized region query."""
        return f"""
        SELECT *
        FROM events 
        WHERE region_hint = ? 
            AND timestamp >= datetime('now', '-{hours_back} hours')
        ORDER BY timestamp DESC, misinformation_risk DESC
        LIMIT {limit}
        """


class PerformanceMonitor:
    """System performance monitoring."""
    
    def __init__(self, history_size: int = 1000):
        """Initialize performance monitor.
        
        Args:
            history_size: Number of metrics to keep in history
        """
        self.history_size = history_size
        self.metrics_history = deque(maxlen=history_size)
        self.request_times = deque(maxlen=1000)
        self.error_count = 0
        self.request_count = 0
        self._lock = threading.Lock()
        
        # Component timing
        self.component_times = {
            'database': deque(maxlen=100),
            'nlp': deque(maxlen=100),
            'satellite': deque(maxlen=100)
        }
    
    def record_request(self, duration: float, error: bool = False):
        """Record API request metrics."""
        with self._lock:
            self.request_times.append(duration)
            self.request_count += 1
            if error:
                self.error_count += 1
    
    def record_component_time(self, component: str, duration: float):
        """Record component processing time."""
        if component in self.component_times:
            with self._lock:
                self.component_times[component].append(duration)
    
    def collect_metrics(self, cache: MemoryCache) -> PerformanceMetrics:
        """Collect current performance metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_mb = memory.used / (1024 * 1024)
        
        # Network connections (approximate)
        try:
            connections = len(psutil.net_connections())
        except:
            connections = 0
        
        # Cache metrics
        cache_stats = cache.get_stats()
        cache_hit_rate = cache_stats['hit_rate']
        
        # Request metrics
        with self._lock:
            if self.request_times:
                avg_response_time = sum(self.request_times) / len(self.request_times)
            else:
                avg_response_time = 0.0
            
            # Calculate RPS over last minute
            now = time.time()
            recent_requests = len([t for t in self.request_times if now - t < 60])
            requests_per_second = recent_requests / 60.0
            
            # Error rate
            if self.request_count > 0:
                error_rate = self.error_count / self.request_count
            else:
                error_rate = 0.0
            
            # Component times
            db_time = sum(self.component_times['database']) / len(self.component_times['database']) if self.component_times['database'] else 0.0
            nlp_time = sum(self.component_times['nlp']) / len(self.component_times['nlp']) if self.component_times['nlp'] else 0.0
            satellite_time = sum(self.component_times['satellite']) / len(self.component_times['satellite']) if self.component_times['satellite'] else 0.0
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_mb,
            active_connections=connections,
            cache_hit_rate=cache_hit_rate,
            avg_response_time=avg_response_time,
            requests_per_second=requests_per_second,
            error_rate=error_rate,
            database_query_time=db_time,
            nlp_processing_time=nlp_time,
            satellite_validation_time=satellite_time
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_metrics_summary(self, minutes: int = 10) -> Dict[str, Any]:
        """Get performance metrics summary for the last N minutes."""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        return {
            'period_minutes': minutes,
            'sample_count': len(recent_metrics),
            'avg_cpu_percent': sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics),
            'avg_memory_percent': sum(m.memory_percent for m in recent_metrics) / len(recent_metrics),
            'avg_memory_mb': sum(m.memory_mb for m in recent_metrics) / len(recent_metrics),
            'avg_response_time': sum(m.avg_response_time for m in recent_metrics) / len(recent_metrics),
            'avg_requests_per_second': sum(m.requests_per_second for m in recent_metrics) / len(recent_metrics),
            'avg_error_rate': sum(m.error_rate for m in recent_metrics) / len(recent_metrics),
            'avg_cache_hit_rate': sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics),
            'max_cpu_percent': max(m.cpu_percent for m in recent_metrics),
            'max_memory_percent': max(m.memory_percent for m in recent_metrics),
            'max_response_time': max(m.avg_response_time for m in recent_metrics)
        }
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health and return status."""
        if not self.metrics_history:
            return {'status': 'unknown', 'message': 'No metrics available'}
        
        latest = self.metrics_history[-1]
        issues = []
        
        # Check CPU usage
        if latest.cpu_percent > 80:
            issues.append(f"High CPU usage: {latest.cpu_percent:.1f}%")
        
        # Check memory usage
        if latest.memory_percent > 85:
            issues.append(f"High memory usage: {latest.memory_percent:.1f}%")
        
        # Check response time
        if latest.avg_response_time > 2.0:
            issues.append(f"Slow response time: {latest.avg_response_time:.2f}s")
        
        # Check error rate
        if latest.error_rate > 0.05:  # 5%
            issues.append(f"High error rate: {latest.error_rate:.1%}")
        
        # Check cache hit rate
        if latest.cache_hit_rate < 0.5:  # 50%
            issues.append(f"Low cache hit rate: {latest.cache_hit_rate:.1%}")
        
        if not issues:
            return {
                'status': 'healthy',
                'message': 'All systems operating normally',
                'metrics': asdict(latest)
            }
        else:
            return {
                'status': 'warning' if len(issues) <= 2 else 'critical',
                'message': f"Issues detected: {'; '.join(issues)}",
                'issues': issues,
                'metrics': asdict(latest)
            }


def cache_result(ttl: int = 300, key_func: Optional[callable] = None):
    """Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_func: Function to generate cache key (optional)
    """
    def decorator(func):
        cache = MemoryCache(max_size=500, default_ttl=ttl)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache._generate_key(*args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.cache_stats = cache.get_stats
        
        return wrapper
    return decorator


def time_component(component_name: str, monitor: PerformanceMonitor):
    """Decorator for timing component execution.
    
    Args:
        component_name: Name of the component being timed
        monitor: Performance monitor instance
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                monitor.record_component_time(component_name, duration)
        return wrapper
    return decorator


class PerformanceOptimizer:
    """Main performance optimization coordinator."""
    
    def __init__(self):
        self.cache = MemoryCache(max_size=1000, default_ttl=300)
        self.query_optimizer = QueryOptimizer()
        self.monitor = PerformanceMonitor()
        self._monitoring_active = False
        self._monitoring_thread = None
    
    def start_monitoring(self, interval: int = 30):
        """Start background performance monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        
        def monitor_loop():
            while self._monitoring_active:
                try:
                    metrics = self.monitor.collect_metrics(self.cache)
                    
                    # Log performance warnings
                    if metrics.cpu_percent > 80:
                        logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")
                    
                    if metrics.memory_percent > 85:
                        logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")
                    
                    if metrics.avg_response_time > 2.0:
                        logger.warning(f"Slow response time: {metrics.avg_response_time:.2f}s")
                    
                    # Trigger garbage collection if memory usage is high
                    if metrics.memory_percent > 90:
                        logger.info("Triggering garbage collection due to high memory usage")
                        gc.collect()
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
                
                time.sleep(interval)
        
        self._monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitoring_thread.start()
        logger.info(f"Performance monitoring started with {interval}s interval")
    
    def stop_monitoring(self):
        """Stop background performance monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        # Check cache performance
        cache_stats = self.cache.get_stats()
        if cache_stats['hit_rate'] < 0.5:
            recommendations.append(
                f"Low cache hit rate ({cache_stats['hit_rate']:.1%}). "
                "Consider increasing cache size or TTL values."
            )
        
        # Check query performance
        slow_queries = self.query_optimizer.get_slow_queries()
        if slow_queries:
            recommendations.append(
                f"Found {len(slow_queries)} slow queries. "
                "Consider adding database indexes or optimizing query logic."
            )
        
        # Check system resources
        health = self.monitor.check_health()
        if health['status'] != 'healthy':
            recommendations.append(
                f"System health issues detected: {health['message']}"
            )
        
        # Check memory usage
        if cache_stats['memory_usage_mb'] > 100:
            recommendations.append(
                f"High cache memory usage ({cache_stats['memory_usage_mb']:.1f}MB). "
                "Consider reducing cache size."
            )
        
        return recommendations
    
    def optimize_database_queries(self):
        """Apply database query optimizations."""
        # This would typically involve creating indexes, updating query plans, etc.
        # For now, we'll log the optimization recommendations
        query_stats = self.query_optimizer.get_query_stats()
        
        for query_type, stats in query_stats.items():
            if stats['slow_queries'] > 0:
                logger.info(
                    f"Query type '{query_type}' has {stats['slow_queries']} slow queries. "
                    f"Average duration: {stats['avg_duration']:.3f}s"
                )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            'timestamp': datetime.now().isoformat(),
            'cache_stats': self.cache.get_stats(),
            'query_stats': self.query_optimizer.get_query_stats(),
            'system_health': self.monitor.check_health(),
            'metrics_summary': self.monitor.get_metrics_summary(minutes=10),
            'slow_queries': self.query_optimizer.get_slow_queries()[:10],  # Top 10
            'recommendations': self.get_optimization_recommendations()
        }


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    return performance_optimizer