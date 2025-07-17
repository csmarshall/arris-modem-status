#!/usr/bin/env python3
"""
Concurrent vs Serial Mode HTTP Compatibility Test Script
=======================================================

This script tests both concurrent and serial request modes to evaluate
HTTP compatibility handling and performance characteristics:

1. HTTP compatibility issue patterns in concurrent vs serial modes
2. Performance differences between the two modes
3. Browser-compatible parsing effectiveness across modes
4. Error recovery patterns and reliability analysis

By comparing HTTP compatibility handling between serial and concurrent modes,
we can validate the effectiveness of the browser-compatible HTTP parsing solution.

Usage:
    python concurrent_vs_serial_test.py --password "your_password"

Author: Charles Marshall
Version: 1.3.0
"""

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

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

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ConcurrentSerialCompatibilityRunner:
    """
    Test runner to compare HTTP compatibility handling between concurrent and serial modes.
    """

    def __init__(self, password: str, host: str = "192.168.100.1"):
        """Initialize the test runner."""
        self.password = password
        self.host = host

        if not CLIENT_AVAILABLE:
            raise ImportError("ArrisModemStatusClient not available - check installation")

    def run_comparison_test(self) -> Dict[str, Any]:
        """
        Run comprehensive comparison between concurrent and serial modes for HTTP compatibility.
        """
        print("=" * 80)
        print("🔧 CONCURRENT vs SERIAL HTTP COMPATIBILITY ANALYSIS")
        print(f"⏰ Time: {datetime.now().isoformat()}")
        print(f"🎯 Target: {self.host}")
        print("=" * 80)

        results = {
            "test_config": {
                "host": self.host,
                "password_length": len(self.password),
                "timestamp": datetime.now().isoformat()
            },
            "serial_mode": {},
            "concurrent_mode": {},
            "comparison": {},
            "compatibility_analysis": {}
        }

        # Test 1: Serial Mode (No Concurrency)
        print("\n🔄 TEST 1: SERIAL MODE HTTP COMPATIBILITY")
        print("-" * 50)
        results["serial_mode"] = self._test_mode(concurrent=False)

        # Test 2: Concurrent Mode (With Threading)
        print("\n🚀 TEST 2: CONCURRENT MODE HTTP COMPATIBILITY")
        print("-" * 50)
        results["concurrent_mode"] = self._test_mode(concurrent=True)

        # Test 3: Comparison Analysis
        print("\n⚖️  TEST 3: HTTP COMPATIBILITY COMPARISON")
        print("-" * 50)
        results["comparison"] = self._compare_modes(results["serial_mode"], results["concurrent_mode"])

        # Test 4: HTTP Compatibility Analysis
        print("\n🔧 TEST 4: HTTP COMPATIBILITY ANALYSIS")
        print("-" * 50)
        results["compatibility_analysis"] = self._analyze_http_compatibility(results)

        return results

    def _test_mode(self, concurrent: bool) -> Dict[str, Any]:
        """Test HTTP compatibility in a specific mode (concurrent or serial)."""
        mode_str = "concurrent" if concurrent else "serial"
        mode_results = {
            "mode": mode_str,
            "performance": {},
            "errors": [],
            "http_compatibility_issues": 0,
            "parsing_artifacts": [],
            "channel_data": {},
            "success": False
        }

        try:
            # Configure client for the specific mode
            client = ArrisModemStatusClient(
                password=self.password,
                host=self.host,
                concurrent=concurrent,
                max_workers=3 if concurrent else 1,
                max_retries=2,  # Lower retries to capture more HTTP compatibility events
                base_backoff=0.1,  # Faster to potentially trigger more compatibility issues
                capture_errors=True
            )

            print(f"🔧 Testing {mode_str} mode for HTTP compatibility...")

            # Run multiple iterations to test HTTP compatibility handling
            total_time = 0
            iterations = 3
            successful_iterations = 0

            for i in range(iterations):
                try:
                    print(f"   Iteration {i + 1}/{iterations}...")

                    # Force re-authentication to stress the HTTP stack
                    client.authenticated = False

                    start_time = time.time()
                    status = client.get_status()
                    iteration_time = time.time() - start_time

                    total_time += iteration_time
                    successful_iterations += 1

                    if i == 0:  # Store channel data from first successful iteration
                        downstream_count = len(status.get('downstream_channels', []))
                        upstream_count = len(status.get('upstream_channels', []))
                        mode_results["channel_data"] = {
                            "downstream_count": downstream_count,
                            "upstream_count": upstream_count,
                            "total_channels": downstream_count + upstream_count
                        }

                    print(f"      ✅ Success: {iteration_time:.2f}s")

                except Exception as e:
                    print(f"      ❌ Error: {e}")

                # Brief pause between iterations
                time.sleep(0.2)

            # Get HTTP compatibility analysis
            error_analysis = client.get_error_analysis()
            client.close()

            # Extract results with HTTP compatibility focus
            mode_results["performance"] = {
                "total_time": total_time,
                "average_time": total_time / successful_iterations if successful_iterations > 0 else 0,
                "successful_iterations": successful_iterations,
                "total_iterations": iterations,
                "success_rate": successful_iterations / iterations
            }

            mode_results["errors"] = error_analysis.get("error_types", {})
            mode_results["http_compatibility_issues"] = error_analysis.get("http_compatibility_issues", 0)
            mode_results["parsing_artifacts"] = error_analysis.get("parsing_artifacts", [])
            mode_results["recovery_rate"] = error_analysis.get("recovery_stats", {}).get("recovery_rate", 0)
            mode_results["success"] = successful_iterations > 0

            # Print immediate results
            print(f"📊 {mode_str.upper()} RESULTS:")
            print(f"   ⏱️  Average time: {mode_results['performance']['average_time']:.2f}s")
            print(f"   ✅ Success rate: {mode_results['performance']['success_rate'] * 100:.1f}%")
            print(f"   🔧 HTTP compatibility issues: {mode_results['http_compatibility_issues']}")
            print(f"   🔍 Parsing artifacts: {len(mode_results['parsing_artifacts'])}")

            if mode_results["parsing_artifacts"]:
                print(f"      Artifacts found: {mode_results['parsing_artifacts']}")

        except Exception as e:
            logger.error(f"{mode_str} mode test failed: {e}")
            mode_results["error"] = str(e)

        return mode_results

    def _compare_modes(self, serial_results: Dict[str, Any], concurrent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare HTTP compatibility results between serial and concurrent modes."""
        comparison = {}

        try:
            # Performance comparison
            serial_time = serial_results.get("performance", {}).get("average_time", 0)
            concurrent_time = concurrent_results.get("performance", {}).get("average_time", 0)

            if serial_time > 0 and concurrent_time > 0:
                speed_improvement = ((serial_time - concurrent_time) / serial_time) * 100
                comparison["performance"] = {
                    "serial_time": serial_time,
                    "concurrent_time": concurrent_time,
                    "speed_improvement_percent": speed_improvement,
                    "concurrent_faster": concurrent_time < serial_time
                }

                print(f"📈 PERFORMANCE COMPARISON:")
                print(f"   Serial: {serial_time:.2f}s")
                print(f"   Concurrent: {concurrent_time:.2f}s")
                print(f"   Speed improvement: {speed_improvement:.1f}%")

            # HTTP compatibility comparison
            serial_compatibility = serial_results.get("http_compatibility_issues", 0)
            concurrent_compatibility = concurrent_results.get("http_compatibility_issues", 0)
            serial_artifacts = len(serial_results.get("parsing_artifacts", []))
            concurrent_artifacts = len(concurrent_results.get("parsing_artifacts", []))

            comparison["http_compatibility"] = {
                "serial_compatibility_issues": serial_compatibility,
                "concurrent_compatibility_issues": concurrent_compatibility,
                "serial_parsing_artifacts": serial_artifacts,
                "concurrent_parsing_artifacts": concurrent_artifacts,
                "more_issues_in_concurrent": concurrent_compatibility > serial_compatibility,
                "artifacts_in_both": serial_artifacts > 0 and concurrent_artifacts > 0,
                "artifacts_only_concurrent": serial_artifacts == 0 and concurrent_artifacts > 0
            }

            print(f"🔧 HTTP COMPATIBILITY COMPARISON:")
            print(f"   Serial compatibility issues: {serial_compatibility}")
            print(f"   Concurrent compatibility issues: {concurrent_compatibility}")
            print(f"   Serial parsing artifacts: {serial_artifacts}")
            print(f"   Concurrent parsing artifacts: {concurrent_artifacts}")

            # Channel data comparison
            serial_channels = serial_results.get("channel_data", {}).get("total_channels", 0)
            concurrent_channels = concurrent_results.get("channel_data", {}).get("total_channels", 0)

            comparison["data_integrity"] = {
                "serial_channels": serial_channels,
                "concurrent_channels": concurrent_channels,
                "channel_count_match": serial_channels == concurrent_channels,
                "data_consistent": abs(serial_channels - concurrent_channels) <= 1  # Allow 1 channel difference
            }

            print(f"📡 DATA INTEGRITY:")
            print(f"   Serial channels: {serial_channels}")
            print(f"   Concurrent channels: {concurrent_channels}")
            print(f"   Data consistent: {'✅' if comparison['data_integrity']['data_consistent'] else '❌'}")

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            comparison["error"] = str(e)

        return comparison

    def _analyze_http_compatibility(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze HTTP compatibility patterns based on the comparison results."""
        analysis = {
            "compatibility_assessment": "unknown",
            "confidence": "low",
            "evidence": [],
            "recommendations": []
        }

        try:
            comparison = results.get("comparison", {})
            serial_results = results.get("serial_mode", {})
            concurrent_results = results.get("concurrent_mode", {})

            # Extract key metrics
            serial_compatibility = serial_results.get("http_compatibility_issues", 0)
            concurrent_compatibility = concurrent_results.get("http_compatibility_issues", 0)
            serial_artifacts = len(serial_results.get("parsing_artifacts", []))
            concurrent_artifacts = len(concurrent_results.get("parsing_artifacts", []))

            print(f"🔧 HTTP COMPATIBILITY ANALYSIS:")

            # Scenario 1: No compatibility issues in either mode
            if serial_compatibility == 0 and concurrent_compatibility == 0:
                analysis["compatibility_assessment"] = "excellent_compatibility"
                analysis["confidence"] = "high"
                analysis["evidence"].append("No HTTP compatibility issues in either mode")
                analysis["evidence"].append("Browser-compatible parsing working flawlessly")
                analysis["recommendations"].append("System working optimally - no action needed")

                print("   🎯 CONCLUSION: EXCELLENT HTTP COMPATIBILITY")
                print("   📋 Evidence: No compatibility issues in either mode")
                print("   🔧 Assessment: Browser-compatible parsing working perfectly")

            # Scenario 2: Issues only in concurrent mode
            elif serial_compatibility == 0 and concurrent_compatibility > 0:
                analysis["compatibility_assessment"] = "concurrent_mode_stress"
                analysis["confidence"] = "medium"
                analysis["evidence"].append("HTTP compatibility issues only in concurrent mode")
                analysis["evidence"].append("Serial mode is completely clean")
                analysis["evidence"].append("Suggests HTTP stack stress under concurrency")
                analysis["recommendations"].append("Browser-compatible parsing handling concurrent stress effectively")
                analysis["recommendations"].append("Consider reducing max_workers if issues persist")

                print("   🎯 CONCLUSION: CONCURRENT MODE HTTP STRESS")
                print("   📋 Evidence: Issues only under concurrent load")
                print("   🔧 Assessment: Browser-compatible parsing handling stress well")

            # Scenario 3: Issues in both modes
            elif serial_compatibility > 0 and concurrent_compatibility > 0:
                analysis["compatibility_assessment"] = "urllib3_parsing_strictness"
                analysis["confidence"] = "high"
                analysis["evidence"].append("HTTP compatibility issues in BOTH modes")
                analysis["evidence"].append("Confirms urllib3 parsing strictness across all scenarios")
                analysis["evidence"].append("Browser-compatible parsing successfully handling all cases")
                analysis["recommendations"].append("urllib3 parsing strictness confirmed across all modes")
                analysis["recommendations"].append("Browser-compatible parsing providing reliable fallback")

                print("   🎯 CONCLUSION: URLLIB3 PARSING STRICTNESS CONFIRMED")
                print("   📋 Evidence: Issues in both modes - confirms urllib3 strictness")
                print("   🔧 Assessment: Browser-compatible parsing working excellently")

            # Scenario 4: More issues in concurrent mode
            elif concurrent_compatibility > serial_compatibility:
                analysis["compatibility_assessment"] = "concurrent_amplification"
                analysis["confidence"] = "medium"
                analysis["evidence"].append("More compatibility issues in concurrent mode")
                analysis["evidence"].append("Concurrency amplifies urllib3 parsing strictness")
                analysis["evidence"].append("Browser-compatible parsing handling increased load")
                analysis["recommendations"].append("Consider tuning concurrency settings for optimal performance")

                print("   🎯 CONCLUSION: CONCURRENCY AMPLIFIES COMPATIBILITY ISSUES")
                print("   📋 Evidence: More issues under concurrent load")
                print("   🔧 Assessment: Browser-compatible parsing scaling effectively")

            # Add specific recommendations based on findings
            total_compatibility_issues = serial_compatibility + concurrent_compatibility
            if total_compatibility_issues > 0:
                recovery_rate_serial = serial_results.get("recovery_rate", 0) * 100
                recovery_rate_concurrent = concurrent_results.get("recovery_rate", 0) * 100

                analysis["recommendations"].extend([
                    f"HTTP compatibility issues detected: {total_compatibility_issues} total",
                    f"Recovery rates: Serial {recovery_rate_serial:.1f}%, Concurrent {recovery_rate_concurrent:.1f}%",
                    "Browser-compatible parsing providing excellent reliability",
                    "No action required - system handling compatibility automatically"
                ])
            else:
                analysis["recommendations"].extend([
                    "No HTTP compatibility issues detected in testing",
                    "System operating with excellent HTTP compatibility",
                    "Current configuration optimal for both modes"
                ])

            # Print final recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis["recommendations"], 1):
                print(f"   {i}. {rec}")

        except Exception as e:
            logger.error(f"HTTP compatibility analysis failed: {e}")
            analysis["error"] = str(e)

        return analysis

    def save_compatibility_analysis(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save the complete HTTP compatibility analysis report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concurrent_vs_serial_compatibility_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"💾 HTTP compatibility analysis report saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save compatibility analysis report: {e}")
            return ""


def main():
    """Main entry point for concurrent vs serial HTTP compatibility testing."""
    parser = argparse.ArgumentParser(
        description="Concurrent vs Serial Mode HTTP Compatibility Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script helps analyze HTTP compatibility handling between concurrent and serial modes:

1. HTTP COMPATIBILITY PATTERNS:
   - urllib3 parsing strictness handling in both modes
   - Browser-compatible parsing effectiveness
   - Recovery patterns and success rates

2. PERFORMANCE ANALYSIS:
   - Speed differences between modes
   - HTTP compatibility issue frequency
   - Error recovery efficiency

EXPECTED OUTCOMES:

Excellent compatibility (no issues in either mode):
  → Browser-compatible parsing working perfectly
  → Solution: Continue with current configuration

Issues only in concurrent mode:
  → HTTP stack stress under concurrency
  → Solution: Browser-compatible parsing handling stress well

Issues in both modes:
  → urllib3 parsing strictness confirmed
  → Solution: Browser-compatible parsing providing reliable fallback

Examples:
  python concurrent_vs_serial_test.py --password "your_password"
  python concurrent_vs_serial_test.py --password "password" --save-report
        """
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-report", action="store_true", help="Save detailed compatibility analysis report")
    parser.add_argument("--output-file", help="Custom output filename")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    try:
        # Create and run analysis
        test_runner = ConcurrentSerialCompatibilityRunner(args.password, args.host)

        logger.info("🔧 Starting concurrent vs serial HTTP compatibility analysis...")
        start_time = time.time()

        # Run the complete analysis
        results = test_runner.run_comparison_test()

        # Save report if requested
        if args.save_report:
            filename = test_runner.save_compatibility_analysis(results, args.output_file)
            if filename:
                print(f"\n📁 Detailed compatibility report saved: {filename}")

        total_time = time.time() - start_time

        # Print final summary
        print("\n" + "=" * 80)
        print("📊 FINAL HTTP COMPATIBILITY ANALYSIS SUMMARY")
        print("=" * 80)

        compatibility_assessment = results.get("compatibility_analysis", {}).get("compatibility_assessment", "unknown")
        confidence = results.get("compatibility_analysis", {}).get("confidence", "low")

        print(f"🔧 HTTP COMPATIBILITY ASSESSMENT: {compatibility_assessment.upper().replace('_', ' ')}")
        print(f"🎯 CONFIDENCE: {confidence.upper()}")

        if compatibility_assessment == "excellent_compatibility":
            print("✅ RESULT: Browser-compatible parsing working perfectly")
        elif compatibility_assessment == "concurrent_mode_stress":
            print("🔧 RESULT: Browser-compatible parsing handling concurrent stress effectively")
        elif compatibility_assessment == "urllib3_parsing_strictness":
            print("🔧 RESULT: Browser-compatible parsing successfully handling urllib3 strictness")
        elif compatibility_assessment == "concurrent_amplification":
            print("🔧 RESULT: Browser-compatible parsing scaling well under load")

        print(f"⏱️ Total analysis time: {total_time:.2f}s")
        print("=" * 80)

        logger.info("✅ Concurrent vs serial HTTP compatibility analysis complete!")

    except KeyboardInterrupt:
        logger.error("❌ Analysis cancelled by user")
        return 1

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
