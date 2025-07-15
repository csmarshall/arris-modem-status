"""
Command Line Interface for Arris Modem Status Client

This module provides a command-line interface for querying status information
from Arris cable modems. It outputs comprehensive modem data in JSON format
suitable for monitoring systems, scripts, or manual inspection.

The CLI is designed to be monitoring-friendly with JSON output to stdout and
summary information to stderr, allowing easy integration with logging and
monitoring systems.

Features HTTP compatibility handling for urllib3 parsing strictness that
can occur with some Arris modem responses.

Usage:
    python -m arris_modem_status.cli --password <password>
    arris-modem-status --password <password>

Example:
    # Basic usage with default IP
    arris-modem-status --password "your_modem_password"

    # Custom modem IP address
    arris-modem-status --password "password" --host 192.168.1.1

    # Enable debug logging for troubleshooting
    arris-modem-status --password "password" --debug

    # Quiet mode (JSON only, no summary)
    arris-modem-status --password "password" --quiet

    # Serial mode for maximum compatibility
    arris-modem-status --password "password" --serial

Output:
    JSON object containing modem status, channel data, and diagnostics.
    Summary information is printed to stderr, JSON data to stdout.

Author: Charles Marshall
Version: 1.3.0
License: MIT
"""

import argparse
import json
import logging
import sys
from datetime import datetime

from arris_modem_status import ArrisStatusClient


def setup_logging(debug: bool = False) -> None:
    """
    Configure logging for the CLI application.

    Args:
        debug: If True, enable debug-level logging
    """
    level = logging.DEBUG if debug else logging.INFO

    # Configure the root logger
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure third-party libraries to be less verbose unless debug is enabled
    if not debug:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)


def format_channel_data_for_display(status: dict) -> dict:
    """
    Convert ChannelInfo objects to dictionaries for JSON serialization.

    The ArrisStatusClient returns ChannelInfo dataclass objects which need
    to be converted to dictionaries for JSON output.

    Args:
        status: Status dictionary from ArrisStatusClient.get_status()

    Returns:
        Status dictionary with channels converted to JSON-serializable format
    """
    output = status.copy()

    # Convert downstream channels
    if "downstream_channels" in output:
        output["downstream_channels"] = [
            {
                "channel_id": ch.channel_id,
                "frequency": ch.frequency,
                "power": ch.power,
                "snr": ch.snr,
                "modulation": ch.modulation,
                "lock_status": ch.lock_status,
                "corrected_errors": ch.corrected_errors,
                "uncorrected_errors": ch.uncorrected_errors,
                "channel_type": ch.channel_type
            }
            for ch in output["downstream_channels"]
        ]

    # Convert upstream channels
    if "upstream_channels" in output:
        output["upstream_channels"] = [
            {
                "channel_id": ch.channel_id,
                "frequency": ch.frequency,
                "power": ch.power,
                "snr": ch.snr,
                "modulation": ch.modulation,
                "lock_status": ch.lock_status,
                "channel_type": ch.channel_type
            }
            for ch in output["upstream_channels"]
        ]

    return output


