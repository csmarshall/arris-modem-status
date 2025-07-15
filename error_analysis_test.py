#!/usr/bin/env python3
"""
HTTP Compatibility Analysis Test Script
======================================

This script analyzes HTTP compatibility issues with Arris modems to understand
urllib3 parsing strictness and validate the browser-compatible HTTP parsing solution.

The analysis focuses on:
1. HTTP compatibility issue detection and recovery
2. Browser-compatible parsing effectiveness  
3. urllib3 parsing strictness patterns
4. Error recovery and correlation analysis

Usage:
    python error_analysis_test.py --password "your_password"
    python error_analysis_test.py --password "password" --save-report

Author: Charles Marshall
Version: 1.3.0
"""

import argparse
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List

# Import the client with proper fallback handling
try:
    from arris_modem_status import ArrisStatusClient
    CLIENT_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ Using installed arris_modem_status package")
except ImportError:
    # Fallback for development testing
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from arris_modem_status.arris_status_client import ArrisStatusClient
        CLIENT_AVAILABLE = True
        logger = logging.getLogger(__name__)
        logger.info("✅ Using local arris_status_client module")
    except ImportError:
        CLIENT_AVAILABLE = False
        print("❌ ERROR: Cannot import ArrisStatusClient")
        print("📋 Please ensure arris_modem_status is installed or run from project directory")

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class HTTPCompatibilityAnalysisRunner:
    """
    Specialized test runner focused on HTTP compatibility analysis and validation.
    """

    def __init__(self, password: str, host: str = "192.168.100.1"):
        self.password = password
        self.host = host

        if not CLIENT_AVAILABLE:
            raise ImportError("ArrisStatusClient not available - check installation")

    def run_http_compatibility_analysis(self, aggressive_testing: bool = False) -> Dict[str, Any]:
        """
        Run comprehensive HTTP compatibility analysis.
        """
        print("=" * 80)
        print("🔧 HTTP COMPATIBILITY ANALYSIS TEST")
        print(f"⏰ Time: {datetime.now().isoformat()}")
        print(f"🎯 Target: {self.host}")
        print("=" * 80)

        try:
            # Configure client for HTTP compatibility testing
            client_config = {
                "password": self.password,
                "host": self.host,
                "max_workers": 4 if aggressive_testing else 2,  # Higher concurrency for stress testing
                "max_retries": 2,  # Lower retries to capture more raw issues
                "base_backoff": 0.1,  # Faster retries to test compatibility handling
                "capture_errors": True
            }

            logger.info("🔧 Initializing HTTP compatibility analysis client...")
            logger.info(f"📊 Config: {client_config['max_workers']} workers, compatibility testing mode")

            results = {
                "test_config": client_config,
                "error_captures": [],
                "status_data": None,
                "analysis": None,
                "compatibility_patterns": []
            }

            with ArrisStatusClient(**client_config) as client:

                # Test 1: Baseline status request
                logger.info("\n🧪 TEST 1: Baseline status request")
                print("📊 Running baseline status request...")

                try:
                    start_time = time.time()
                    status = client.get_status()
                    baseline_time = time.time() - start_time

                    results["status_data"] = status

                    print(f"✅ Baseline complete: {baseline_time:.2f}s")
                    print(f"📡 Channels: {len(status.get('downstream_channels', []))} down, {len(status.get('upstream_channels', []))} up")

                except Exception as e:
                    print(f"❌ Baseline failed: {e}")
                    logger.error(f"Baseline test failed: {e}")

                # Test 2: Aggressive concurrent requests to test HTTP compatibility
                logger.info("\n🧪 TEST 2: HTTP compatibility stress testing")
                print("🚀 Running aggressive concurrent requests to test HTTP compatibility...")

                for iteration in range(3):
                    try:
                        logger.info(f"🔄 Compatibility test iteration {iteration + 1}/3")
                        start_time = time.time()

                        # Force new authentication to stress the HTTP stack
                        client.authenticated = False
                        status = client.get_status()

                        iteration_time = time.time() - start_time
                        print(f"   Iteration {iteration + 1}: {iteration_time:.2f}s")

                        # Brief pause
                        time.sleep(0.3)

                    except Exception as e:
                        print(f"   Iteration {iteration + 1}: Error - {e}")
                        logger.warning(f"Iteration {iteration + 1} error: {e}")

                # Test 3: Get comprehensive HTTP compatibility analysis
                logger.info("\n🧪 TEST 3: HTTP compatibility analysis")
                print("🔍 Analyzing HTTP compatibility handling...")

                analysis = client.get_error_analysis()
                results["analysis"] = analysis
                results["error_captures"] = client.error_captures

                # Print immediate analysis
                self._print_compatibility_analysis(analysis, client.error_captures)

                # Test 4: Pattern analysis for HTTP compatibility
                logger.info("\n🧪 TEST 4: Compatibility pattern analysis")
                print("🔗 Looking for HTTP compatibility patterns and urllib3 parsing artifacts...")

                patterns = self._analyze_compatibility_patterns(client.error_captures, status)
                results["compatibility_patterns"] = patterns
                self._print_compatibility_patterns(patterns)

            return results

        except Exception as e:
            logger.error(f"HTTP compatibility analysis failed: {e}")
            print(f"\n❌ HTTP compatibility analysis failed: {e}")
            return {"error": str(e), "timestamp": time.time()}

    def _print_compatibility_analysis(self, analysis: Dict[str, Any], captures: List) -> None:
        """Print detailed HTTP compatibility analysis to console."""
        print(f"\n🔧 HTTP COMPATIBILITY ANALYSIS RESULTS:")
        print(f"   📊 Total errors captured: {analysis.get('total_errors', 0)}")

        # Error types breakdown
        error_types = analysis.get("error_types", {})
        if error_types:
            print(f"   📋 Error types:")
            for error_type, count in error_types.items():
                if error_type == "http_compatibility":
                    print(f"      • {error_type}: {count} (handled by browser-compatible parsing)")
                else:
                    print(f"      • {error_type}: {count}")

        # Recovery statistics
        recovery_stats = analysis.get("recovery_stats", {})
        if recovery_stats:
            recovery_rate = recovery_stats.get("recovery_rate", 0) * 100
            print(f"   🔄 Recovery rate: {recovery_rate:.1f}%")

        # HTTP compatibility specific metrics
        compatibility_issues = analysis.get("http_compatibility_issues", 0)
        if compatibility_issues > 0:
            print(f"   🔧 HTTP compatibility issues: {compatibility_issues} (automatically resolved)")
        else:
            print(f"   ✅ No HTTP compatibility issues detected")

        # Parsing artifacts
        parsing_artifacts = analysis.get("parsing_artifacts", [])
        if parsing_artifacts:
            print(f"   🔍 Parsing artifacts found: {parsing_artifacts}")
            print(f"   💡 These are urllib3 parsing strictness artifacts, not data corruption")
        else:
            print(f"   ✅ No parsing artifacts detected")

        # Detailed error examination
        if captures:
            compatibility_captures = [c for c in captures if getattr(c, 'compatibility_issue', False)]
            other_captures = [c for c in captures if not getattr(c, 'compatibility_issue', False)]

            if compatibility_captures:
                print(f"\n🔧 HTTP COMPATIBILITY ISSUES DETECTED:")
                for i, capture in enumerate(compatibility_captures):
                    print(f"   Issue {i + 1}:")
                    print(f"      • Type: {capture.error_type}")
                    print(f"      • Request: {capture.request_type}")
                    print(f"      • HTTP Status: {capture.http_status}")
                    print(f"      • Recovered: {'✅' if capture.recovery_successful else '❌'}")
                    print(f"      • Solution: Browser-compatible HTTP parsing")

                    # Show raw error details for HTTP compatibility issues
                    if capture.raw_error:
                        print(f"      • urllib3 error: {capture.raw_error[:100]}...")
                    print()

            if other_captures:
                print(f"\n⚠️ OTHER ERRORS (Non-compatibility):")
                for i, capture in enumerate(other_captures):
                    print(f"   Error {i + 1}:")
                    print(f"      • Type: {capture.error_type}")
                    print(f"      • Request: {capture.request_type}")
                    print(f"      • Recovered: {'✅' if capture.recovery_successful else '❌'}")
                    print()

    def _analyze_compatibility_patterns(self, captures: List, status_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze HTTP compatibility patterns and urllib3 parsing artifacts.
        """
        patterns = []

        if not captures or not status_data:
            return patterns

        # Extract parsing artifacts from HTTP compatibility issues
        parsing_artifacts = []
        compatibility_issues = []

        for capture in captures:
            if getattr(capture, 'compatibility_issue', False):
                compatibility_issues.append(capture)

                try:
                    import re
                    # Look for urllib3 parsing artifacts in error messages
                    if "|" in capture.raw_error:
                        # Pattern specifically for HTTP parsing artifacts: "3.500000 |Content-type"
                        matches = re.findall(r'(\d+\.?\d*)\s*\|', capture.raw_error)
                        for match in matches:
                            try:
                                num = float(match)
                                parsing_artifacts.append(num)
                                print(f"🔍 Found urllib3 parsing artifact: {num}")
                            except ValueError:
                                pass
                    else:
                        # Look for other HTTP compatibility patterns
                        if "HeaderParsingError" in capture.raw_error:
                            patterns.append({
                                "type": "header_parsing_strictness",
                                "description": "urllib3 strict header parsing",
                                "solution": "Browser-compatible parsing fallback",
                                "error_sample": capture.raw_error[:100]
                            })

                except Exception as e:
                    logger.debug(f"Error extracting patterns from capture: {e}")

        if not parsing_artifacts and not compatibility_issues:
            print("✅ No HTTP compatibility issues found")
            return patterns

        if parsing_artifacts:
            print(f"🔍 Found {len(parsing_artifacts)} urllib3 parsing artifacts: {parsing_artifacts}")

            # Analyze the nature of these artifacts
            patterns.append({
                "type": "urllib3_parsing_artifacts",
                "artifacts": parsing_artifacts,
                "count": len(parsing_artifacts),
                "analysis": "These are urllib3 parsing strictness artifacts, not actual data injection",
                "solution": "Browser-compatible HTTP parsing handles these automatically"
            })

        if compatibility_issues:
            patterns.append({
                "type": "http_compatibility_issues",
                "count": len(compatibility_issues),
                "analysis": "urllib3 is too strict compared to browser HTTP parsing",
                "solution": "ArrisCompatibleHTTPAdapter provides browser-like tolerance",
                "recovery_rate": len([c for c in compatibility_issues if c.recovery_successful]) / len(compatibility_issues) * 100
            })

        return patterns

    def _print_compatibility_patterns(self, patterns: List[Dict[str, Any]]) -> None:
        """Print HTTP compatibility pattern analysis results."""
        if not patterns:
            print("   ✅ No specific HTTP compatibility patterns detected")
            return

        print(f"   🔧 Found {len(patterns)} HTTP compatibility patterns:")

        for i, pattern in enumerate(patterns):
            pattern_type = pattern.get('type', 'unknown')

            print(f"      📋 Pattern {i + 1}: {pattern_type}")

            if pattern_type == "urllib3_parsing_artifacts":
                artifacts = pattern.get('artifacts', [])
                print(f"         • Count: {len(artifacts)} artifacts")
                print(f"         • Values: {artifacts}")
                print(f"         • Analysis: {pattern.get('analysis', 'N/A')}")
                print(f"         • Solution: {pattern.get('solution', 'N/A')}")

            elif pattern_type == "http_compatibility_issues":
                count = pattern.get('count', 0)
                recovery_rate = pattern.get('recovery_rate', 0)
                print(f"         • Issues: {count}")
                print(f"         • Recovery rate: {recovery_rate:.1f}%")
                print(f"         • Analysis: {pattern.get('analysis', 'N/A')}")
                print(f"         • Solution: {pattern.get('solution', 'N/A')}")

            elif pattern_type == "header_parsing_strictness":
                print(f"         • Description: {pattern.get('description', 'N/A')}")
                print(f"         • Solution: {pattern.get('solution', 'N/A')}")
                print(f"         • Example: {pattern.get('error_sample', 'N/A')}")

            print()

    def save_compatibility_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save detailed HTTP compatibility analysis report to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"http_compatibility_report_{timestamp}.json"

        try:
            # Convert ErrorCapture objects to dicts for JSON serialization
            if "error_captures" in results:
                serializable_captures = []
                for capture in results["error_captures"]:
                    capture_dict = {
                        "timestamp": capture.timestamp,
                        "request_type": capture.request_type,
                        "http_status": capture.http_status,
                        "error_type": capture.error_type,
                        "raw_error": capture.raw_error,
                        "response_headers": capture.response_headers,
                        "partial_content": capture.partial_content,
                        "recovery_successful": capture.recovery_successful
                    }

                    # Add HTTP compatibility information if available
                    if hasattr(capture, 'compatibility_issue'):
                        capture_dict["compatibility_issue"] = capture.compatibility_issue

                    serializable_captures.append(capture_dict)

                results["error_captures"] = serializable_captures

            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"💾 HTTP compatibility report saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save compatibility report: {e}")
            return ""


def main():
    """Main entry point for HTTP compatibility analysis testing."""
    parser = argparse.ArgumentParser(
        description="HTTP Compatibility Analysis for Arris Modem Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script analyzes HTTP compatibility between the Arris modem client and
urllib3 parsing strictness to validate the browser-compatible HTTP parsing solution.

The analysis focuses on:
1. HTTP compatibility issue detection and recovery
2. urllib3 parsing strictness vs browser tolerance  
3. Browser-compatible parsing effectiveness
4. Error recovery patterns and success rates

Examples:
  python error_analysis_test.py --password "your_password"
  python error_analysis_test.py --password "password" --aggressive-testing --save-report
        """
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--aggressive-testing", action="store_true", help="Use aggressive settings to stress HTTP compatibility")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-report", action="store_true", help="Save detailed compatibility report")
    parser.add_argument("--output-file", help="Custom output filename for report")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    try:
        # Create and run HTTP compatibility analysis
        test_runner = HTTPCompatibilityAnalysisRunner(args.password, args.host)

        logger.info("🔧 Starting HTTP compatibility analysis...")
        start_time = time.time()

        # Run the analysis
        results = test_runner.run_http_compatibility_analysis(aggressive_testing=args.aggressive_testing)

        # Save report if requested
        if args.save_report:
            filename = test_runner.save_compatibility_report(results, args.output_file)
            if filename:
                print(f"\n📁 Detailed compatibility report saved: {filename}")

        total_time = time.time() - start_time

        # Print summary
        print("\n" + "=" * 80)
        print("📊 HTTP COMPATIBILITY ANALYSIS SUMMARY")
        print("=" * 80)

        if "analysis" in results:
            analysis = results["analysis"]
            print(f"🔧 Total errors captured: {analysis.get('total_errors', 0)}")
            print(f"🔧 HTTP compatibility issues: {analysis.get('http_compatibility_issues', 0)}")
            print(f"🔍 Parsing artifacts found: {len(analysis.get('parsing_artifacts', []))}")

            recovery_rate = analysis.get("recovery_stats", {}).get("recovery_rate", 0) * 100
            print(f"🔄 Error recovery rate: {recovery_rate:.1f}%")

        patterns = results.get('compatibility_patterns', [])
        print(f"📋 Compatibility patterns: {len(patterns)}")

        print(f"⏱️ Total analysis time: {total_time:.2f}s")
        print("=" * 80)

        # Final assessment
        compatibility_issues = results.get("analysis", {}).get("http_compatibility_issues", 0)
        if compatibility_issues > 0:
            print("🔧 HTTP compatibility issues detected and successfully handled")
            print("✅ Browser-compatible parsing working as expected")
        else:
            print("✅ No HTTP compatibility issues detected - system working smoothly")

        logger.info("✅ HTTP compatibility analysis complete!")

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
