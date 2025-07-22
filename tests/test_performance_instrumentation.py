import time
from unittest.mock import patch

import pytest

from arris_modem_status.instrumentation import PerformanceInstrumentation
from arris_modem_status.models import TimingMetrics


@pytest.mark.unit
@pytest.mark.performance
class TestTimingMetrics:
    """Test TimingMetrics dataclass."""

    def test_timing_metrics_creation(self):
        """Test TimingMetrics creation and properties."""
        start_time = time.time()
        end_time = start_time + 0.5

        metrics = TimingMetrics(
            operation="test_op",
            start_time=start_time,
            end_time=end_time,
            duration=0.5,
            success=True,
            error_type=None,
            retry_count=0,
            http_status=200,
            response_size=1024,
        )

        assert metrics.operation == "test_op"
        assert metrics.duration == 0.5
        assert metrics.duration_ms == 500.0
        assert metrics.success is True
        assert metrics.http_status == 200
        assert metrics.response_size == 1024

    def test_timing_metrics_with_error(self):
        """Test TimingMetrics with error information."""
        metrics = TimingMetrics(
            operation="failed_op",
            start_time=time.time(),
            end_time=time.time() + 0.1,
            duration=0.1,
            success=False,
            error_type="ConnectionError",
            retry_count=2,
            http_status=500,
        )

        assert metrics.success is False
        assert metrics.error_type == "ConnectionError"
        assert metrics.retry_count == 2


