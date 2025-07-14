#!/usr/bin/env python3
"""
Error Analysis Test Script
=========================

This script specifically captures and analyzes the malformed responses from
Arris firmware to understand what's really happening with those mysterious
numbers and header parsing errors.

Usage:
    python error_analysis_test.py --password "your_password"
    python error_analysis_test.py --password "password" --force-errors

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


class ErrorAnalysisRunner:
    """
    Specialized test runner focused on capturing and analyzing malformed responses.
    """

    def __init__(self, password: str, host: str = "192.168.100.1"):
        self.password = password
        self.host = host

        if not CLIENT_AVAILABLE:
            raise ImportError("ArrisStatusClient not available - check installation")

    def run_error_capture_test(self, force_concurrent: bool = False) -> Dict[str, Any]:
        """
        Run test specifically designed to trigger and capture malformed responses.
        """
        print("=" * 80)
        print("🔍 ARRIS FIRMWARE ERROR ANALYSIS TEST")
        print(f"⏰ Time: {datetime.now().isoformat()}")
        print(f"🎯 Target: {self.host}")
        print("=" * 80)

        try:
            # Configure client for maximum error capture
            client_config = {
                "password": self.password,
                "host": self.host,
                "max_workers": 5 if force_concurrent else 2,  # Higher concurrency to trigger bugs
                "max_retries": 1,  # Lower retries to capture more errors
                "base_backoff": 0.1,  # Faster retries to trigger race conditions
                "capture_errors": True
            }

            logger.info("🔧 Initializing error analysis client...")
            logger.info(f"📊 Config: {client_config['max_workers']} workers, aggressive timing")

            results = {
                "test_config": client_config,
                "error_captures": [],
                "status_data": None,
                "analysis": None,
                "correlations": []
            }

            with ArrisStatusClient(**client_config) as client:

                # Test 1: Single status request to establish baseline
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

                # Test 2: Rapid concurrent requests to trigger firmware bugs
                logger.info("\n🧪 TEST 2: Rapid concurrent requests (firmware bug trigger)")
                print("🚀 Running rapid concurrent requests to trigger firmware bugs...")

                for iteration in range(3):
                    try:
                        logger.info(f"🔄 Rapid iteration {iteration + 1}/3")
                        start_time = time.time()

                        # Force new authentication to stress the system
                        client.authenticated = False
                        status = client.get_status()

                        iteration_time = time.time() - start_time
                        print(f"   Iteration {iteration + 1}: {iteration_time:.2f}s")

                        # Brief pause
                        time.sleep(0.3)

                    except Exception as e:
                        print(f"   Iteration {iteration + 1}: Error - {e}")
                        logger.warning(f"Iteration {iteration + 1} error: {e}")

                # Test 3: Get comprehensive error analysis
                logger.info("\n🧪 TEST 3: Error analysis")
                print("🔍 Analyzing captured errors...")

                analysis = client.get_error_analysis()
                results["analysis"] = analysis
                results["error_captures"] = client.error_captures

                # Print immediate analysis
                self._print_error_analysis(analysis, client.error_captures)

                # Test 4: Correlation analysis
                logger.info("\n🧪 TEST 4: Correlation analysis")
                print("🔗 Looking for correlations between errors and channel data...")

                correlations = self._analyze_correlations(client.error_captures, status)
                results["correlations"] = correlations
                self._print_correlations(correlations)

            return results

        except Exception as e:
            logger.error(f"Error analysis test failed: {e}")
            print(f"\n❌ Error analysis test failed: {e}")
            return {"error": str(e), "timestamp": time.time()}

    def _print_error_analysis(self, analysis: Dict[str, Any], captures: List) -> None:
        """Print detailed error analysis to console."""
        print(f"\n🔍 ERROR ANALYSIS RESULTS:")
        print(f"   📊 Total errors captured: {analysis.get('total_errors', 0)}")

        # Error types breakdown
        error_types = analysis.get("error_types", {})
        if error_types:
            print(f"   📋 Error types:")
            for error_type, count in error_types.items():
                print(f"      • {error_type}: {count}")

        # Recovery statistics
        recovery_stats = analysis.get("recovery_stats", {})
        if recovery_stats:
            recovery_rate = recovery_stats.get("recovery_rate", 0) * 100
            print(f"   🔄 Recovery rate: {recovery_rate:.1f}%")

        # Mysterious numbers
        mysterious_numbers = analysis.get("mysterious_numbers", [])
        if mysterious_numbers:
            print(f"   🔢 Mysterious numbers found: {mysterious_numbers}")
        else:
            print(f"   🔢 No mysterious numbers detected")

        # Detailed error examination
        if captures:
            print(f"\n🔬 DETAILED ERROR EXAMINATION:")
            for i, capture in enumerate(captures):
                print(f"   Error {i + 1}:")
                print(f"      • Type: {capture.error_type}")
                print(f"      • Request: {capture.request_type}")
                print(f"      • HTTP Status: {capture.http_status}")
                print(f"      • Recovered: {'✅' if capture.recovery_successful else '❌'}")

                # Extract and display raw error details
                if capture.raw_error:
                    print(f"      • Raw error: {capture.raw_error[:150]}...")

                # Show partial content if available
                if capture.partial_content:
                    print(f"      • Partial content: {capture.partial_content[:100]}...")

                print()

    def _analyze_correlations(self, captures: List, status_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze correlations between error numbers and channel data.
        This tries to figure out what those mysterious numbers actually represent.
        """
        correlations = []

        if not captures or not status_data:
            return correlations

        # Extract all mysterious numbers from errors and warnings
        mysterious_numbers = []
        for capture in captures:
            try:
                import re
                # Look for numbers in the raw error message
                if "|" in capture.raw_error:
                    # Pattern specifically for header parsing errors: "3.500000  |Content-type"
                    matches = re.findall(r'(\d+\.?\d*)\s*\|', capture.raw_error)
                    for match in matches:
                        try:
                            num = float(match)
                            mysterious_numbers.append(num)
                            print(f"🔍 Found mysterious number in {capture.error_type}: {num}")
                        except ValueError:
                            pass
                else:
                    # Look for any numbers in the error
                    matches = re.findall(r'(\d+\.?\d*)', capture.raw_error)
                    for match in matches:
                        try:
                            num = float(match)
                            if 0.1 < num < 100:  # Reasonable range for power/SNR values
                                mysterious_numbers.append(num)
                                print(f"🔍 Found potential mysterious number: {num}")
                        except ValueError:
                            pass
            except Exception as e:
                logger.debug(f"Error extracting numbers from capture: {e}")

        if not mysterious_numbers:
            print("🔍 No mysterious numbers found in error captures")
            return correlations

        print(f"🔍 Found {len(mysterious_numbers)} mysterious numbers: {mysterious_numbers}")

        # Get all channel data for comparison
        channel_values = []

        # Extract downstream channel values
        for channel in status_data.get('downstream_channels', []):
            try:
                # Convert ChannelInfo string representation to actual object if needed
                if isinstance(channel, str):
                    # Parse the string representation
                    import re
                    power_match = re.search(r"power='([^']*)'", channel)
                    snr_match = re.search(r"snr='([^']*)'", channel)
                    channel_id_match = re.search(r"channel_id='([^']*)'", channel)

                    if power_match and channel_id_match:
                        power_str = power_match.group(1).replace(" dBmV", "").strip()
                        try:
                            power_val = float(power_str)
                            channel_values.append({
                                "type": "downstream_power",
                                "channel_id": channel_id_match.group(1),
                                "value": power_val,
                                "raw": power_match.group(1)
                            })
                        except ValueError:
                            pass

                    if snr_match and channel_id_match and snr_match.group(1) not in ["N/A", "Unknown"]:
                        snr_str = snr_match.group(1).replace(" dB", "").strip()
                        try:
                            snr_val = float(snr_str)
                            channel_values.append({
                                "type": "downstream_snr",
                                "channel_id": channel_id_match.group(1),
                                "value": snr_val,
                                "raw": snr_match.group(1)
                            })
                        except ValueError:
                            pass
                else:
                    # Handle actual ChannelInfo objects
                    # Power values
                    if hasattr(channel, 'power') and channel.power and channel.power != "Unknown":
                        power_str = channel.power.replace(" dBmV", "").strip()
                        try:
                            power_val = float(power_str)
                            channel_values.append({
                                "type": "downstream_power",
                                "channel_id": channel.channel_id,
                                "value": power_val,
                                "raw": channel.power
                            })
                        except ValueError:
                            pass

                    # SNR values
                    if hasattr(channel, 'snr') and channel.snr and channel.snr not in ["Unknown", "N/A"]:
                        snr_str = channel.snr.replace(" dB", "").strip()
                        try:
                            snr_val = float(snr_str)
                            channel_values.append({
                                "type": "downstream_snr",
                                "channel_id": channel.channel_id,
                                "value": snr_val,
                                "raw": channel.snr
                            })
                        except ValueError:
                            pass

            except Exception as e:
                logger.debug(f"Error processing downstream channel: {e}")

        # Extract upstream channel values
        for channel in status_data.get('upstream_channels', []):
            try:
                if isinstance(channel, str):
                    # Parse string representation
                    import re
                    power_match = re.search(r"power='([^']*)'", channel)
                    channel_id_match = re.search(r"channel_id='([^']*)'", channel)

                    if power_match and channel_id_match:
                        power_str = power_match.group(1).replace(" dBmV", "").strip()
                        try:
                            power_val = float(power_str)
                            channel_values.append({
                                "type": "upstream_power",
                                "channel_id": channel_id_match.group(1),
                                "value": power_val,
                                "raw": power_match.group(1)
                            })
                        except ValueError:
                            pass
                else:
                    # Handle actual ChannelInfo objects
                    if hasattr(channel, 'power') and channel.power and channel.power != "Unknown":
                        power_str = channel.power.replace(" dBmV", "").strip()
                        try:
                            power_val = float(power_str)
                            channel_values.append({
                                "type": "upstream_power",
                                "channel_id": channel.channel_id,
                                "value": power_val,
                                "raw": channel.power
                            })
                        except ValueError:
                            pass

            except Exception as e:
                logger.debug(f"Error processing upstream channel: {e}")

        print(f"🔍 Found {len(channel_values)} channel values to compare")

        # Look for correlations with better tolerance for floating point precision
        for mysterious_num in mysterious_numbers:
            for channel_val in channel_values:
                # Check for exact matches (within floating point precision)
                if abs(mysterious_num - channel_val["value"]) < 0.001:
                    correlations.append({
                        "type": "exact_match",
                        "mysterious_number": mysterious_num,
                        "channel_type": channel_val["type"],
                        "channel_id": channel_val["channel_id"],
                        "channel_value": channel_val["value"],
                        "raw_value": channel_val["raw"],
                        "confidence": "high",
                        "difference": abs(mysterious_num - channel_val["value"])
                    })
                    print(f"🎯 EXACT MATCH: {mysterious_num} matches {channel_val['type']} #{channel_val['channel_id']} ({channel_val['value']})")

                # Check for close matches (within 0.1)
                elif abs(mysterious_num - channel_val["value"]) < 0.1:
                    correlations.append({
                        "type": "close_match",
                        "mysterious_number": mysterious_num,
                        "channel_type": channel_val["type"],
                        "channel_id": channel_val["channel_id"],
                        "channel_value": channel_val["value"],
                        "raw_value": channel_val["raw"],
                        "difference": abs(mysterious_num - channel_val["value"]),
                        "confidence": "medium"
                    })
                    print(f"🔍 CLOSE MATCH: {mysterious_num} ≈ {channel_val['type']} #{channel_val['channel_id']} ({channel_val['value']}, diff: {abs(mysterious_num - channel_val['value']):.4f})")

        return correlations

    def _print_correlations(self, correlations: List[Dict[str, Any]]) -> None:
        """Print correlation analysis results."""
        if not correlations:
            print("   ❌ No correlations found between mysterious numbers and channel data")
            return

        print(f"   🎯 Found {len(correlations)} potential correlations:")

        for i, corr in enumerate(correlations):
            confidence_icon = {"high": "🎯", "medium": "🔍", "low": "❓"}.get(corr["confidence"], "❓")

            print(f"      {confidence_icon} Correlation {i + 1}:")
            print(f"         • Type: {corr['type']}")
            print(f"         • Mysterious number: {corr['mysterious_number']}")
            print(f"         • Channel: {corr['channel_type']} #{corr['channel_id']}")
            print(f"         • Channel value: {corr['channel_value']} ({corr['raw_value']})")

            if "difference" in corr:
                print(f"         • Difference: {corr['difference']:.4f}")

            print()

    def save_analysis_report(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save detailed analysis report to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_analysis_report_{timestamp}.json"

        try:
            # Convert ErrorCapture objects to dicts for JSON serialization
            if "error_captures" in results:
                serializable_captures = []
                for capture in results["error_captures"]:
                    serializable_captures.append({
                        "timestamp": capture.timestamp,
                        "request_type": capture.request_type,
                        "http_status": capture.http_status,
                        "error_type": capture.error_type,
                        "raw_error": capture.raw_error,
                        "response_headers": capture.response_headers,
                        "partial_content": capture.partial_content,
                        "recovery_successful": capture.recovery_successful
                    })
                results["error_captures"] = serializable_captures

            with open(filename, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"💾 Analysis report saved to: {filename}")
            return filename

        except Exception as e:
            logger.error(f"Failed to save analysis report: {e}")
            return ""


def main():
    """Main entry point for error analysis testing."""
    parser = argparse.ArgumentParser(
        description="Error Analysis Test for Arris Firmware Bug Investigation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script specifically captures and analyzes malformed HTTP responses
from Arris firmware to understand what those mysterious numbers and
header parsing errors really represent.

Examples:
  python error_analysis_test.py --password "your_password"
  python error_analysis_test.py --password "password" --force-errors --save-report
        """
    )

    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--force-errors", action="store_true", help="Use aggressive settings to trigger more errors")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--save-report", action="store_true", help="Save detailed analysis report")
    parser.add_argument("--output-file", help="Custom output filename for report")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    try:
        # Create and run error analysis
        test_runner = ErrorAnalysisRunner(args.password, args.host)

        logger.info("🔍 Starting error analysis test...")
        start_time = time.time()

        # Run the analysis
        results = test_runner.run_error_capture_test(force_concurrent=args.force_errors)

        # Save report if requested
        if args.save_report:
            filename = test_runner.save_analysis_report(results, args.output_file)
            if filename:
                print(f"\n📁 Detailed report saved: {filename}")

        total_time = time.time() - start_time

        # Print summary
        print("\n" + "=" * 80)
        print("📊 ERROR ANALYSIS SUMMARY")
        print("=" * 80)

        if "analysis" in results:
            analysis = results["analysis"]
            print(f"🔍 Total errors captured: {analysis.get('total_errors', 0)}")
            print(f"🔢 Mysterious numbers found: {len(analysis.get('mysterious_numbers', []))}")
            print(f"🔗 Correlations discovered: {len(results.get('correlations', []))}")

            recovery_rate = analysis.get("recovery_stats", {}).get("recovery_rate", 0) * 100
            print(f"🔄 Error recovery rate: {recovery_rate:.1f}%")

        print(f"⏱️ Total analysis time: {total_time:.2f}s")
        print("=" * 80)

        logger.info("✅ Error analysis complete!")

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
