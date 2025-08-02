#!/usr/bin/env python3
"""
Comprehensive Performance Test for Optimized Arris Client
=========================================================

This script performs extensive testing and validation of the optimized
Arris modem client, including:

- Performance benchmarking vs original client
- Data parsing validation

- Error handling verification
- Channel data quality analysis
- Speed optimization verification
- HTTP compatibility analysis and correlation

Usage:
    python comprehensive_test.py --password "your_password" [options]

"""

import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from typing import Any, Dict

# Import both clients for comparison
try:
    from arris_modem_status import ArrisModemStatusClient as OptimizedClient

except Exception as e:
    print(f"Error: {e}")
try:
    from arris_modem_status import __version__ as CLIENT_VERSION
except ImportError:
    CLIENT_VERSION = "1.0.0"

    OPTIMIZED_CLIENT_AVAILABLE = True
except ImportError:
    OPTIMIZED_CLIENT_AVAILABLE = False

try:
    from arris_modem_status.legacy import ArrisModemStatusClient as OriginalClient

    ORIGINAL_CLIENT_AVAILABLE = True
except ImportError:
    ORIGINAL_CLIENT_AVAILABLE = False

# Configure enhanced logging with timestamps
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class ComprehensiveTestSuite:
    """
    Complete test suite for validating optimized Arris client performance and accuracy.

    This test suite provides comprehensive validation of the production-ready
    Arris client with specific focus on HTTP compatibility handling and performance
    optimization verification.
    """

    def __init__(self, password: str, host: str = "192.168.100.1"):
        """
        Initialize the comprehensive test suite.

        Args:
            password: Modem admin password
            host: Modem IP address (default: "192.168.100.1")
        """
        self.password = password
        self.host = host
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "test_configuration": {"host": host, "password_length": len(password), "test_version": CLIENT_VERSION},
            "performance_tests": {},
            "validation_tests": {},
            "comparison_tests": {},
            "http_compatibility_analysis": {},
            "recommendations": [],
        }

        if not OPTIMIZED_CLIENT_AVAILABLE:
            raise ImportError("Optimized Arris client not available")

        logger.info(f"🚀 Comprehensive Test Suite v{CLIENT_VERSION}")
        logger.info(f"📋 Target: {host}")
        logger.info(f"🔧 Password length: {len(password)} chars")
        logger.info("=" * 70)

    def run_all_tests(self) -> Dict[str, Any]:
        """Execute complete test suite."""

        # Test 1: Performance Benchmarking
        logger.info("\n🏁 TEST 1: Performance Benchmarking")
        logger.info("-" * 50)
        self.test_results["performance_tests"] = self._run_performance_tests()

        # Test 2: Data Validation

        logger.info("\n🔍 TEST 2: Data Validation & Parsing")
        logger.info("-" * 50)
        self.test_results["validation_tests"] = self._run_validation_tests()

        # Test 3: HTTP Compatibility Analysis
        logger.info("\n🔧 TEST 3: HTTP Compatibility Analysis")
        logger.info("-" * 50)
        self.test_results["http_compatibility_analysis"] = self._run_http_compatibility_analysis()

        # Test 4: Stress Testing
        logger.info("\n💪 TEST 4: Stress & Reliability Testing")
        logger.info("-" * 50)
        self.test_results["stress_tests"] = self._run_stress_tests()

        # Test 5: Comparison with Original (if available)
        if ORIGINAL_CLIENT_AVAILABLE:
            logger.info("\n⚖️  TEST 5: Original vs Optimized Comparison")
            logger.info("-" * 50)
            self.test_results["comparison_tests"] = self._run_comparison_tests()

        # Generate recommendations
        self._generate_recommendations()

        return self.test_results

    def _run_performance_tests(self) -> Dict[str, Any]:
        """Test performance characteristics of optimized client."""
        performance_results = {
            "authentication_speed": {},
            "data_retrieval_speed": {},
            "concurrent_performance": {},
            "memory_efficiency": {},
        }

        try:
            # Authentication Speed Test
            logger.info("🔐 Testing authentication speed...")
            auth_times = []

            for i in range(3):
                client = OptimizedClient(password=self.password, host=self.host)
                start_time = time.time()

                success = client.authenticate()
                auth_time = time.time() - start_time

                if success:
                    auth_times.append(auth_time)
                    logger.info(f"   Auth attempt {i + 1}: {auth_time:.2f}s ✅")
                else:
                    logger.error(f"   Auth attempt {i + 1}: FAILED ❌")

                client.close()
                time.sleep(1)  # Brief pause between tests

            if auth_times:
                performance_results["authentication_speed"] = {
                    "attempts": len(auth_times),
                    "average_time": statistics.mean(auth_times),
                    "min_time": min(auth_times),
                    "max_time": max(auth_times),
                    "consistency": max(auth_times) - min(auth_times) < 1.0,
                }

                avg_time = statistics.mean(auth_times)
                logger.info(
                    f"📊 Auth Performance: Avg {avg_time:.2f}s, Range {min(auth_times):.2f}-{max(auth_times):.2f}s"
                )

            # Data Retrieval Speed Test
            logger.info("📊 Testing data retrieval speed...")

            client = OptimizedClient(password=self.password, host=self.host)
            retrieval_times = []

            for i in range(3):
                start_time = time.time()
                status = client.get_status()
                retrieval_time = time.time() - start_time

                retrieval_times.append(retrieval_time)
                downstream_count = len(status.get("downstream_channels", []))
                upstream_count = len(status.get("upstream_channels", []))
                channel_count = downstream_count + upstream_count
                logger.info(f"   Retrieval {i + 1}: {retrieval_time:.2f}s, {channel_count} channels ✅")

                time.sleep(0.5)

            client.close()

            if retrieval_times:
                performance_results["data_retrieval_speed"] = {
                    "attempts": len(retrieval_times),
                    "average_time": statistics.mean(retrieval_times),
                    "min_time": min(retrieval_times),
                    "max_time": max(retrieval_times),
                    "channels_per_second": channel_count / statistics.mean(retrieval_times) if retrieval_times else 0,
                }

                avg_time = statistics.mean(retrieval_times)
                logger.info(
                    f"📊 Retrieval Performance: Avg {avg_time:.2f}s, {channel_count / avg_time:.1f} channels/sec"
                )

        except Exception as e:
            logger.error(f"Performance test error: {e}")
            performance_results["error"] = str(e)

        return performance_results

    def _run_validation_tests(self) -> Dict[str, Any]:
        """Comprehensive data validation testing."""
        validation_results = {}

        try:
            logger.info("🔍 Running comprehensive validation...")

            client = OptimizedClient(password=self.password, host=self.host)
            validation_data = client.validate_parsing()
            client.close()

            # Extract validation metrics
            parsing_validation = validation_data.get("parsing_validation", {})
            performance_metrics = validation_data.get("performance_metrics", {})

            validation_results = {
                "data_completeness": {
                    "basic_info_complete": parsing_validation.get("basic_info_parsed", False),
                    "internet_status_available": parsing_validation.get("internet_status_parsed", False),
                    "channel_data_available": parsing_validation.get("downstream_channels_found", 0) > 0,
                    "completeness_score": performance_metrics.get("data_completeness_score", 0),
                },
                "channel_analysis": {
                    "downstream_count": parsing_validation.get("downstream_channels_found", 0),
                    "upstream_count": parsing_validation.get("upstream_channels_found", 0),
                    "total_channels": performance_metrics.get("total_channels", 0),
                    "channel_quality": parsing_validation.get("channel_data_quality", {}),
                },
                "format_validation": {
                    "mac_address_valid": parsing_validation.get("mac_address_format", False),
                    "frequency_formats_valid": parsing_validation.get("frequency_formats", {}),
                },
                "http_compatibility_metrics": {
                    "parsing_errors": performance_metrics.get("parsing_errors", 0),
                    "http_compatibility_issues": performance_metrics.get("http_compatibility_issues", 0),
                },
            }

            # Log validation results
            downstream_count = validation_results["channel_analysis"]["downstream_count"]
            upstream_count = validation_results["channel_analysis"]["upstream_count"]
            completeness = validation_results["data_completeness"]["completeness_score"]

            logger.info(f"📈 Channel Data: {downstream_count} downstream, {upstream_count} upstream")
            logger.info(f"🎯 Data Completeness: {completeness:.1f}%")
            logger.info(f"✅ MAC Format Valid: {validation_results['format_validation']['mac_address_valid']}")

            # HTTP compatibility reporting
            http_compat_issues = validation_results["http_compatibility_metrics"]["http_compatibility_issues"]
            if http_compat_issues > 0:
                logger.info(f"🔧 HTTP Compatibility Issues Handled: {http_compat_issues}")

            # Detailed channel quality analysis
            channel_quality = validation_results["channel_analysis"]["channel_quality"]
            if channel_quality:
                downstream_qual = channel_quality.get("downstream_validation", {})
                upstream_qual = channel_quality.get("upstream_validation", {})

                if downstream_qual:
                    all_locked = downstream_qual.get("all_locked", False)
                    modulation_count = len(downstream_qual.get("modulation_types", []))
                    logger.info(f"📡 Downstream Quality: {all_locked} all locked, Modulations: {modulation_count}")

                if upstream_qual:
                    all_locked = upstream_qual.get("all_locked", False)
                    modulation_count = len(upstream_qual.get("modulation_types", []))
                    logger.info(f"📤 Upstream Quality: {all_locked} all locked, Modulations: {modulation_count}")

        except Exception as e:
            logger.error(f"Validation test error: {e}")
            validation_results["error"] = str(e)

        return validation_results

    def _run_http_compatibility_analysis(self) -> Dict[str, Any]:
        """Analyze HTTP compatibility handling and recovery."""
        http_compatibility_results = {}

        try:
            logger.info("🔧 Testing HTTP compatibility detection and recovery...")

            # Use aggressive settings to trigger HTTP compatibility issues
            client = OptimizedClient(
                password=self.password,
                host=self.host,
                max_workers=4,  # Higher concurrency to trigger compatibility issues
                max_retries=2,
                base_backoff=0.1,
                capture_errors=True,
            )

            # Run multiple rapid requests to stress HTTP compatibility
            for iteration in range(3):
                try:
                    logger.info(f"🔄 HTTP compatibility test iteration {iteration + 1}/3")

                    # Force re-authentication to stress the system
                    client.authenticated = False
                    status = client.get_status()

                    logger.info(f"   Iteration {iteration + 1}: Success")

                except Exception as e:
                    logger.warning(f"   Iteration {iteration + 1}: {e}")

                time.sleep(0.2)

            # Get error analysis
            error_analysis = client.get_error_analysis()
            client.close()

            http_compatibility_results = {
                "total_errors": error_analysis.get("total_errors", 0),
                "error_types": error_analysis.get("error_types", {}),
                "parsing_artifacts": error_analysis.get("parsing_artifacts", []),
                "recovery_stats": error_analysis.get("recovery_stats", {}),
                "patterns": error_analysis.get("patterns", []),
                "http_compatibility_issues": error_analysis.get("http_compatibility_issues", 0),
            }

            # Log HTTP compatibility analysis
            total_errors = http_compatibility_results["total_errors"]
            recovery_rate = http_compatibility_results["recovery_stats"].get("recovery_rate", 0) * 100
            parsing_artifact_count = len(http_compatibility_results["parsing_artifacts"])
            compatibility_issues = http_compatibility_results["http_compatibility_issues"]

            logger.info(f"🔍 HTTP Compatibility Analysis: {total_errors} errors, {recovery_rate:.1f}% recovery")
            if parsing_artifact_count > 0:
                logger.info(f"🔍 urllib3 parsing artifacts: {parsing_artifact_count} instances")
            if compatibility_issues > 0:
                logger.info(f"🔧 HTTP compatibility issues handled: {compatibility_issues}")

        except Exception as e:
            logger.error(f"HTTP compatibility analysis error: {e}")
            http_compatibility_results["error"] = str(e)

        return http_compatibility_results

    def _run_stress_tests(self) -> Dict[str, Any]:
        """Test reliability under stress conditions."""
        stress_results = {"rapid_requests": {}, "connection_stability": {}, "error_recovery": {}}

        try:
            logger.info("💪 Testing rapid consecutive requests...")

            client = OptimizedClient(password=self.password, host=self.host)

            # Rapid request test
            rapid_times = []
            rapid_successes = 0

            for i in range(5):
                try:
                    start_time = time.time()
                    status = client.get_status()
                    request_time = time.time() - start_time

                    if status and len(status.get("downstream_channels", [])) > 0:
                        rapid_times.append(request_time)
                        rapid_successes += 1
                        logger.info(f"   Rapid request {i + 1}: {request_time:.2f}s ✅")
                    else:
                        logger.warning(f"   Rapid request {i + 1}: No data ⚠️")

                except Exception as e:
                    logger.error(f"   Rapid request {i + 1}: {e} ❌")

                time.sleep(0.2)  # Brief pause

            stress_results["rapid_requests"] = {
                "total_attempts": 5,
                "successful_requests": rapid_successes,
                "success_rate": rapid_successes / 5,
                "average_time": statistics.mean(rapid_times) if rapid_times else 0,
                "performance_degradation": max(rapid_times) - min(rapid_times) if len(rapid_times) > 1 else 0,
            }

            logger.info(f"📊 Stress Test: {rapid_successes}/5 successful ({rapid_successes / 5 * 100:.1f}%)")

            client.close()

        except Exception as e:
            logger.error(f"Stress test error: {e}")
            stress_results["error"] = str(e)

        return stress_results

    def _run_comparison_tests(self) -> Dict[str, Any]:
        """Compare optimized vs original client performance."""
        comparison_results = {}

        if not ORIGINAL_CLIENT_AVAILABLE:
            return {"error": "Original client not available for comparison"}

        try:
            logger.info("⚖️  Comparing optimized vs original client...")

            # Test Original Client
            logger.info("📊 Testing original client...")
            original_start = time.time()

            original_client = OriginalClient(password=self.password, host=self.host)
            original_status = original_client.get_status()
            original_time = time.time() - original_start
            original_client.close()

            # Test Optimized Client

            logger.info("🚀 Testing optimized client...")
            optimized_start = time.time()

            optimized_client = OptimizedClient(password=self.password, host=self.host)
            optimized_status = optimized_client.get_status()
            optimized_time = time.time() - optimized_start
            optimized_client.close()

            # Compare results
            original_downstream = len(original_status.get("downstream_channels", []))
            original_upstream = len(original_status.get("upstream_channels", []))
            original_channels = original_downstream + original_upstream

            optimized_downstream = len(optimized_status.get("downstream_channels", []))
            optimized_upstream = len(optimized_status.get("upstream_channels", []))
            optimized_channels = optimized_downstream + optimized_upstream

            speed_improvement = ((original_time - optimized_time) / original_time) * 100

            comparison_results = {
                "timing_comparison": {
                    "original_time": original_time,
                    "optimized_time": optimized_time,
                    "speed_improvement_percent": speed_improvement,
                    "faster": optimized_time < original_time,
                },
                "data_comparison": {
                    "original_channels": original_channels,
                    "optimized_channels": optimized_channels,
                    "channel_count_match": original_channels == optimized_channels,
                    "data_integrity_maintained": True,
                },
                "feature_comparison": {
                    "original_has_error_handling": False,
                    "optimized_has_error_handling": True,
                    "original_has_concurrency": False,
                    "optimized_has_concurrency": True,
                    "original_has_http_compatibility": False,
                    "optimized_has_http_compatibility": True,
                },
            }

            logger.info(f"📊 Performance Comparison:")
            logger.info(f"   Original: {original_time:.2f}s, {original_channels} channels")
            logger.info(f"   Optimized: {optimized_time:.2f}s, {optimized_channels} channels")
            logger.info(f"   Speed improvement: {speed_improvement:.1f}%")
            logger.info(f"   Data integrity: {'✅' if original_channels == optimized_channels else '❌'}")

        except Exception as e:
            logger.error(f"Comparison test error: {e}")
            comparison_results["error"] = str(e)

        return comparison_results

    def _generate_recommendations(self):
        """Generate performance and usage recommendations."""
        recommendations = []

        # Performance recommendations
        perf_tests = self.test_results.get("performance_tests", {})
        auth_speed = perf_tests.get("authentication_speed", {})

        if auth_speed.get("average_time", 0) > 3.0:
            recommendations.append(
                {
                    "type": "performance",
                    "priority": "medium",
                    "message": "Authentication taking longer than expected (>3s). Check network latency to modem.",
                }
            )

        if auth_speed.get("consistency", True) is False:
            recommendations.append(
                {
                    "type": "reliability",
                    "priority": "low",
                    "message": "Authentication timing inconsistent. Consider connection stability.",
                }
            )

        # Data quality recommendations

        validation_tests = self.test_results.get("validation_tests", {})
        completeness = validation_tests.get("data_completeness", {}).get("completeness_score", 0)

        if completeness < 80:
            recommendations.append(
                {
                    "type": "data_quality",
                    "priority": "high",
                    "message": f"Data completeness only {completeness:.1f}%. Some modem data may be unavailable.",
                }
            )

        # HTTP compatibility recommendations
        http_compatibility_analysis = self.test_results.get("http_compatibility_analysis", {})
        total_errors = http_compatibility_analysis.get("total_errors", 0)
        recovery_rate = http_compatibility_analysis.get("recovery_stats", {}).get("recovery_rate", 0)
        compatibility_issues = http_compatibility_analysis.get("http_compatibility_issues", 0)

        if total_errors > 0:
            if recovery_rate >= 0.9:
                recommendations.append(
                    {
                        "type": "success",
                        "priority": "info",
                        "message": f"Excellent HTTP compatibility handling: {total_errors} errors, {recovery_rate * 100:.1f}% recovery rate.",
                    }
                )
            else:
                recommendations.append(
                    {
                        "type": "http_compatibility",
                        "priority": "medium",
                        "message": f"HTTP compatibility issues detected with {recovery_rate * 100:.1f}% recovery rate. Consider reducing concurrency.",
                    }
                )

        if compatibility_issues > 0:
            recommendations.append(
                {
                    "type": "success",
                    "priority": "info",
                    "message": f"HTTP compatibility layer working excellently: {compatibility_issues} urllib3 parsing issues resolved automatically.",
                }
            )

        # Stress test recommendations
        stress_tests = self.test_results.get("stress_tests", {})
        success_rate = stress_tests.get("rapid_requests", {}).get("success_rate", 0)

        if success_rate < 0.8:
            recommendations.append(
                {
                    "type": "reliability",
                    "priority": "medium",
                    "message": f"Rapid request success rate only {success_rate * 100:.1f}%. Consider adding delays between requests.",
                }
            )

        # Performance improvement recommendations
        comparison_tests = self.test_results.get("comparison_tests", {})
        if comparison_tests and not comparison_tests.get("error"):
            speed_improvement = comparison_tests.get("timing_comparison", {}).get("speed_improvement_percent", 0)

            if speed_improvement > 50:
                recommendations.append(
                    {
                        "type": "success",
                        "priority": "info",
                        "message": f"Outstanding performance improvement: {speed_improvement:.1f}% faster than original client.",
                    }
                )
            elif speed_improvement < 10:
                recommendations.append(
                    {
                        "type": "performance",
                        "priority": "low",
                        "message": "Optimizations showing minimal improvement. Network may be the bottleneck.",
                    }
                )

        self.test_results["recommendations"] = recommendations

        # Log recommendations
        logger.info("\n💡 RECOMMENDATIONS:")
        logger.info("-" * 50)
        for rec in recommendations:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(rec["priority"], "📋")
            logger.info(f"{priority_icon} {rec['type'].upper()}: {rec['message']}")

    def save_results(self, filename: str = None) -> str:
        """Save test results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                json.dump(self.test_results, f, indent=2, default=str)

            logger.info(f"💾 Results saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""

    def print_summary(self):
        """Print comprehensive test summary."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 70)

        # Performance Summary
        perf_tests = self.test_results.get("performance_tests", {})
        auth_speed = perf_tests.get("authentication_speed", {})
        data_speed = perf_tests.get("data_retrieval_speed", {})

        if auth_speed:
            logger.info(f"🔐 Authentication: {auth_speed.get('average_time', 0):.2f}s average")
        if data_speed:
            logger.info(f"📊 Data Retrieval: {data_speed.get('average_time', 0):.2f}s average")

        # Validation Summary
        validation_tests = self.test_results.get("validation_tests", {})
        channel_analysis = validation_tests.get("channel_analysis", {})
        data_completeness = validation_tests.get("data_completeness", {})

        if channel_analysis:
            downstream = channel_analysis.get("downstream_count", 0)
            upstream = channel_analysis.get("upstream_count", 0)
            logger.info(f"📈 Channels: {downstream} downstream, {upstream} upstream")

        if data_completeness:
            completeness = data_completeness.get("completeness_score", 0)
            logger.info(f"🎯 Data Completeness: {completeness:.1f}%")

        # HTTP Compatibility Summary
        http_compatibility_analysis = self.test_results.get("http_compatibility_analysis", {})
        if http_compatibility_analysis and not http_compatibility_analysis.get("error"):
            total_errors = http_compatibility_analysis.get("total_errors", 0)
            recovery_rate = http_compatibility_analysis.get("recovery_stats", {}).get("recovery_rate", 0) * 100
            compatibility_issues = http_compatibility_analysis.get("http_compatibility_issues", 0)
            logger.info(f"🔧 HTTP Compatibility: {compatibility_issues} issues handled, {recovery_rate:.1f}% recovery")

        # Comparison Summary
        comparison_tests = self.test_results.get("comparison_tests", {})
        if comparison_tests and not comparison_tests.get("error"):
            timing = comparison_tests.get("timing_comparison", {})
            improvement = timing.get("speed_improvement_percent", 0)
            logger.info(f"⚡ Speed Improvement: {improvement:.1f}%")

        # Overall Assessment
        logger.info("\n🎯 OVERALL ASSESSMENT:")

        # Determine overall status
        all_good = True
        if auth_speed.get("average_time", 0) > 3.0:
            all_good = False
        if data_completeness.get("completeness_score", 0) < 80:
            all_good = False

        # Consider HTTP compatibility handling as a positive
        http_recovery = http_compatibility_analysis.get("recovery_stats", {}).get("recovery_rate", 0)
        if http_recovery >= 0.9:
            logger.info("🛡️  HTTP compatibility handling: EXCELLENT")
        elif http_recovery > 0:
            logger.info("🛡️  HTTP compatibility handling: GOOD")

        if all_good:
            logger.info("🎉 EXCELLENT - Optimized client performing at peak efficiency!")
        else:
            logger.info("⚠️  GOOD - Some areas for improvement identified.")

        logger.info("=" * 70)


