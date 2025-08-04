#!/usr/bin/env python3
"""
HNAP Raw Data Debugger for Arris Modem Status Client
===================================================

This debugging tool authenticates with an Arris modem and captures raw HNAP
response data before parsing. Useful for debugging vendor response format changes.

Author: Charles Marshall
License: MIT
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from arris_modem_status import ArrisModemStatusClient
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConnectionError,
    ArrisModemError,
    ArrisTimeoutError,
)


class HNAPRawDebugger:
    """Raw HNAP response debugger and analyzer."""

    def __init__(
        self,
        password: str,
        username: str = "admin",
        host: str = "192.168.100.1",
        port: int = 443,
        timeout: int = 30,
        verbose: bool = False,
    ):
        """
        Initialize HNAP debugger.

        Args:
            password: Modem admin password
            username: Login username (default: "admin")
            host: Modem IP address (default: "192.168.100.1")
            port: HTTPS port (default: 443)
            timeout: Request timeout in seconds (default: 30)
            verbose: Enable verbose logging
        """
        self.password = password
        self.username = username
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verbose = verbose

        # Setup logging
        self._setup_logging()

        # Initialize client (using serial mode for reliability)
        self.client = ArrisModemStatusClient(
            password=password,
            username=username,
            host=host,
            port=port,
            concurrent=False,  # Use serial mode for debugging reliability
            max_retries=3,
            timeout=(5, timeout),
            capture_errors=True,
        )

        # HNAP request definitions (from the main client)
        self.hnap_requests = {
            "software_info": {
                "description": "Software version, model, uptime information",
                "request": {"GetMultipleHNAPs": {"GetCustomerStatusSoftware": ""}},
            },
            "startup_connection": {
                "description": "Startup sequence and connection info",
                "request": {
                    "GetMultipleHNAPs": {
                        "GetCustomerStatusStartupSequence": "",
                        "GetCustomerStatusConnectionInfo": "",
                    }
                },
            },
            "internet_register": {
                "description": "Internet status and registration info",
                "request": {
                    "GetMultipleHNAPs": {
                        "GetInternetConnectionStatus": "",
                        "GetArrisRegisterInfo": "",
                        "GetArrisRegisterStatus": "",
                    }
                },
            },
            "channel_info": {
                "description": "Downstream and upstream channel data",
                "request": {
                    "GetMultipleHNAPs": {
                        "GetCustomerStatusDownstreamChannelInfo": "",
                        "GetCustomerStatusUpstreamChannelInfo": "",
                    }
                },
            },
        }

        self.logger = logging.getLogger(__name__)

    def _setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO

        # Configure root logger
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )

        # Reduce noise from third-party libraries
        if not self.verbose:
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)

    def authenticate(self) -> bool:
        """
        Authenticate with the modem.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            self.logger.info(f"🔐 Authenticating with {self.host}:{self.port} as {self.username}")
            start_time = time.time()

            success = self.client.authenticate()
            auth_time = time.time() - start_time

            if success:
                self.logger.info(f"✅ Authentication successful in {auth_time:.2f}s")
                return True
            else:
                self.logger.error("❌ Authentication failed")
                return False

        except ArrisAuthenticationError as e:
            self.logger.error(f"❌ Authentication error: {e}")
            return False
        except ArrisConnectionError as e:
            self.logger.error(f"❌ Connection error: {e}")
            return False
        except ArrisTimeoutError as e:
            self.logger.error(f"❌ Timeout error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Unexpected authentication error: {e}")
            return False

    def capture_raw_response(self, request_name: str, request_body: Dict[str, Any]) -> Optional[str]:
        """
        Capture raw HNAP response without parsing.

        Args:
            request_name: Name of the request for logging
            request_body: HNAP request body

        Returns:
            Raw response text or None if failed
        """
        try:
            self.logger.info(f"📤 Making HNAP request: {request_name}")
            start_time = time.time()

            # Use the client's internal request method to get raw response
            response = self.client._make_hnap_request_with_retry("GetMultipleHNAPs", request_body)

            request_time = time.time() - start_time

            if response:
                self.logger.info(f"📥 Response received in {request_time:.2f}s ({len(response)} chars)")
                return response
            else:
                self.logger.warning(f"⚠️  No response received for {request_name}")
                return None

        except Exception as e:
            self.logger.error(f"❌ Error capturing {request_name}: {e}")
            return None

    def format_json_response(self, response_text: str, pretty: bool = True) -> str:
        """
        Format JSON response for display.

        Args:
            response_text: Raw JSON response text
            pretty: Whether to pretty-print JSON

        Returns:
            Formatted JSON string
        """
        try:
            if pretty:
                # Parse and re-format with indentation
                parsed = json.loads(response_text)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            else:
                return response_text
        except json.JSONDecodeError as e:
            self.logger.warning(f"⚠️  Invalid JSON response: {e}")
            return f"INVALID JSON: {response_text}"

    def analyze_response_structure(self, response_text: str) -> Dict[str, Any]:
        """
        Analyze the structure of a response.

        Args:
            response_text: Raw JSON response text

        Returns:
            Analysis results
        """
        analysis = {
            "size_bytes": len(response_text),
            "size_chars": len(response_text),
            "valid_json": False,
            "top_level_keys": [],
            "nested_structure": {},
            "data_types": {},
        }

        try:
            parsed = json.loads(response_text)
            analysis["valid_json"] = True

            if isinstance(parsed, dict):
                analysis["top_level_keys"] = list(parsed.keys())

                # Analyze nested structure
                for key, value in parsed.items():
                    analysis["data_types"][key] = type(value).__name__

                    if isinstance(value, dict):
                        analysis["nested_structure"][key] = list(value.keys())

        except json.JSONDecodeError:
            analysis["valid_json"] = False

        return analysis

    def save_response_to_file(self, response_text: str, filename: str, pretty: bool = True):
        """
        Save raw response to file.

        Args:
            response_text: Raw response text
            filename: Output filename
            pretty: Whether to pretty-print JSON
        """
        try:
            formatted_response = self.format_json_response(response_text, pretty)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(formatted_response)

            self.logger.info(f"💾 Response saved to {filename}")

        except Exception as e:
            self.logger.error(f"❌ Error saving to {filename}: {e}")

    def capture_all_responses(self, save_to_files: bool = False, output_dir: Optional[str] = None) -> Dict[str, str]:
        """
        Capture all HNAP responses.

        Args:
            save_to_files: Whether to save responses to files
            output_dir: Directory to save files (default: current directory)

        Returns:
            Dictionary of response name to raw response text
        """
        if not self.client.authenticated:
            self.logger.error("❌ Not authenticated - call authenticate() first")
            return {}

        responses = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.logger.info(f"🚀 Capturing {len(self.hnap_requests)} HNAP responses...")
        overall_start = time.time()

        for request_name, request_info in self.hnap_requests.items():
            self.logger.info(f"\n📋 {request_name}: {request_info['description']}")

            response = self.capture_raw_response(request_name, request_info["request"])

            if response:
                responses[request_name] = response

                # Analyze response structure
                analysis = self.analyze_response_structure(response)
                self.logger.info(
                    f"   📊 Size: {analysis['size_chars']} chars, "
                    f"Valid JSON: {analysis['valid_json']}, "
                    f"Keys: {len(analysis['top_level_keys'])}"
                )

                # Save to file if requested
                if save_to_files:
                    if output_dir:
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
                        filename = f"{output_dir}/{request_name}_{timestamp}.json"
                    else:
                        filename = f"{request_name}_{timestamp}.json"

                    self.save_response_to_file(response, filename)

            else:
                self.logger.warning(f"   ⚠️  Failed to capture {request_name}")

            # Small delay between requests to avoid overwhelming the modem
            time.sleep(0.2)

        overall_time = time.time() - overall_start
        success_count = len(responses)
        total_count = len(self.hnap_requests)

        self.logger.info(f"\n✅ Capture complete: {success_count}/{total_count} responses in {overall_time:.2f}s")

        return responses

    def display_responses(self, responses: Dict[str, str], show_analysis: bool = True):
        """
        Display captured responses in a readable format.

        Args:
            responses: Dictionary of response name to raw response text
            show_analysis: Whether to show response analysis
        """
        print("\n" + "=" * 80)
        print("HNAP RAW RESPONSE DATA")
        print("=" * 80)

        for request_name, response_text in responses.items():
            print(f"\n📋 {request_name.upper()}")
            print("-" * 60)

            if show_analysis:
                analysis = self.analyze_response_structure(response_text)
                print(f"Size: {analysis['size_chars']} characters")
                print(f"Valid JSON: {analysis['valid_json']}")
                if analysis["valid_json"]:
                    print(f"Top-level keys: {', '.join(analysis['top_level_keys'])}")
                print()

            # Display formatted response
            formatted_response = self.format_json_response(response_text, pretty=True)
            print(formatted_response)
            print("\n" + "-" * 60)

    def compare_with_parsed_data(self, responses: Dict[str, str]):
        """
        Compare raw responses with parsed data to show the difference.

        Args:
            responses: Dictionary of raw responses
        """
        try:
            # Get parsed data using the normal client method
            self.logger.info("🔄 Getting parsed data for comparison...")

            # Reset client state and get parsed status
            parsed_status = self.client.get_status()

            print("\n" + "=" * 80)
            print("RAW vs PARSED DATA COMPARISON")
            print("=" * 80)

            print(f"\n📊 PARSED STATUS SUMMARY:")
            print(f"Model: {parsed_status.get('model_name', 'Unknown')}")
            print(f"Firmware: {parsed_status.get('firmware_version', 'Unknown')}")
            print(f"Internet: {parsed_status.get('internet_status', 'Unknown')}")
            print(f"Downstream Channels: {len(parsed_status.get('downstream_channels', []))}")
            print(f"Upstream Channels: {len(parsed_status.get('upstream_channels', []))}")

            if "channel_info" in responses:
                print(f"\n📋 CHANNEL_INFO RAW DATA PREVIEW:")
                try:
                    channel_data = json.loads(responses["channel_info"])
                    hnap_response = channel_data.get("GetMultipleHNAPsResponse", {})

                    # Show downstream raw data
                    downstream_resp = hnap_response.get("GetCustomerStatusDownstreamChannelInfoResponse", {})
                    downstream_raw = downstream_resp.get("CustomerConnDownstreamChannel", "Not found")
                    if downstream_raw and len(downstream_raw) > 100:
                        print(f"Downstream raw: {downstream_raw[:100]}...")
                    else:
                        print(f"Downstream raw: {downstream_raw}")

                    # Show upstream raw data
                    upstream_resp = hnap_response.get("GetCustomerStatusUpstreamChannelInfoResponse", {})
                    upstream_raw = upstream_resp.get("CustomerConnUpstreamChannel", "Not found")
                    if upstream_raw and len(upstream_raw) > 100:
                        print(f"Upstream raw: {upstream_raw[:100]}...")
                    else:
                        print(f"Upstream raw: {upstream_raw}")

                except json.JSONDecodeError:
                    print("❌ Could not parse channel_info response")

        except Exception as e:
            self.logger.error(f"❌ Error comparing data: {e}")

    def generate_summary_report(self, responses: Dict[str, str]) -> str:
        """
        Generate a summary report of all captured data.

        Args:
            responses: Dictionary of raw responses

        Returns:
            Summary report as string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report_lines = [
            "HNAP RAW DATA CAPTURE SUMMARY REPORT",
            "=" * 50,
            f"Timestamp: {timestamp}",
            f"Modem: {self.host}:{self.port}",
            f"Username: {self.username}",
            f"Responses Captured: {len(responses)}/{len(self.hnap_requests)}",
            "",
        ]

        for request_name, response_text in responses.items():
            analysis = self.analyze_response_structure(response_text)
            request_info = self.hnap_requests.get(request_name, {})

            report_lines.extend(
                [
                    f"📋 {request_name.upper()}:",
                    f"   Description: {request_info.get('description', 'N/A')}",
                    f"   Size: {analysis['size_chars']} characters",
                    f"   Valid JSON: {analysis['valid_json']}",
                    f"   Structure: {len(analysis['top_level_keys'])} top-level keys",
                    "",
                ]
            )

        return "\n".join(report_lines)


def main():
    """Main entry point for the HNAP debugger."""
    parser = argparse.ArgumentParser(
        description="HNAP Raw Data Debugger for Arris Modem Status Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic capture and display
  python hnap_debugger.py --password "your_password"

  # Capture with verbose logging and save to files
  python hnap_debugger.py --password "password" --verbose --save-files

  # Custom host and save to specific directory
  python hnap_debugger.py --password "password" --host 192.168.1.1 \\
                          --save-files --output-dir debug_capture

  # Show comparison with parsed data
  python hnap_debugger.py --password "password" --show-comparison

Output:
  Displays raw HNAP JSON responses before parsing, useful for debugging
  vendor response format changes and understanding modem behavior.
        """,
    )

    # Connection arguments
    parser.add_argument("--password", required=True, help="Modem admin password")
    parser.add_argument("--username", default="admin", help="Login username (default: admin)")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address (default: 192.168.100.1)")
    parser.add_argument("--port", type=int, default=443, help="HTTPS port (default: 443)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")

    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--save-files", action="store_true", help="Save raw responses to JSON files")
    parser.add_argument("--output-dir", help="Directory to save files (default: current directory)")
    parser.add_argument(
        "--show-analysis", action="store_true", default=True, help="Show response analysis (default: True)"
    )
    parser.add_argument("--show-comparison", action="store_true", help="Compare raw data with parsed data")
    parser.add_argument("--summary-only", action="store_true", help="Show only summary, not full responses")

    args = parser.parse_args()

    # Create debugger instance
    debugger = HNAPRawDebugger(
        password=args.password,
        username=args.username,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    try:
        # Authenticate
        if not debugger.authenticate():
            print("❌ Authentication failed. Check your credentials and network connection.")
            return 1

        # Capture responses
        responses = debugger.capture_all_responses(
            save_to_files=args.save_files,
            output_dir=args.output_dir,
        )

        if not responses:
            print("❌ No responses captured. Check modem connectivity.")
            return 1

        # Display results
        if args.summary_only:
            summary = debugger.generate_summary_report(responses)
            print(summary)
        else:
            debugger.display_responses(responses, show_analysis=args.show_analysis)

        # Show comparison if requested
        if args.show_comparison:
            debugger.compare_with_parsed_data(responses)

        print(f"\n✅ Successfully captured {len(responses)} HNAP responses!")

        if args.save_files:
            print(f"💾 Files saved to: {args.output_dir or 'current directory'}")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        return 1
    except Exception as e:
        debugger.logger.error(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1
    finally:
        # Cleanup
        debugger.client.close()


if __name__ == "__main__":
    sys.exit(main())