@pytest.mark.unit
@pytest.mark.performance
class TestPerformanceInstrumentation:
    """Test PerformanceInstrumentation class."""

    def test_initialization(self):
        """Test instrumentation initialization."""
        instrumentation = PerformanceInstrumentation()

        assert instrumentation.timing_metrics == []
        assert instrumentation.request_metrics == {}
        assert isinstance(instrumentation.session_start_time, float)

    def test_start_timer(self):
        """Test timer start functionality."""
        instrumentation = PerformanceInstrumentation()

        start_time = instrumentation.start_timer("test_operation")

        assert isinstance(start_time, float)
        assert start_time <= time.time()

    def test_record_timing_success(self):
        """Test recording successful timing."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        metric = instrumentation.record_timing(
            "test_operation",
            start_time,
            success=True,
            http_status=200,
            response_size=1024,
        )

        assert isinstance(metric, TimingMetrics)
        assert metric.operation == "test_operation"
        assert metric.success is True
        assert metric.http_status == 200
        assert metric.response_size == 1024
        assert len(instrumentation.timing_metrics) == 1
        assert "test_operation" in instrumentation.request_metrics

    def test_record_timing_failure(self):
        """Test recording failed timing."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        metric = instrumentation.record_timing(
            "failed_operation",
            start_time,
            success=False,
            error_type="ConnectionError",
            retry_count=1,
        )

        assert metric.success is False
        assert metric.error_type == "ConnectionError"
        assert metric.retry_count == 1

    def test_multiple_operations(self):
        """Test recording multiple operations."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        # Record multiple metrics
        instrumentation.record_timing("auth", start_time, success=True)
        instrumentation.record_timing("data_retrieval", start_time, success=True)
        instrumentation.record_timing("auth", start_time, success=True)

        assert len(instrumentation.timing_metrics) == 3
        # Two distinct operations
        assert len(instrumentation.request_metrics) == 2
        assert len(instrumentation.request_metrics["auth"]) == 2
        assert len(instrumentation.request_metrics["data_retrieval"]) == 1

    def test_get_performance_summary_empty(self):
        """Test performance summary with no metrics."""
        instrumentation = PerformanceInstrumentation()

        summary = instrumentation.get_performance_summary()

        assert summary["error"] == "No timing metrics recorded"

    def test_get_performance_summary_with_data(self):
        """Test performance summary with recorded metrics."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        # Record some test metrics
        instrumentation.record_timing("auth", start_time, success=True, http_status=200)
        instrumentation.record_timing("data", start_time, success=True, http_status=200)
        instrumentation.record_timing("auth", start_time, success=False, error_type="TimeoutError")

        summary = instrumentation.get_performance_summary()

        assert "session_metrics" in summary
        assert "operation_breakdown" in summary
        assert "response_time_percentiles" in summary
        assert "performance_insights" in summary

        # Check session metrics
        session_metrics = summary["session_metrics"]
        assert session_metrics["total_operations"] == 3
        assert session_metrics["successful_operations"] == 2
        assert session_metrics["failed_operations"] == 1

        # Check operation breakdown
        operation_breakdown = summary["operation_breakdown"]
        assert "auth" in operation_breakdown
        assert "data" in operation_breakdown

        auth_stats = operation_breakdown["auth"]
        assert auth_stats["count"] == 2
        assert auth_stats["success_rate"] == 0.5  # 1 success out of 2

    def test_performance_insights_generation(self):
        """Test performance insights generation."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        # Record metrics that should generate insights
        instrumentation.record_timing("auth", start_time, success=True)

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        assert isinstance(insights, list)
        # Should have some insights with recorded metrics

    def test_percentile_calculation(self):
        """Test response time percentile calculation."""
        instrumentation = PerformanceInstrumentation()
        base_time = time.time()

        # Record metrics with known durations
        for i, duration in enumerate([0.1, 0.2, 0.3, 0.4, 0.5]):
            instrumentation.record_timing(f"op_{i}", base_time, success=True)
            # Manually set duration for testing
            instrumentation.timing_metrics[-1].duration = duration

        summary = instrumentation.get_performance_summary()
        percentiles = summary["response_time_percentiles"]

        assert "p50" in percentiles
        assert "p90" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # With 5 values [0.1, 0.2, 0.3, 0.4, 0.5], median should be 0.3
        assert percentiles["p50"] == 0.3

    def test_http_compatibility_overhead_tracking(self):
        """Test tracking of HTTP compatibility overhead."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        # Record normal operation
        instrumentation.record_timing("normal_request", start_time, success=True)

        # Record operation with compatibility handling
        instrumentation.record_timing(
            "http_compatibility_fallback",
            start_time,
            success=True,
            retry_count=1,
        )

        summary = instrumentation.get_performance_summary()
        session_metrics = summary["session_metrics"]

        # Should track compatibility overhead
        assert "http_compatibility_overhead" in session_metrics

    @patch("arris_modem_status.instrumentation.logger")
    def test_debug_logging(self, mock_logger):
        """Test debug logging during timing recording."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        instrumentation.record_timing("test_op", start_time, success=True)

        # Should have logged the timing
        mock_logger.debug.assert_called()

        # Check log message format
        call_args = mock_logger.debug.call_args[0][0]
        assert "test_op" in call_args
        assert "ms" in call_args
        assert "success: True" in call_args

    def test_record_timing_with_zero_response_size(self):
        """Test recording timing with zero response size."""
        instrumentation = PerformanceInstrumentation()
        start_time = time.time()

        # Record with zero response size
        metric = instrumentation.record_timing(
            "empty_response",
            start_time,
            success=True,
            http_status=204,
            response_size=0,  # No Content
        )

        assert metric.response_size == 0
        assert metric.http_status == 204

    def test_performance_insights_low_throughput(self):
        """Test performance insights for low throughput scenario."""
        instrumentation = PerformanceInstrumentation()

        # Record very few operations over a long time
        # This should trigger the low throughput insight
        instrumentation.session_start_time = time.time() - 10  # 10 seconds ago

        instrumentation.record_timing("slow_op1", time.time() - 5, success=True)
        instrumentation.record_timing("slow_op2", time.time() - 2, success=True)

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        # Should have insight about low throughput
        assert any("low throughput" in insight.lower() for insight in insights)

    def test_performance_insights_no_errors(self):
        """Test performance insights when there are no errors."""
        instrumentation = PerformanceInstrumentation()

        # Record only successful operations
        for i in range(5):
            instrumentation.record_timing(f"success_{i}", time.time() - i, success=True)

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        # Should have insight about perfect reliability
        assert any("perfect reliability" in insight.lower() or "0% error" in insight.lower() for insight in insights)

    def test_performance_insights_slow_auth(self):
        """Test performance insights for slow authentication."""
        instrumentation = PerformanceInstrumentation()

        # Record slow auth operations (manually set durations)
        metric1 = instrumentation.record_timing("authentication_complete", time.time() - 10, success=True)
        metric1.duration = 3.5  # Manually set to trigger slow auth insight

        metric2 = instrumentation.record_timing("authentication_challenge", time.time() - 5, success=True)
        metric2.duration = 2.5

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        # Should have insight about slow authentication
        assert any("authentication" in insight.lower() and "consider" in insight.lower() for insight in insights)

    def test_performance_insights_fast_auth(self):
        """Test performance insights for fast authentication."""
        from arris_modem_status.models import TimingMetrics

        instrumentation = PerformanceInstrumentation()

        # Create metrics with consistent timing data
        start_time = time.time()

        # First create the timing metrics with proper structure
        metric1 = TimingMetrics(
            operation="authentication_complete",
            start_time=start_time - 1.0,
            end_time=start_time - 0.5,
            duration=0.5,
            success=True,
        )

        metric2 = TimingMetrics(
            operation="authentication_challenge",
            start_time=start_time - 0.5,
            end_time=start_time - 0.2,
            duration=0.3,
            success=True,
        )

        # Add to instrumentation
        instrumentation.timing_metrics.append(metric1)
        instrumentation.timing_metrics.append(metric2)

        # IMPORTANT: Update request_metrics to match
        instrumentation.request_metrics["authentication_complete"] = [0.5]
        instrumentation.request_metrics["authentication_challenge"] = [0.3]

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        # The total auth time is 0.5 + 0.3 = 0.8, which is < 1.0
        # So it should generate the "excellent" message
        assert any("excellent" in insight.lower() and "authentication" in insight.lower() for insight in insights)

    def test_percentiles_with_single_value(self):
        """Test percentile calculation with only one value."""
        instrumentation = PerformanceInstrumentation()

        # Record single metric
        metric = instrumentation.record_timing("single_op", time.time() - 1.0, success=True)
        metric.duration = 1.0  # Set specific duration

        summary = instrumentation.get_performance_summary()
        percentiles = summary["response_time_percentiles"]

        # All percentiles should be the same with single value
        assert percentiles["p50"] == percentiles["p90"]
        assert percentiles["p90"] == percentiles["p95"]
        assert percentiles["p95"] == percentiles["p99"]
        assert percentiles["p50"] == 1.0

    def test_percentiles_with_no_successful_operations(self):
        """Test percentile calculation when all operations failed."""
        instrumentation = PerformanceInstrumentation()

        # Record only failed operations
        instrumentation.record_timing("fail1", time.time() - 1.0, success=False, error_type="TestError")
        instrumentation.record_timing("fail2", time.time() - 0.5, success=False, error_type="TestError")

        summary = instrumentation.get_performance_summary()
        percentiles = summary["response_time_percentiles"]

        # Should have zero percentiles when no successful operations
        assert percentiles["p50"] == 0
        assert percentiles["p90"] == 0
        assert percentiles["p95"] == 0
        assert percentiles["p99"] == 0

    def test_performance_insights_high_error_rate(self):
        """Test performance insights with high error rate."""
        instrumentation = PerformanceInstrumentation()

        # Record mostly failed operations
        for i in range(8):
            instrumentation.record_timing(
                f"fail_{i}",
                time.time() - i,
                success=False,
                error_type="NetworkError",
            )

        # Only 2 successful
        instrumentation.record_timing("success_1", time.time() - 1, success=True)
        instrumentation.record_timing("success_2", time.time() - 0.5, success=True)

        summary = instrumentation.get_performance_summary()
        insights = summary["performance_insights"]

        # Should have insight about high error rate
        assert any("high error rate" in insight.lower() for insight in insights)

    def test_http_compatibility_overhead_calculation(self):
        """Test calculation of HTTP compatibility overhead."""
        instrumentation = PerformanceInstrumentation()

        # Record normal operation
        normal = instrumentation.record_timing("normal_request", time.time() - 1, success=True)
        normal.duration = 0.5

        # Record operation with compatibility handling (has retry)
        compat = instrumentation.record_timing(
            "http_compatibility_fallback",
            time.time() - 0.5,
            success=True,
            retry_count=1,
        )
        compat.duration = 0.8

        summary = instrumentation.get_performance_summary()

        # Should calculate compatibility overhead
        assert "http_compatibility_overhead" in summary["session_metrics"]
        # Only the compat operation
        assert summary["session_metrics"]["http_compatibility_overhead"] == 0.8


@pytest.mark.unit
@pytest.mark.performance
class TestPerformanceIntegration:
    """Test performance instrumentation integration."""

    def test_instrumentation_disabled(self):
        """Test behavior when instrumentation is disabled."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test", enable_instrumentation=False)

        assert client.instrumentation is None

    def test_instrumentation_enabled(self):
        """Test behavior when instrumentation is enabled."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test", enable_instrumentation=True)

        assert client.instrumentation is not None
        assert isinstance(client.instrumentation, PerformanceInstrumentation)

    def test_get_performance_metrics(self):
        """Test getting performance metrics from client."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test", enable_instrumentation=True)

        # Should return metrics even if empty
        metrics = client.get_performance_metrics()
        assert isinstance(metrics, dict)

    def test_get_performance_metrics_disabled(self):
        """Test getting performance metrics when disabled."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test", enable_instrumentation=False)

        metrics = client.get_performance_metrics()
        assert metrics["error"] == "Performance instrumentation not enabled"