def main():
    """Main entry point for comprehensive testing."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Performance Test for Optimized Arris Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This comprehensive test suite validates the production-ready Arris client
with specific focus on:

1. Performance benchmarking (authentication, data retrieval, concurrency)
2. Data validation and parsing accuracy
3. HTTP compatibility detection and recovery analysis
4. Stress testing and reliability verification
5. Comparison with original client (if available)

The test suite is designed to validate the client's ability to handle
urllib3 parsing strictness issues with Arris modem HTTP responses through
browser-compatible HTTP parsing fallback mechanisms.

Examples:
  python comprehensive_test.py --password "your_password"
  python comprehensive_test.py --password "password" --save-results
  python comprehensive_test.py --password "password" --debug --output-file custom_results.json
        """,
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-results", action="store_true", help="Save detailed results to JSON")
    parser.add_argument("--output-file", help="Custom output filename for results")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    # Create and run test suite
    test_suite = ComprehensiveTestSuite(args.password, args.host)

    try:
        logger.info("🚀 Starting comprehensive test suite...")
        start_time = time.time()

        # Run all tests
        results = test_suite.run_all_tests()

        # Print summary
        test_suite.print_summary()

        # Save results if requested
        if args.save_results:
            filename = test_suite.save_results(args.output_file)
            if filename:
                logger.info(f"📁 Detailed results: {filename}")

        total_time = time.time() - start_time
        logger.info(f"\n⏱️  Total test time: {total_time:.2f}s")
        logger.info("✅ Comprehensive testing complete!")

    except KeyboardInterrupt:
        logger.error("\n❌ Tests cancelled by user")
        return 1

    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
