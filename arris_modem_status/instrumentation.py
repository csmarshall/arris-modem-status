"""
Performance Instrumentation for Arris Modem Status Client
========================================================

This module provides comprehensive performance instrumentation for monitoring
and analyzing the performance characteristics of the Arris client.

Author: Charles Marshall
Version: 1.3.0
"""

import logging
import time
from typing import Any, Dict, List, Optional

from .models import TimingMetrics

logger = logging.getLogger("arris-modem-status")


class PerformanceInstrumentation:
    """
    Comprehensive performance instrumentation for the Arris client.

    Tracks detailed timing metrics for all operations:
    - Individual HNAP request timing
    - Authentication vs data retrieval breakdown
    - Network latency vs processing time
    - HTTP compatibility overhead
    - Concurrent request coordination
    """

    def __init__(self) -> None:
        self.timing_metrics: List[TimingMetrics] = []
        self.session_start_time = time.time()
        self.auth_metrics: Dict[str, float] = {}
        self.request_metrics: Dict[str, List[float]] = {}

    def start_timer(self, operation: str) -> float:
        """Start timing an operation."""
        return time.time()

    def record_timing(
        self,
        operation: str,
        start_time: float,
        success: bool = True,
        error_type: Optional[str] = None,
        retry_count: int = 0,
        http_status: Optional[int] = None,
        response_size: int = 0,
    ) -> TimingMetrics:
        """Record timing metrics for an operation."""
        end_time = time.time()
        duration = end_time - start_time

        metric = TimingMetrics(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            error_type=error_type,
            retry_count=retry_count,
            http_status=http_status,
            response_size=response_size,
        )

        self.timing_metrics.append(metric)

        # Update request metrics for statistics
        if operation not in self.request_metrics:
            self.request_metrics[operation] = []
        self.request_metrics[operation].append(duration)

        logger.debug(f"📊 {operation}: {duration * 1000:.1f}ms (success: {success})")
        return metric

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        if not self.timing_metrics:
            return {"error": "No timing metrics recorded"}

        total_session_time = time.time() - self.session_start_time

        # Aggregate metrics by operation
        operation_stats = {}
        for operation, durations in self.request_metrics.items():
            if durations:
                operation_stats[operation] = {
                    "count": len(durations),
                    "total_time": sum(durations),
                    "avg_time": sum(durations) / len(durations),
                    "min_time": min(durations),
                    "max_time": max(durations),
                    "success_rate": len([m for m in self.timing_metrics if m.operation == operation and m.success])
                    / len([m for m in self.timing_metrics if m.operation == operation]),
                }

        # Calculate percentiles for total response time
        all_durations = [m.duration for m in self.timing_metrics if m.success]
        if all_durations:
            all_durations.sort()
            n = len(all_durations)
            percentiles = {
                "p50": all_durations[n // 2] if n > 0 else 0,
                "p90": all_durations[int(n * 0.9)] if n > 0 else 0,
                "p95": all_durations[int(n * 0.95)] if n > 0 else 0,
                "p99": all_durations[int(n * 0.99)] if n > 0 else 0,
            }
        else:
            percentiles = {"p50": 0, "p90": 0, "p95": 0, "p99": 0}

        # HTTP compatibility overhead
        compatibility_metrics = [
            m for m in self.timing_metrics if "compatibility" in m.operation.lower() or m.retry_count > 0
        ]
        compatibility_overhead = sum(m.duration for m in compatibility_metrics)

        return {
            "session_metrics": {
                "total_session_time": total_session_time,
                "total_operations": len(self.timing_metrics),
                "successful_operations": len([m for m in self.timing_metrics if m.success]),
                "failed_operations": len([m for m in self.timing_metrics if not m.success]),
                "http_compatibility_overhead": compatibility_overhead,
            },
            "operation_breakdown": operation_stats,
            "response_time_percentiles": percentiles,
            "performance_insights": self._generate_performance_insights(operation_stats, total_session_time),
        }

    def _generate_performance_insights(self, operation_stats: Dict[str, Any], total_time: float) -> List[str]:
        """Generate performance insights based on metrics."""
        insights = []

        # Authentication performance
        auth_ops = [op for op in operation_stats.keys() if "auth" in op.lower()]
        if auth_ops:
            # Calculate total auth time across all auth operations
            total_auth_time = 0
            for op in auth_ops:
                avg_time = operation_stats[op].get("avg_time", 0)
                total_auth_time += avg_time

            if total_auth_time > 2.0:
                insights.append(f"Authentication taking {total_auth_time:.2f}s - consider network optimization")
            elif total_auth_time < 1.0:
                insights.append(f"Excellent authentication performance: {total_auth_time:.2f}s")

        # Overall throughput
        if total_time > 0:
            ops_per_sec = len(self.timing_metrics) / total_time
            if ops_per_sec > 2:
                insights.append(f"High throughput: {ops_per_sec:.1f} operations/sec")
            elif ops_per_sec < 0.5:
                insights.append(f"Low throughput: {ops_per_sec:.1f} operations/sec - check for bottlenecks")

        # Error rates
        total_ops = len(self.timing_metrics)
        failed_ops = len([m for m in self.timing_metrics if not m.success])
        if total_ops > 0:
            error_rate = failed_ops / total_ops
            if error_rate > 0.1:
                insights.append(f"High error rate: {error_rate * 100:.1f}% - investigate HTTP compatibility")
            elif error_rate == 0:
                insights.append("Perfect reliability: 0% error rate")

        return insights


# Export instrumentation classes
__all__ = ["PerformanceInstrumentation"]
