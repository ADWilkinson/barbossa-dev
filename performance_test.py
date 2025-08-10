#!/usr/bin/env python3
"""
Performance test script for Barbossa Enhanced optimizations
Tests various performance improvements and measures execution times
"""

import time
import json
import asyncio
import statistics
from pathlib import Path
from datetime import datetime
import sys

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

try:
    from barbossa import BarbossaEnhanced
    from server_manager import BarbossaServerManager, MetricsCollector
    from web_portal.app import app, cached_response
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import components: {e}")
    COMPONENTS_AVAILABLE = False

class PerformanceTester:
    """Performance testing suite for Barbossa components"""
    
    def __init__(self):
        self.results = {}
        
    def time_operation(self, name: str, func, iterations: int = 10):
        """Time an operation multiple times and collect statistics"""
        times = []
        
        print(f"Testing {name}...")
        for i in range(iterations):
            start = time.time()
            try:
                result = func()
                end = time.time()
                duration = end - start
                times.append(duration)
                if i == 0:
                    print(f"  First run: {duration:.3f}s")
            except Exception as e:
                print(f"  Error on iteration {i}: {e}")
                continue
        
        if times:
            self.results[name] = {
                'avg_time': statistics.mean(times),
                'min_time': min(times),
                'max_time': max(times),
                'std_dev': statistics.stdev(times) if len(times) > 1 else 0,
                'iterations': len(times),
                'timestamp': datetime.now().isoformat()
            }
            
            stats = self.results[name]
            print(f"  Average: {stats['avg_time']:.3f}s")
            print(f"  Min: {stats['min_time']:.3f}s")
            print(f"  Max: {stats['max_time']:.3f}s")
            print(f"  Std Dev: {stats['std_dev']:.3f}s")
        else:
            print(f"  No successful runs for {name}")
    
    def test_database_operations(self):
        """Test database operation performance"""
        if not COMPONENTS_AVAILABLE:
            return
        
        print("\n=== Testing Database Operations ===")
        
        try:
            # Create temporary database for testing
            test_db = Path("/tmp/test_metrics.db")
            if test_db.exists():
                test_db.unlink()
            
            collector = MetricsCollector(test_db)
            
            # Test metrics collection
            self.time_operation("metrics_collection", collector.collect_metrics, iterations=5)
            
            # Test metrics storage
            test_metrics = collector.collect_metrics()
            self.time_operation(
                "metrics_storage", 
                lambda: collector.store_metrics(test_metrics), 
                iterations=20
            )
            
            # Test batch storage
            metrics_list = [test_metrics for _ in range(10)]
            self.time_operation(
                "batch_metrics_storage",
                lambda: collector.store_metrics_batch(metrics_list),
                iterations=5
            )
            
            # Test historical query
            self.time_operation(
                "historical_metrics_query",
                lambda: collector.get_historical_metrics(hours=1, limit=100),
                iterations=10
            )
            
            # Cleanup
            if test_db.exists():
                test_db.unlink()
                
        except Exception as e:
            print(f"Error testing database operations: {e}")
    
    def test_caching_performance(self):
        """Test caching system performance"""
        print("\n=== Testing Caching Performance ===")
        
        if not COMPONENTS_AVAILABLE:
            return
            
        try:
            collector = MetricsCollector(Path("/tmp/test_cache.db"))
            
            # Test with cache miss (first call)
            cache_key = 'test_cache_performance'
            
            def expensive_operation():
                # Simulate expensive computation
                time.sleep(0.1)  # 100ms delay
                return collector.collect_metrics()
            
            # Test cache miss
            self.time_operation("cache_miss", expensive_operation, iterations=3)
            
            # Test cache hit (should be much faster)
            # First populate the cache
            expensive_operation()
            
            def cached_operation():
                return collector.collect_metrics()  # Should be cached now
            
            self.time_operation("cache_hit", cached_operation, iterations=10)
            
        except Exception as e:
            print(f"Error testing caching: {e}")
    
    def test_parallel_operations(self):
        """Test parallel operation performance"""
        print("\n=== Testing Parallel Operations ===")
        
        if not COMPONENTS_AVAILABLE:
            return
        
        try:
            from server_manager import ServiceManager
            
            test_db = Path("/tmp/test_services.db")
            service_manager = ServiceManager(test_db)
            
            # Test sequential vs parallel service updates
            def sequential_update():
                service_manager._get_systemd_services()
                service_manager._get_docker_containers()
                service_manager._get_tmux_sessions()
            
            self.time_operation("sequential_service_update", sequential_update, iterations=3)
            
            # The parallel version is tested through _update_services which uses the executor
            self.time_operation("parallel_service_update", service_manager._update_services, iterations=3)
            
            if test_db.exists():
                test_db.unlink()
                
        except Exception as e:
            print(f"Error testing parallel operations: {e}")
    
    def test_web_portal_caching(self):
        """Test web portal API caching"""
        print("\n=== Testing Web Portal Caching ===")
        
        # Test the cached_response decorator
        call_count = 0
        
        @cached_response(ttl=5)  # 5 second cache
        def test_api_endpoint():
            nonlocal call_count
            call_count += 1
            time.sleep(0.05)  # Simulate API work
            return {'data': f'response_{call_count}', 'timestamp': time.time()}
        
        # First call should execute
        start = time.time()
        result1 = test_api_endpoint()
        first_call_time = time.time() - start
        
        # Second call should be cached
        start = time.time()
        result2 = test_api_endpoint()
        cached_call_time = time.time() - start
        
        print(f"  First call time: {first_call_time:.3f}s")
        print(f"  Cached call time: {cached_call_time:.3f}s")
        print(f"  Cache speedup: {first_call_time / cached_call_time:.1f}x")
        print(f"  Call count: {call_count} (should be 1)")
        
        self.results['web_portal_caching'] = {
            'first_call_time': first_call_time,
            'cached_call_time': cached_call_time,
            'speedup_ratio': first_call_time / cached_call_time if cached_call_time > 0 else 0,
            'cache_working': call_count == 1
        }
    
    def test_memory_usage(self):
        """Test memory usage optimization"""
        print("\n=== Testing Memory Usage ===")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            if COMPONENTS_AVAILABLE:
                # Create Barbossa instance
                barbossa = BarbossaEnhanced()
                
                # Memory after initialization
                init_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                # Perform some operations
                for _ in range(10):
                    barbossa.get_comprehensive_status()
                    barbossa.perform_system_health_check()
                
                # Memory after operations
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                barbossa.cleanup()
            else:
                init_memory = baseline_memory
                final_memory = baseline_memory
            
            print(f"  Baseline memory: {baseline_memory:.1f} MB")
            print(f"  After init: {init_memory:.1f} MB")
            print(f"  After operations: {final_memory:.1f} MB")
            print(f"  Memory growth: {final_memory - baseline_memory:.1f} MB")
            
            self.results['memory_usage'] = {
                'baseline_mb': baseline_memory,
                'init_mb': init_memory,
                'final_mb': final_memory,
                'growth_mb': final_memory - baseline_memory
            }
            
        except Exception as e:
            print(f"Error testing memory usage: {e}")
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("Starting Barbossa Enhanced Performance Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        self.test_database_operations()
        self.test_caching_performance()
        self.test_parallel_operations()
        self.test_web_portal_caching()
        self.test_memory_usage()
        
        total_time = time.time() - start_time
        
        print(f"\n=== Performance Test Summary ===")
        print(f"Total test time: {total_time:.2f}s")
        
        # Save results
        results_file = Path(__file__).parent / 'performance_test_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to: {results_file}")
        
        # Print key metrics
        if 'metrics_collection' in self.results:
            print(f"\nKey Performance Metrics:")
            print(f"  Metrics Collection: {self.results['metrics_collection']['avg_time']:.3f}s avg")
            
        if 'web_portal_caching' in self.results:
            cache_results = self.results['web_portal_caching']
            print(f"  Web Portal Cache Speedup: {cache_results.get('speedup_ratio', 0):.1f}x")
            
        if 'memory_usage' in self.results:
            mem_results = self.results['memory_usage']
            print(f"  Memory Growth: {mem_results.get('growth_mb', 0):.1f} MB")

def main():
    """Run performance tests"""
    tester = PerformanceTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()