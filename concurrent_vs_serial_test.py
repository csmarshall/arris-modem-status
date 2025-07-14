#!/usr/bin/env python3
"""
Concurrent vs Serial Mode Test Script
====================================

This script specifically tests both concurrent and serial request modes to
isolate whether the mysterious numbers and header parsing errors are caused by:

1. Client-side threading issues (requests/urllib3)
2. Server-side race conditions (Arris firmware bug)
3. HTTP connection pooling problems
4. Session sharing issues

By comparing error patterns between serial and concurrent modes, we can
definitively identify the root cause.

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

# Import the enhanced client with serial/parallel option
try:
    from enhanced_arris_client import ArrisStatusClient
    CLIENT_AVAILABLE = True
except ImportError:
    # Fallback for testing
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from enhanced_arris_client import ArrisStatusClient
        CLIENT_AVAILABLE = True
    except ImportError:
        CLIENT_AVAILABLE = False

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class ConcurrentSerialTestRunner:
    """
    Test runner to isolate threading vs firmware bug root cause.
    """

    def __init__(self, password: str, host: str = "192.168.100.1"):
        """Initialize the test runner."""
        self.password = password
        self.host = host

        if not CLIENT_AVAILABLE:
            raise ImportError("Enhanced Arris client not available")

    def run_comparison_test(self) -> Dict[str, Any]:
        """
        Run comprehensive comparison between concurrent and serial modes.
        """
        print("=" * 80)
        print("🔍 CONCURRENT vs SERIAL MODE ANALYSIS")
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
            "root_cause_analysis": {}
        }

        # Test 1: Serial Mode (No Concurrency)
        print("\n🔄 TEST 1: SERIAL MODE (No Threading)")
        print("-" * 50)
        results["serial_mode"] = self._test_mode(concurrent=False)

        # Test 2: Concurrent Mode (With Threading)
        print("\n🚀 TEST 2: CONCURRENT MODE (With Threading)")
        print("-" * 50)
        results["concurrent_mode"] = self._test_mode(concurrent=True)

        # Test 3: Comparison Analysis
        print("\n⚖️  TEST 3: COMPARISON ANALYSIS")
        print("-" * 50)
        results["comparison"] = self._compare_modes(results["serial_mode"], results["concurrent_mode"])

        # Test 4: Root Cause Analysis
        print("\n🔍 TEST 4: ROOT CAUSE ANALYSIS")
        print("-" * 50)
        results["root_cause_analysis"] = self._analyze_root_cause(results)

        return results

    def _test_mode(self, concurrent: bool) -> Dict[str, Any]:
        """Test a specific mode (concurrent or serial)."""
        mode_str = "concurrent" if concurrent else "serial"
        mode_results = {
            "mode": mode_str,
            "performance": {},
            "errors": [],
            "mysterious_numbers": [],
            "channel_data": {},
            "success": False
        }

        try:
            # Configure client for the specific mode
            client = ArrisStatusClient(
                password=self.password,
                host=self.host,
                concurrent=concurrent,
                max_workers=3 if concurrent else 1,
                max_retries=2,  # Lower retries to capture more raw errors
                base_backoff=0.1,  # Faster to trigger more issues
                capture_errors=True
            )

            print(f"🔧 Testing {mode_str} mode...")

            # Run multiple iterations to increase chance of triggering firmware bugs
            total_time = 0
            iterations = 3
            successful_iterations = 0

            for i in range(iterations):
                try:
                    print(f"   Iteration {i + 1}/{iterations}...")

                    # Force re-authentication to stress the system
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

            # Get error analysis
            error_analysis = client.get_error_analysis()
            client.close()

            # Extract results
            mode_results["performance"] = {
                "total_time": total_time,
                "average_time": total_time / successful_iterations if successful_iterations > 0 else 0,
                "successful_iterations": successful_iterations,
                "total_iterations": iterations,
                "success_rate": successful_iterations / iterations
            }

            mode_results["errors"] = error_analysis.get("error_types", {})
            mode_results["mysterious_numbers"] = error_analysis.get("mysterious_numbers", [])
            mode_results["recovery_rate"] = error_analysis.get("recovery_stats", {}).get("recovery_rate", 0)
            mode_results["success"] = successful_iterations > 0

            # Print immediate results
            print(f"📊 {mode_str.upper()} RESULTS:")
            print(f"   ⏱️  Average time: {mode_results['performance']['average_time']:.2f}s")
            print(f"   ✅ Success rate: {mode_results['performance']['success_rate'] * 100:.1f}%")
            print(f"   🐛 Total errors: {error_analysis.get('total_errors', 0)}")
            print(f"   🔢 Mysterious numbers: {len(mode_results['mysterious_numbers'])}")

            if mode_results["mysterious_numbers"]:
                print(f"      Numbers found: {mode_results['mysterious_numbers']}")

        except Exception as e:
            logger.error(f"{mode_str} mode test failed: {e}")
            mode_results["error"] = str(e)

        return mode_results

    def _compare_modes(self, serial_results: Dict[str, Any], concurrent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare results between serial and concurrent modes."""
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

            # Error comparison
            serial_errors = len(serial_results.get("errors", {}))
            concurrent_errors = len(concurrent_results.get("errors", {}))
            serial_mysterious = len(serial_results.get("mysterious_numbers", []))
            concurrent_mysterious = len(concurrent_results.get("mysterious_numbers", []))

            comparison["errors"] = {
                "serial_error_types": serial_errors,
                "concurrent_error_types": concurrent_errors,
                "serial_mysterious_numbers": serial_mysterious,
                "concurrent_mysterious_numbers": concurrent_mysterious,
                "more_errors_in_concurrent": concurrent_errors > serial_errors,
                "mysterious_numbers_in_both": serial_mysterious > 0 and concurrent_mysterious > 0,
                "mysterious_numbers_only_concurrent": serial_mysterious == 0 and concurrent_mysterious > 0
            }

            print(f"🐛 ERROR COMPARISON:")
            print(f"   Serial errors: {serial_errors}")
            print(f"   Concurrent errors: {concurrent_errors}")
            print(f"   Serial mysterious numbers: {serial_mysterious}")
            print(f"   Concurrent mysterious numbers: {concurrent_mysterious}")

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

    def _analyze_root_cause(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the root cause based on the comparison results."""
        analysis = {
            "root_cause": "unknown",
            "confidence": "low",
            "evidence": [],
            "recommendations": []
        }

        try:
            comparison = results.get("comparison", {})
            serial_results = results.get("serial_mode", {})
            concurrent_results = results.get("concurrent_mode", {})

            # Extract key metrics
            serial_mysterious = len(serial_results.get("mysterious_numbers", []))
            concurrent_mysterious = len(concurrent_results.get("mysterious_numbers", []))
            serial_errors = len(serial_results.get("errors", {}))
            concurrent_errors = len(concurrent_results.get("errors", {}))

            print(f"🔍 ROOT CAUSE ANALYSIS:")

            # Scenario 1: Errors only in concurrent mode
            if concurrent_mysterious > 0 and serial_mysterious == 0:
                analysis["root_cause"] = "client_side_threading"
                analysis["confidence"] = "high"
                analysis["evidence"].append("Mysterious numbers only appear in concurrent mode")
                analysis["evidence"].append("Serial mode is completely clean")
                analysis["recommendations"].append("Use serial mode for maximum reliability")
                analysis["recommendations"].append("Issue is likely in requests/urllib3 threading or connection pooling")

                print("   🎯 CONCLUSION: CLIENT-SIDE THREADING ISSUE")
                print("   📋 Evidence: Errors only in concurrent mode")
                print("   🔧 Root cause: requests/urllib3 threading or connection pooling")

            # Scenario 2: Errors in both modes
            elif concurrent_mysterious > 0 and serial_mysterious > 0:
                analysis["root_cause"] = "arris_firmware_bug"
                analysis["confidence"] = "very_high"
                analysis["evidence"].append("Mysterious numbers appear in BOTH concurrent and serial modes")
                analysis["evidence"].append("Rules out client-side threading issues")
                analysis["evidence"].append("Confirms server-side race condition in Arris firmware")
                analysis["recommendations"].append("Arris firmware has inherent race conditions")
                analysis["recommendations"].append("Use retry logic regardless of mode")
                analysis["recommendations"].append("Contact Arris support for firmware fix")

                print("   🎯 CONCLUSION: ARRIS FIRMWARE BUG CONFIRMED")
                print("   📋 Evidence: Errors in BOTH modes - rules out threading")
                print("   🔧 Root cause: Arris S34 firmware race condition")

            # Scenario 3: More errors in concurrent but some in serial
            elif concurrent_errors > serial_errors and serial_mysterious > 0:
                analysis["root_cause"] = "combined_issue"
                analysis["confidence"] = "medium"
                analysis["evidence"].append("More errors in concurrent mode suggests threading amplifies the issue")
                analysis["evidence"].append("Errors in serial mode confirm underlying firmware issue")
                analysis["recommendations"].append("Arris firmware bug amplified by client-side concurrency")
                analysis["recommendations"].append("Use lower concurrency settings")

                print("   🎯 CONCLUSION: COMBINED ISSUE")
                print("   📋 Evidence: Firmware bug amplified by threading")
                print("   🔧 Root cause: Arris bug + threading interactions")

            # Scenario 4: No errors in either mode
            elif concurrent_mysterious == 0 and serial_mysterious == 0:
                analysis["root_cause"] = "no_issues_detected"
                analysis["confidence"] = "low"
                analysis["evidence"].append("No mysterious numbers detected in either mode")
                analysis["evidence"].append("May need more aggressive testing to trigger issues")
                analysis["recommendations"].append("Increase test iterations or concurrency")
                analysis["recommendations"].append("Try different timing patterns")

                print("   🎯 CONCLUSION: NO ISSUES DETECTED")
                print("   📋 Evidence: Clean operation in both modes")
                print("   🔧 May need more aggressive testing")

            # Add specific recommendations
            if analysis["root_cause"] == "arris_firmware_bug":
                analysis["recommendations"].extend([
                    "Use the retry logic in production",
                    "Monitor for correlation between mysterious numbers and channel data",
                    "Consider firmware update from Arris"
                ])
            elif analysis["root_cause"] == "client_side_threading":
                analysis["recommendations"].extend([
                    "Use serial mode (concurrent=False) for production",
                    "Report issue to requests/urllib3 maintainers",
                    "Consider alternative HTTP libraries"
                ])

            # Print final recommendations
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis["recommendations"], 1):
                print(f"   {i}. {rec}")

        except Exception as e:
            logger.error(f"Root cause analysis failed: {e}")
            analysis["error"] = str(e)

        return analysis

    def save_analysis_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save the complete analysis report."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"concurrent_vs_serial_analysis_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"💾 Analysis report saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save analysis report: {e}")
            return ""

def main():
    """Main entry point for concurrent vs serial testing."""
    parser = argparse.ArgumentParser(
        description="Concurrent vs Serial Mode Analysis for Root Cause Investigation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script helps isolate whether mysterious numbers and header parsing errors are caused by:

1. CLIENT-SIDE ISSUES:
   - requests/urllib3 threading problems
   - HTTP connection pooling issues
   - Session sharing problems

2. SERVER-SIDE ISSUES:
   - Arris firmware race conditions
   - Buffer management bugs
   - Inherent firmware defects

EXPECTED OUTCOMES:

If errors only occur in concurrent mode:
  → Client-side threading issue (requests/urllib3)
  → Solution: Use serial mode or fix threading

If errors occur in BOTH modes:
  → Arris firmware bug confirmed
  → Solution: Use retry logic, contact Arris

Examples:
  python concurrent_vs_serial_test.py --password "your_password"
  python concurrent_vs_serial_test.py --password "password" --save-report
        """
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-report", action="store_true", help="Save detailed analysis report")
    parser.add_argument("--output-file", help="Custom output filename")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    try:
        # Create and run analysis
        test_runner = ConcurrentSerialTestRunner(args.password, args.host)

        logger.info("🔍 Starting concurrent vs serial analysis...")
        start_time = time.time()

        # Run the complete analysis
        results = test_runner.run_comparison_test()

        # Save report if requested
        if args.save_report:
            filename = test_runner.save_analysis_report(results, args.output_file)
            if filename:
                print(f"\n📁 Detailed report saved: {filename}")

        total_time = time.time() - start_time

        # Print final summary
        print("\n" + "=" * 80)
        print("📊 FINAL ANALYSIS SUMMARY")
        print("=" * 80)

        root_cause = results.get("root_cause_analysis", {}).get("root_cause", "unknown")
        confidence = results.get("root_cause_analysis", {}).get("confidence", "low")

        print(f"🎯 ROOT CAUSE: {root_cause.upper()}")
        print(f"🔍 CONFIDENCE: {confidence.upper()}")

        if root_cause == "arris_firmware_bug":
            print("🛠️  SOLUTION: Use retry logic, it's an Arris firmware bug")
        elif root_cause == "client_side_threading":
            print("🛠️  SOLUTION: Use serial mode or fix requests/urllib3 threading")
        elif root_cause == "combined_issue":
            print("🛠️  SOLUTION: Reduce concurrency and use retry logic")

        print(f"⏱️ Total analysis time: {total_time:.2f}s")
        print("=" * 80)

        logger.info("✅ Concurrent vs serial analysis complete!")

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
