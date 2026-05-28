"""
Profiling Utilities
Author: Jhon Villegas
Project: Petroflow FastAPI Backend

Performance profiling and benchmarking utilities for optimization operations.
Provides decorators and functions to measure execution time and compare implementations.
"""

import time
import functools
import logging
from typing import Callable, Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import statistics

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics for a single execution."""
    function_name: str
    execution_time_ms: float
    timestamp: datetime
    args_hash: Optional[int] = None
    result_size: Optional[int] = None
    memory_delta_mb: Optional[float] = None


@dataclass
class PerformanceReport:
    """Aggregated performance report."""
    function_name: str
    total_calls: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    executions: List[ExecutionMetrics] = field(default_factory=list)


class PerformanceProfiler:
    """
    Performance profiler for tracking execution metrics.
    
    Features:
    - Track execution time for functions
    - Aggregate statistics across multiple calls
    - Generate performance reports
    - Compare different implementations
    """
    
    def __init__(self):
        """Initialize performance profiler."""
        self._metrics: Dict[str, List[ExecutionMetrics]] = {}
        self.logger = logging.getLogger(f"{__name__}.PerformanceProfiler")
    
    def record_execution(self, metric: ExecutionMetrics):
        """
        Record an execution metric.
        
        Args:
            metric: Execution metric to record
        """
        if metric.function_name not in self._metrics:
            self._metrics[metric.function_name] = []
        
        self._metrics[metric.function_name].append(metric)
        
        self.logger.debug(
            f"Recorded execution: {metric.function_name} took {metric.execution_time_ms:.2f}ms",
            extra={
                "function": metric.function_name,
                "execution_time_ms": metric.execution_time_ms,
                "timestamp": metric.timestamp.isoformat()
            }
        )
    
    def get_report(self, function_name: str) -> Optional[PerformanceReport]:
        """
        Get performance report for a function.
        
        Args:
            function_name: Name of function to report on
            
        Returns:
            PerformanceReport or None if no data
        """
        if function_name not in self._metrics:
            return None
        
        executions = self._metrics[function_name]
        times = [e.execution_time_ms for e in executions]
        
        return PerformanceReport(
            function_name=function_name,
            total_calls=len(executions),
            total_time_ms=sum(times),
            avg_time_ms=statistics.mean(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
            std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0.0,
            executions=executions
        )
    
    def get_all_reports(self) -> List[PerformanceReport]:
        """
        Get performance reports for all tracked functions.
        
        Returns:
            List of performance reports
        """
        reports = []
        for func_name in self._metrics.keys():
            report = self.get_report(func_name)
            if report:
                reports.append(report)
        return reports
    
    def clear_metrics(self, function_name: Optional[str] = None):
        """
        Clear recorded metrics.
        
        Args:
            function_name: Specific function to clear, or None for all
        """
        if function_name:
            self._metrics.pop(function_name, None)
        else:
            self._metrics.clear()
    
    def print_report(self, function_name: Optional[str] = None):
        """
        Print performance report to console.
        
        Args:
            function_name: Specific function to report, or None for all
        """
        if function_name:
            reports = [self.get_report(function_name)]
        else:
            reports = self.get_all_reports()
        
        print("\n" + "=" * 80)
        print("PERFORMANCE PROFILING REPORT")
        print("=" * 80)
        
        for report in reports:
            if report:
                print(f"\nFunction: {report.function_name}")
                print(f"  Total Calls: {report.total_calls}")
                print(f"  Total Time: {report.total_time_ms:.2f} ms")
                print(f"  Average Time: {report.avg_time_ms:.2f} ms")
                print(f"  Min Time: {report.min_time_ms:.2f} ms")
                print(f"  Max Time: {report.max_time_ms:.2f} ms")
                print(f"  Std Dev: {report.std_dev_ms:.2f} ms")
        
        print("\n" + "=" * 80)


# Global profiler instance
_global_profiler = PerformanceProfiler()


def profile_execution_time(
    func: Optional[Callable] = None,
    *,
    profiler: Optional[PerformanceProfiler] = None,
    log_result: bool = True
) -> Callable:
    """
    Decorator to profile function execution time.
    
    Args:
        func: Function to decorate
        profiler: Custom profiler instance (uses global if None)
        log_result: Whether to log execution time
        
    Returns:
        Decorated function
        
    Example:
        @profile_execution_time
        def my_function():
            # function code
            pass
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            success = False
            result = None
            
            try:
                result = f(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise e
            finally:
                end_time = time.perf_counter()
                execution_time_ms = (end_time - start_time) * 1000
                
                # Create metric
                metric = ExecutionMetrics(
                    function_name=f.__name__,
                    execution_time_ms=execution_time_ms,
                    timestamp=datetime.utcnow(),
                    args_hash=hash(str(args) + str(kwargs)) if args or kwargs else None
                )
                
                # Record in profiler
                target_profiler = profiler or _global_profiler
                target_profiler.record_execution(metric)
                
                # Log if requested
                if log_result:
                    logger.info(
                        f"{f.__name__} executed in {execution_time_ms:.2f}ms",
                        extra={
                            "function": f.__name__,
                            "execution_time_ms": execution_time_ms,
                            "success": success
                        }
                    )
            
            return result
        
        return wrapper
    
    # Handle both @profile_execution_time and @profile_execution_time()
    if func is None:
        return decorator
    else:
        return decorator(func)


def compare_performance(
    implementations: Dict[str, Callable],
    test_args: List[Tuple],
    iterations: int = 100
) -> Dict[str, PerformanceReport]:
    """
    Compare performance of multiple implementations.
    
    Args:
        implementations: Dictionary of {name: function}
        test_args: List of argument tuples to test with
        iterations: Number of iterations per test case
        
    Returns:
        Dictionary of {name: PerformanceReport}
        
    Example:
        results = compare_performance(
            {
                'vectorized': vectorized_func,
                'loop': loop_func
            },
            test_args=[(data1,), (data2,)],
            iterations=100
        )
    """
    profiler = PerformanceProfiler()
    results = {}
    
    for name, func in implementations.items():
        logger.info(f"Benchmarking implementation: {name}")
        
        # Wrap function with profiler
        profiled_func = profile_execution_time(func, profiler=profiler, log_result=False)
        
        # Run iterations
        for _ in range(iterations):
            for args in test_args:
                try:
                    profiled_func(*args)
                except Exception as e:
                    logger.error(f"Error in {name}: {e}")
        
        # Get report
        report = profiler.get_report(func.__name__)
        if report:
            results[name] = report
    
    return results


def print_comparison_report(
    comparison_results: Dict[str, PerformanceReport],
    baseline: Optional[str] = None
):
    """
    Print comparison report for multiple implementations.
    
    Args:
        comparison_results: Results from compare_performance()
        baseline: Name of baseline implementation for speedup calculation
    """
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON REPORT")
    print("=" * 80)
    
    # Sort by average time
    sorted_results = sorted(
        comparison_results.items(),
        key=lambda x: x[1].avg_time_ms
    )
    
    baseline_time = None
    if baseline and baseline in comparison_results:
        baseline_time = comparison_results[baseline].avg_time_ms
    
    print(f"\n{'Implementation':<20} {'Avg Time (ms)':<15} {'Min (ms)':<12} {'Max (ms)':<12} {'Speedup':<10}")
    print("-" * 80)
    
    for name, report in sorted_results:
        speedup = ""
        if baseline_time and baseline_time > 0:
            speedup_factor = baseline_time / report.avg_time_ms
            speedup = f"{speedup_factor:.2f}x"
        
        print(
            f"{name:<20} {report.avg_time_ms:<15.2f} {report.min_time_ms:<12.2f} "
            f"{report.max_time_ms:<12.2f} {speedup:<10}"
        )
    
    print("\n" + "=" * 80)
    
    # Winner
    winner = sorted_results[0]
    print(f"\n🏆 Fastest Implementation: {winner[0]}")
    print(f"   Average Time: {winner[1].avg_time_ms:.2f} ms")
    
    if baseline and baseline != winner[0] and baseline_time:
        improvement = ((baseline_time - winner[1].avg_time_ms) / baseline_time) * 100
        print(f"   Improvement over {baseline}: {improvement:.1f}%")
    
    print("\n" + "=" * 80)


def benchmark_batch_sizes(
    func: Callable,
    batch_sizes: List[int],
    data_generator: Callable[[int], Any],
    iterations: int = 10
) -> Dict[int, PerformanceReport]:
    """
    Benchmark function performance across different batch sizes.
    
    Args:
        func: Function to benchmark
        batch_sizes: List of batch sizes to test
        data_generator: Function that generates test data given batch size
        iterations: Number of iterations per batch size
        
    Returns:
        Dictionary of {batch_size: PerformanceReport}
        
    Example:
        results = benchmark_batch_sizes(
            func=optimize_batch,
            batch_sizes=[10, 100, 1000],
            data_generator=lambda n: generate_equipment_data(n),
            iterations=10
        )
    """
    profiler = PerformanceProfiler()
    results = {}
    
    for batch_size in batch_sizes:
        logger.info(f"Benchmarking batch size: {batch_size}")
        
        # Create unique function name for this batch size
        func_name = f"{func.__name__}_batch_{batch_size}"
        
        # Run iterations
        for _ in range(iterations):
            data = data_generator(batch_size)
            
            start_time = time.perf_counter()
            try:
                func(data)
            except Exception as e:
                logger.error(f"Error with batch size {batch_size}: {e}")
                continue
            end_time = time.perf_counter()
            
            execution_time_ms = (end_time - start_time) * 1000
            
            metric = ExecutionMetrics(
                function_name=func_name,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.utcnow(),
                result_size=batch_size
            )
            
            profiler.record_execution(metric)
        
        # Get report
        report = profiler.get_report(func_name)
        if report:
            results[batch_size] = report
    
    return results


def print_batch_benchmark_report(batch_results: Dict[int, PerformanceReport]):
    """
    Print benchmark report for batch size testing.
    
    Args:
        batch_results: Results from benchmark_batch_sizes()
    """
    print("\n" + "=" * 80)
    print("BATCH SIZE BENCHMARK REPORT")
    print("=" * 80)
    
    print(f"\n{'Batch Size':<15} {'Avg Time (ms)':<15} {'Time per Item (ms)':<20} {'Throughput (items/s)':<20}")
    print("-" * 80)
    
    for batch_size in sorted(batch_results.keys()):
        report = batch_results[batch_size]
        time_per_item = report.avg_time_ms / batch_size
        throughput = (batch_size / report.avg_time_ms) * 1000  # items per second
        
        print(
            f"{batch_size:<15} {report.avg_time_ms:<15.2f} {time_per_item:<20.4f} {throughput:<20.1f}"
        )
    
    print("\n" + "=" * 80)


def get_global_profiler() -> PerformanceProfiler:
    """
    Get the global profiler instance.
    
    Returns:
        Global PerformanceProfiler instance
    """
    return _global_profiler


# Export main classes and functions
__all__ = [
    "ExecutionMetrics",
    "PerformanceReport",
    "PerformanceProfiler",
    "profile_execution_time",
    "compare_performance",
    "print_comparison_report",
    "benchmark_batch_sizes",
    "print_batch_benchmark_report",
    "get_global_profiler",
]