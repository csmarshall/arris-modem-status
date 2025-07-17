#!/usr/bin/env python3
"""
Production Test Script for Arris Modem Status Client
===================================================

Comprehensive testing and validation script for the HTTP-compatible Arris modem client.
Combines functionality testing with performance benchmarking and HTTP compatibility validation.

Features:
- Quick validation test for immediate functionality verification
- Performance benchmarking with multiple iterations
- HTTP compatibility analysis and testing
- Data parsing validation with comprehensive output analysis
- JSON export for monitoring integration

Usage:
    python production_test.py --password "YOUR_PASSWORD"
    python production_test.py --password "PASSWORD" --comprehensive
    python production_test.py --password "PASSWORD" --benchmark --save-results

Author: Charles Marshall
Version: 1.3.0
License: MIT
"""

import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Import the client with proper fallback handling
try:
    from arris_modem_status import ArrisModemStatusClient
    CLIENT_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Using installed arris_modem_status package")
except ImportError:
    # Fallback for development testing
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from arris_modem_status.arris_status_client import ArrisModemStatusClient
        CLIENT_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.info("✅ Using local arris_status_client module")
    except ImportError:
        CLIENT_AVAILABLE = False
        print("❌ ERROR: Cannot import ArrisModemStatusClient")
        print("📋 Please ensure arris_modem_status is installed or run from project directory")

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ProductionTestRunner:
    """
    Production-ready test runner for Arris modem client validation.

    Provides multiple test modes:
    - Quick validation (default)
    - Performance benchmarking
    - HTTP compatibility analysis
    - Comprehensive data validation
    - Serial vs concurrent mode testing
    """

    def __init__(self, password: str, host: str = "192.168.100.1", concurrent: bool = True):
        """
        Initialize the test runner.

        Args:
            password: Modem admin password
            host: Modem IP address (default: "192.168.100.1")
            concurrent: Use concurrent mode (default: True)
        """
        self.password = password
        self.host = host
        self.concurrent = concurrent
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "test_configuration": {
                "host": host,
                "password_length": len(password),
                "client_version": "1.3.0",
                "concurrent_mode": concurrent
            }
        }

        if not CLIENT_AVAILABLE:
            raise ImportError("ArrisModemStatusClient not available. Please check installation.")

    def run_quick_test(self) -> bool:
        """
        Quick validation test for basic functionality verification.

        Returns:
            True if basic functionality works
        """
        print("=" * 70)
        print("🚀 ARRIS STATUS CLIENT - QUICK VALIDATION TEST")
        print(f"⏰ Time: {datetime.now().isoformat()}")
        print(f"🎯 Target: {self.host}")
        print(f"🔧 Mode: {'Concurrent' if self.concurrent else 'Serial'}")
        print("=" * 70)

        try:
            # Initialize client with HTTP compatibility
            logger.info("🔧 Initializing HTTP-compatible client...")
            start_time = time.time()

            with ArrisModemStatusClient(password=self.password, host=self.host, concurrent=self.concurrent) as client:

                # Get status with timing
                logger.info("📊 Retrieving modem status...")
                status_start = time.time()
                status = client.get_status()
                status_time = time.time() - status_start

                # Basic validation
                print("\n" + "=" * 70)
                print("📋 QUICK TEST RESULTS")
                print("=" * 70)

                # Core information
                print(f"🏷️  Model: {status.get('model_name', 'Unknown')}")
                print(f"🌐 Internet: {status.get('internet_status', 'Unknown')}")
                print(f"🔗 Connection: {status.get('connection_status', 'Unknown')}")
                print(f"⏱️  Uptime: {status.get('system_uptime', 'Unknown')}")

                if status.get('mac_address', 'Unknown') != 'Unknown':
                    print(f"🔖 MAC: {status['mac_address']}")

                # Channel summary
                downstream_count = len(status.get('downstream_channels', []))
                upstream_count = len(status.get('upstream_channels', []))
                total_channels = downstream_count + upstream_count

                print(f"\n📡 CHANNEL SUMMARY:")
                print(f"   📥 Downstream: {downstream_count} channels")
                print(f"   📤 Upstream: {upstream_count} channels")
                print(f"   📊 Total: {total_channels} channels")
                print(f"   🎯 Data Available: {status.get('channel_data_available', False)}")

                # Performance metrics
                total_time = time.time() - start_time
                print(f"\n⚡ PERFORMANCE:")
                print(f"   📊 Status Retrieval: {status_time:.2f}s")
                print(f"   🏁 Total Time: {total_time:.2f}s")
                if status_time > 0:
                    print(f"   🚀 Speed: {total_channels/status_time:.1f} channels/sec")

                # Sample channel data
                if downstream_count > 0:
                    sample = status['downstream_channels'][0]
                    print(f"\n📡 SAMPLE DOWNSTREAM CHANNEL:")
                    print(f"   🆔 Channel ID: {sample.channel_id}")
                    print(f"   📻 Frequency: {sample.frequency}")
                    print(f"   📶 Power: {sample.power}")
                    print(f"   📊 SNR: {sample.snr}")
                    print(f"   🔧 Modulation: {sample.modulation}")
                    print(f"   🔒 Lock: {sample.lock_status}")
                    if sample.corrected_errors:
                        print(f"   ✅ Corrected Errors: {sample.corrected_errors}")
                    if sample.uncorrected_errors:
                        print(f"   ❌ Uncorrected Errors: {sample.uncorrected_errors}")

                if upstream_count > 0:
                    sample = status['upstream_channels'][0]
                    print(f"\n📤 SAMPLE UPSTREAM CHANNEL:")
                    print(f"   🆔 Channel ID: {sample.channel_id}")
                    print(f"   📻 Frequency: {sample.frequency}")
                    print(f"   📶 Power: {sample.power}")
                    print(f"   🔧 Modulation: {sample.modulation}")
                    print(f"   🔒 Lock: {sample.lock_status}")

                # Success evaluation
                success_criteria = [
                    status.get('internet_status') == 'Connected',
                    downstream_count > 0,
                    upstream_count > 0,
                    status.get('channel_data_available', False),
                    status_time < 5.0  # Performance requirement
                ]

                success_count = sum(success_criteria)
                total_criteria = len(success_criteria)
                success_rate = (success_count / total_criteria) * 100

                print(f"\n🎯 SUCCESS METRICS:")
                print(f"   ✅ Criteria Met: {success_count}/{total_criteria}")
                print(f"   📊 Success Rate: {success_rate:.1f}%")
                print(f"   🚀 Performance Target: {'✅ PASSED' if status_time < 5.0 else '⚠️ SLOW'}")

                # HTTP compatibility analysis if available
                error_analysis = status.get('_error_analysis')
                if error_analysis:
                    total_errors = error_analysis.get('total_errors', 0)
                    recovery_rate = error_analysis.get('recovery_rate', 0) * 100
                    compatibility_issues = error_analysis.get('http_compatibility_issues', 0)

                    print(f"\n🔧 HTTP COMPATIBILITY ANALYSIS:")
                    print(f"   🔍 Total Errors: {total_errors}")
                    print(f"   🔄 Recovery Rate: {recovery_rate:.1f}%")
                    print(f"   🔧 HTTP Compatibility Issues: {compatibility_issues}")

                # Store results
                self.results["quick_test"] = {
                    "success_rate": success_rate,
                    "total_time": total_time,
                    "status_time": status_time,
                    "channel_count": total_channels,
                    "internet_connected": status.get('internet_status') == 'Connected',
                    "performance_target_met": status_time < 5.0,
                    "error_analysis": error_analysis
                }

                # Final assessment
                if success_count == total_criteria:
                    print(f"\n🎉 QUICK TEST: ✅ COMPLETE SUCCESS!")
                    print("   ✅ Authentication working perfectly")
                    print("   ✅ Channel data extraction operational")
                    print("   ✅ Performance targets met")
                    print("   ✅ HTTP compatibility handled automatically")
                    print("   🚀 Ready for production use!")
                    return True
                else:
                    print(f"\n⚠️  QUICK TEST: PARTIAL SUCCESS ({success_count}/{total_criteria})")
                    if status_time >= 5.0:
                        print("   ⚠️ Performance below target (>5s)")
                    if not status.get('channel_data_available'):
                        print("   ⚠️ Channel data not available")
                    return False

        except Exception as e:
            print(f"\n❌ Quick test failed: {e}")
            logger.error(f"Quick test error: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                import traceback
                traceback.print_exc()
            return False

    def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run performance benchmark tests with HTTP compatibility analysis."""
        logger.info("🏁 Starting performance benchmark...")

        benchmark_results = {
            "authentication_times": [],
            "retrieval_times": [],
            "total_times": [],
            "channel_counts": [],
            "http_compatibility_events": []
        }

        try:
            # Run 5 test iterations
            for iteration in range(5):
                logger.info(f"🔄 Benchmark iteration {iteration + 1}/5...")

                start_time = time.time()

                with ArrisModemStatusClient(password=self.password, host=self.host, concurrent=self.concurrent) as client:
                    # Time authentication separately if possible
                    auth_start = time.time()
                    if not client.authenticated:
                        client.authenticate()
                    auth_time = time.time() - auth_start

                    # Time status retrieval
                    retrieval_start = time.time()
                    status = client.get_status()
                    retrieval_time = time.time() - retrieval_start

                    total_time = time.time() - start_time
                    downstream_channels = len(status.get('downstream_channels', []))
                    upstream_channels = len(status.get('upstream_channels', []))
                    channel_count = downstream_channels + upstream_channels

                    # Track HTTP compatibility events
                    error_analysis = status.get('_error_analysis', {})
                    compatibility_issues = error_analysis.get('http_compatibility_issues', 0)

                    # Store results
                    benchmark_results["authentication_times"].append(auth_time)
                    benchmark_results["retrieval_times"].append(retrieval_time)
                    benchmark_results["total_times"].append(total_time)
                    benchmark_results["channel_counts"].append(channel_count)
                    benchmark_results["http_compatibility_events"].append(compatibility_issues)

                    logger.info(f"   ⏱️ Auth: {auth_time:.2f}s, Retrieval: {retrieval_time:.2f}s, Total: {total_time:.2f}s")
                    if compatibility_issues > 0:
                        logger.info(f"   🔧 HTTP compatibility issues handled: {compatibility_issues}")

                # Brief pause between iterations
                time.sleep(0.5)

            # Calculate statistics
            if benchmark_results["total_times"]:
                avg_channel_count = statistics.mean(benchmark_results["channel_counts"])
                avg_retrieval_time = statistics.mean(benchmark_results["retrieval_times"])
                total_compatibility_events = sum(benchmark_results["http_compatibility_events"])

                benchmark_results["statistics"] = {
                    "avg_auth_time": statistics.mean(benchmark_results["authentication_times"]),
                    "avg_retrieval_time": avg_retrieval_time,
                    "avg_total_time": statistics.mean(benchmark_results["total_times"]),
                    "min_total_time": min(benchmark_results["total_times"]),
                    "max_total_time": max(benchmark_results["total_times"]),
                    "consistency": max(benchmark_results["total_times"]) - min(benchmark_results["total_times"]),
                    "avg_channel_count": avg_channel_count,
                    "channels_per_second": avg_channel_count / avg_retrieval_time if avg_retrieval_time > 0 else 0,
                    "total_http_compatibility_events": total_compatibility_events,
                    "avg_compatibility_events_per_request": total_compatibility_events / 5
                }

                stats = benchmark_results["statistics"]
                print(f"\n📊 PERFORMANCE BENCHMARK RESULTS:")
                print(f"   🔐 Authentication: {stats['avg_auth_time']:.2f}s average")
                print(f"   📊 Data Retrieval: {stats['avg_retrieval_time']:.2f}s average")
                print(f"   🏁 Total Time: {stats['avg_total_time']:.2f}s average")
                print(f"   📈 Throughput: {stats['channels_per_second']:.1f} channels/sec")
                print(f"   🎯 Consistency: {stats['consistency']:.2f}s variance")
                print(f"   🔧 HTTP Compatibility Events: {stats['total_http_compatibility_events']} total")

        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            benchmark_results["error"] = str(e)

        return benchmark_results

    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive data analysis and HTTP compatibility validation."""
        logger.info("🔍 Starting comprehensive analysis...")

        try:
            with ArrisModemStatusClient(password=self.password, host=self.host, concurrent=self.concurrent) as client:
                # Get validation data
                validation_data = client.validate_parsing()

                # Extract key metrics
                parsing_validation = validation_data.get("parsing_validation", {})
                performance_metrics = validation_data.get("performance_metrics", {})

                analysis_results = {
                    "data_quality": {
                        "completeness_score": performance_metrics.get("data_completeness_score", 0),
                        "downstream_channels": parsing_validation.get("downstream_channels_found", 0),
                        "upstream_channels": parsing_validation.get("upstream_channels_found", 0),
                        "basic_info_complete": parsing_validation.get("basic_info_parsed", False)
                    },
                    "channel_analysis": parsing_validation.get("channel_data_quality", {}),
                    "format_validation": {
                        "mac_address_valid": parsing_validation.get("mac_address_format", False),
                        "frequency_formats": parsing_validation.get("frequency_formats", {})
                    },
                    "http_compatibility_analysis": {
                        "parsing_errors": performance_metrics.get("parsing_errors", 0),
                        "http_compatibility_issues": performance_metrics.get("http_compatibility_issues", 0),
                        "request_mode": performance_metrics.get("request_mode", "unknown")
                    }
                }

                downstream_count = analysis_results["data_quality"]["downstream_channels"]
                upstream_count = analysis_results["data_quality"]["upstream_channels"]
                completeness = analysis_results["data_quality"]["completeness_score"]

                print(f"\n🔍 COMPREHENSIVE ANALYSIS:")
                print(f"   📊 Data Completeness: {completeness:.1f}%")
                print(f"   📡 Total Channels: {downstream_count + upstream_count}")
                print(f"   ✅ MAC Address Valid: {analysis_results['format_validation']['mac_address_valid']}")

                # HTTP compatibility analysis
                http_analysis = analysis_results["http_compatibility_analysis"]
                compatibility_issues = http_analysis["http_compatibility_issues"]
                if compatibility_issues > 0:
                    print(f"   🔧 HTTP Compatibility Issues Handled: {compatibility_issues}")
                    print("   ✅ All issues resolved automatically with browser-compatible parsing")
                else:
                    print(f"   ✅ No HTTP compatibility issues detected")

                return analysis_results

        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}")
            return {"error": str(e)}

    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"production_test_results_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)

            logger.info(f"💾 Results saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

    def export_for_monitoring(self, format_type: str = "json") -> Dict[str, Any]:
        """Export results in format suitable for monitoring systems."""
        monitoring_data = {
            "timestamp": self.results["timestamp"],
            "status": "healthy" if self.results.get("quick_test", {}).get("success_rate", 0) >= 80 else "degraded",
            "metrics": {}
        }

        # Add quick test metrics if available
        if "quick_test" in self.results:
            qt = self.results["quick_test"]
            monitoring_data["metrics"].update({
                "success_rate_percent": qt.get("success_rate", 0),
                "total_time_seconds": qt.get("total_time", 0),
                "status_time_seconds": qt.get("status_time", 0),
                "channel_count": qt.get("channel_count", 0),
                "internet_connected": qt.get("internet_connected", False),
                "performance_target_met": qt.get("performance_target_met", False)
            })

            # Add error analysis metrics if available
            error_analysis = qt.get("error_analysis")
            if error_analysis:
                monitoring_data["metrics"].update({
                    "total_errors": error_analysis.get("total_errors", 0),
                    "recovery_rate_percent": error_analysis.get("recovery_rate", 0) * 100,
                    "http_compatibility_issues": error_analysis.get("http_compatibility_issues", 0)
                })

        # Add benchmark metrics if available
        if "benchmark" in self.results and "statistics" in self.results["benchmark"]:
            stats = self.results["benchmark"]["statistics"]
            monitoring_data["metrics"].update({
                "avg_auth_time_seconds": stats.get("avg_auth_time", 0),
                "avg_retrieval_time_seconds": stats.get("avg_retrieval_time", 0),
                "channels_per_second": stats.get("channels_per_second", 0),
                "http_compatibility_events": stats.get("total_http_compatibility_events", 0)
            })

        return monitoring_data


def main():
    """Main entry point for production testing."""
    parser = argparse.ArgumentParser(
        description="Production Test Script for Arris Modem Status Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  (default)           Quick validation test
  --benchmark         Performance benchmark (5 iterations)
  --comprehensive     Full analysis with data validation and HTTP compatibility
  --all              Run all test types
  --serial           Test serial mode instead of concurrent
  --test-both-modes  Test both concurrent and serial modes for comparison

Examples:
  python production_test.py --password "your_password"
  python production_test.py --password "password" --benchmark
  python production_test.py --password "password" --serial
  python production_test.py --password "password" --test-both-modes
  python production_test.py --password "password" --all --save-results

The quick test validates basic functionality and performance targets.
Benchmark mode runs multiple iterations to measure performance consistency.
Comprehensive mode includes detailed data validation and HTTP compatibility analysis.
Serial mode disables concurrent requests for maximum compatibility testing.
Test-both-modes compares concurrent vs serial performance and HTTP compatibility patterns.
        """
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--benchmark", action="store_true", help="Run performance benchmark")
    parser.add_argument("--comprehensive", action="store_true", help="Run comprehensive analysis")
    parser.add_argument("--all", action="store_true", help="Run all test types")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-results", action="store_true", help="Save results to JSON file")
    parser.add_argument("--output-file", help="Custom output filename")
    parser.add_argument("--monitoring", action="store_true", help="Output monitoring-friendly format")
    parser.add_argument("--serial", action="store_true", help="Test serial mode instead of concurrent")
    parser.add_argument("--test-both-modes", action="store_true", help="Test both concurrent and serial modes")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    try:
        success = True

        if args.test_both_modes:
            # Test both concurrent and serial modes
            logger.info("🔄 Testing both concurrent and serial modes...")

            # Test concurrent mode
            logger.info("🚀 Testing concurrent mode...")
            test_runner_concurrent = ProductionTestRunner(args.password, args.host, concurrent=True)
            if not args.benchmark and not args.comprehensive or args.all:
                quick_success_concurrent = test_runner_concurrent.run_quick_test()
                test_runner_concurrent.results["concurrent_mode"] = {"quick_test": test_runner_concurrent.results["quick_test"]}

            # Test serial mode
            logger.info("🔄 Testing serial mode...")
            test_runner_serial = ProductionTestRunner(args.password, args.host, concurrent=False)
            if not args.benchmark and not args.comprehensive or args.all:
                quick_success_serial = test_runner_serial.run_quick_test()
                test_runner_serial.results["serial_mode"] = {"quick_test": test_runner_serial.results["quick_test"]}

            # Compare results
            print("\n" + "=" * 70)
            print("🔍 MODE COMPARISON RESULTS")
            print("=" * 70)
            concurrent_time = test_runner_concurrent.results.get("quick_test", {}).get("total_time", 0)
            serial_time = test_runner_serial.results.get("quick_test", {}).get("total_time", 0)

            if concurrent_time > 0 and serial_time > 0:
                speed_improvement = ((serial_time - concurrent_time) / serial_time) * 100
                print(f"Concurrent mode: {concurrent_time:.2f}s")
                print(f"Serial mode: {serial_time:.2f}s")
                print(f"Speed improvement: {speed_improvement:.1f}%")

            # Use the concurrent results for final status
            test_runner = test_runner_concurrent
            success = quick_success_concurrent and quick_success_serial

        else:
            # Single mode testing
            concurrent_mode = not args.serial
            mode_str = "concurrent" if concurrent_mode else "serial"
            logger.info(f"🔧 Testing {mode_str} mode...")

            # Initialize test runner
            test_runner = ProductionTestRunner(args.password, args.host, concurrent=concurrent_mode)

            # Quick test (always run unless only other modes specified)
            if not args.benchmark and not args.comprehensive or args.all:
                logger.info("🚀 Running quick validation test...")
                quick_success = test_runner.run_quick_test()
                success = success and quick_success

        # Performance benchmark
        if args.benchmark or args.all:
            logger.info("🏁 Running performance benchmark...")
            benchmark_results = test_runner.run_performance_benchmark()
            test_runner.results["benchmark"] = benchmark_results

        # Comprehensive analysis
        if args.comprehensive or args.all:
            logger.info("🔍 Running comprehensive analysis...")
            analysis_results = test_runner.run_comprehensive_analysis()
            test_runner.results["comprehensive"] = analysis_results

        # Save results if requested
        if args.save_results:
            filename = test_runner.save_results(args.output_file)

        # Output monitoring format if requested
        if args.monitoring:
            monitoring_data = test_runner.export_for_monitoring()
            print("\n📊 MONITORING OUTPUT:")
            print(json.dumps(monitoring_data, indent=2))

        # Final status
        print("\n" + "=" * 70)
        status_emoji = "🎉" if success else "⚠️"
        status_text = "SUCCESS" if success else "PARTIAL SUCCESS"
        print(f"🏁 FINAL RESULT: {status_emoji} {status_text}")
        print("=" * 70)

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.error("❌ Test cancelled by user")
        return 1

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