def print_summary_to_stderr(status: dict) -> None:
    """
    Print a human-readable summary to stderr (so JSON output to stdout is clean).

    Args:
        status: Parsed status dictionary from the modem
    """
    print("=" * 60, file=sys.stderr)
    print("ARRIS MODEM STATUS SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Model: {status.get('model_name', 'Unknown')}", file=sys.stderr)
    print(f"Internet Status: {status.get('internet_status', 'Unknown')}", file=sys.stderr)
    print(f"Connection Status: {status.get('connection_status', 'Unknown')}", file=sys.stderr)

    if status.get('mac_address', 'Unknown') != 'Unknown':
        print(f"MAC Address: {status.get('mac_address')}", file=sys.stderr)

    downstream_count = len(status.get('downstream_channels', []))
    upstream_count = len(status.get('upstream_channels', []))

    print(f"Downstream Channels: {downstream_count}", file=sys.stderr)
    print(f"Upstream Channels: {upstream_count}", file=sys.stderr)
    print(f"Channel Data Available: {status.get('channel_data_available', False)}", file=sys.stderr)

    # Show sample channel if available
    if downstream_count > 0:
        sample = status['downstream_channels'][0]
        sample_info = f"ID {sample.channel_id}, {sample.frequency}, {sample.power}, SNR {sample.snr}"
        print(f"Sample Channel: {sample_info}", file=sys.stderr)

    # Show error analysis if available
    error_analysis = status.get('_error_analysis')
    if error_analysis:
        total_errors = error_analysis.get('total_errors', 0)
        recovery_rate = error_analysis.get('recovery_rate', 0) * 100
        compatibility_issues = error_analysis.get('http_compatibility_issues', 0)

        print(f"Error Analysis: {total_errors} errors, {recovery_rate:.1f}% recovery", file=sys.stderr)
        if compatibility_issues > 0:
            print(f"HTTP Compatibility Issues Handled: {compatibility_issues}", file=sys.stderr)

    print("=" * 60, file=sys.stderr)


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(
        description="Query Arris cable modem status and output JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --password "your_password"
  %(prog)s --password "password" --host 192.168.1.1
  %(prog)s --password "password" --debug

Output:
  JSON object with modem status, channel information, and diagnostics.
  Summary information is printed to stderr, JSON data to stdout.

Monitoring Integration:
  The JSON output is designed for easy integration with monitoring systems.
  Use --quiet to suppress stderr output and get pure JSON on stdout.

HTTP Compatibility:
  The client automatically handles urllib3 parsing strictness issues with
  some Arris modem responses by falling back to browser-compatible parsing.
  All compatibility issues are gracefully handled with smart retry logic.

Serial Mode:
  Use --serial to disable concurrent requests for maximum compatibility.
  Serial mode is slower but provides the highest reliability for modems
  that may have issues with concurrent request processing.
        """
    )

    parser.add_argument(
        "--host",
        default="192.168.100.1",
        help="Modem hostname or IP address (default: %(default)s)"
    )
    parser.add_argument(
        "--port",
        default=443,
        type=int,
        help="HTTPS port for modem connection (default: %(default)s)"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Modem login username (default: %(default)s)"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Modem login password (required)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output to stderr"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output to stderr (JSON only to stdout)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: %(default)s)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of concurrent workers (default: %(default)s)"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: %(default)s)"
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="Use serial requests instead of concurrent (for maximum compatibility)"
    )

    args = parser.parse_args()

    # Configure logging
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    try:
        # Log startup information (to stderr)
        if not args.quiet:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            mode_str = "serial" if args.serial else "concurrent"
            print(f"Arris Modem Status Client v1.3.0 - {timestamp}", file=sys.stderr)
            print(f"Connecting to {args.host}:{args.port} as {args.username} ({mode_str} mode)", file=sys.stderr)

        # Initialize the client with HTTP compatibility
        client = ArrisStatusClient(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            concurrent=not args.serial,
            max_workers=args.workers,
            max_retries=args.retries,
            timeout=(3, args.timeout)
        )

        logger.info(f"Querying modem at {args.host}:{args.port}")

        # Get the modem status
        with client:
            status = client.get_status()

        # Print summary to stderr (unless quiet mode)
        if not args.quiet:
            print_summary_to_stderr(status)

        # Convert channel objects to JSON-serializable format
        json_output = format_channel_data_for_display(status)

        # Add metadata
        json_output["query_timestamp"] = datetime.now().isoformat()
        json_output["query_host"] = args.host
        json_output["client_version"] = "1.3.0"
        json_output["configuration"] = {
            "max_workers": args.workers,
            "max_retries": args.retries,
            "timeout": args.timeout,
            "concurrent_mode": not args.serial,
            "http_compatibility": True
        }

        # Output JSON to stdout (this is the primary output)
        print(json.dumps(json_output, indent=2))

        logger.info("Modem status retrieved successfully")

    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        print("Operation cancelled by user", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Failed to get modem status: {e}")

        # Print error to stderr
        print(f"Error: {e}", file=sys.stderr)

        if args.debug:
            # Print full traceback in debug mode
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            # Provide helpful suggestions for common issues
            print("\nTroubleshooting suggestions:", file=sys.stderr)
            print("1. Verify the modem password is correct", file=sys.stderr)
            print("2. Check that the modem IP address is reachable", file=sys.stderr)
            print("3. Ensure the modem web interface is enabled", file=sys.stderr)
            print("4. Try with --debug for more detailed error information", file=sys.stderr)
            print("5. Try --serial mode for maximum compatibility", file=sys.stderr)
            print("6. HTTP compatibility issues are automatically handled", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()