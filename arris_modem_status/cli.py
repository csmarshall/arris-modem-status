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

NEW: Quick connectivity check and improved error handling with proper variable scoping.

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

    # Quick connectivity check before attempting connection
    arris-modem-status --password "password" --quick-check

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
import socket
import sys
import time
from datetime import datetime
from typing import Tuple, Optional

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


def quick_connectivity_check(host: str, port: int = 443, timeout: float = 2.0) -> Tuple[bool, Optional[str]]:
    """
    Quick TCP connectivity check before attempting HTTPS connection.
    
    This helps fail fast for unreachable devices instead of waiting for long timeouts.
    Since Arris modems are typically on local networks, if they don't respond quickly,
    they're likely offline or unreachable.
    
    Args:
        host: Target hostname or IP address
        port: Target port (default: 443 for HTTPS)
        timeout: Connection timeout in seconds (default: 2.0)
        
    Returns:
        (is_reachable, error_message) - error_message is None if reachable
    """
    try:
        print(f"🔍 Quick connectivity check: {host}:{port}...", file=sys.stderr)
        
        with socket.create_connection((host, port), timeout=timeout):
            print(f"✅ TCP connection successful", file=sys.stderr)
            return True, None
            
    except socket.timeout:
        return False, f"Connection timeout - {host}:{port} not responding within {timeout}s"
    except socket.gaierror as e:
        return False, f"DNS resolution failed for {host}: {e}"
    except ConnectionRefusedError:
        return False, f"Connection refused - {host}:{port} not accepting connections"
    except OSError as e:
        return False, f"Network error connecting to {host}:{port}: {e}"


def get_optimal_timeouts(host: str) -> Tuple[float, float]:
    """
    Get optimal connection timeouts based on whether the host appears to be local.
    
    Args:
        host: Target hostname or IP address
        
    Returns:
        (connect_timeout, read_timeout) in seconds
    """
    # Check if this appears to be a local network address
    is_local = (
        host.startswith('192.168.') or
        host.startswith('10.') or
        host.startswith('172.') or
        host in ['localhost', '127.0.0.1']
    )
    
    if is_local:
        return (2, 8)  # Shorter timeouts for local devices
    else:
        return (5, 15)  # Longer timeouts for remote access


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


def print_connectivity_troubleshooting(host: str, port: int, error_msg: str) -> None:
    """Print specific troubleshooting suggestions based on the connection error."""
    print(f"\n💡 TROUBLESHOOTING for {host}:{port}:", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    if "timeout" in error_msg.lower():
        print("Connection timeout suggests:", file=sys.stderr)
        print(f"  1. Device may be offline - verify {host} is powered on", file=sys.stderr)
        print(f"  2. Wrong IP address - check your modem's current IP", file=sys.stderr)
        print(f"  3. Network issue - try: ping {host}", file=sys.stderr)
        print(f"  4. Firewall blocking connection", file=sys.stderr)
        
    elif "refused" in error_msg.lower():
        print("Connection refused suggests:", file=sys.stderr)
        print(f"  1. Device is on but HTTPS service disabled", file=sys.stderr)
        print(f"  2. Try HTTP instead: --port 80", file=sys.stderr)
        print(f"  3. Web interface may be disabled", file=sys.stderr)
        
    elif "dns" in error_msg.lower() or "resolution" in error_msg.lower():
        print("DNS resolution failed suggests:", file=sys.stderr)
        print(f"  1. Use IP address instead of hostname", file=sys.stderr)
        print(f"  2. Check DNS settings", file=sys.stderr)
        print(f"  3. Verify hostname spelling", file=sys.stderr)
        
    else:
        print("Network connectivity issue:", file=sys.stderr)
        print(f"  1. Verify device IP: {host}", file=sys.stderr)
        print(f"  2. Check network connectivity: ping {host}", file=sys.stderr)
        print(f"  3. Try web interface: https://{host}/", file=sys.stderr)
        print(f"  4. Check if device is on the same network", file=sys.stderr)
        
    print(f"\n🔧 Quick tests:", file=sys.stderr)
    print(f"  ping {host}", file=sys.stderr)
    print(f"  curl -k https://{host}/ --connect-timeout 5", file=sys.stderr)


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

Quick Check:
  Use --quick-check to perform a fast connectivity test before attempting
  the full connection. This helps identify unreachable devices quickly.
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
    parser.add_argument(
        "--quick-check",
        action="store_true",
        help="Perform quick connectivity check before attempting connection"
    )

    args = parser.parse_args()

    # IMPORTANT: Define start_time at function scope to avoid variable scoping issues
    start_time = time.time()

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

        # NEW: Quick connectivity check if requested or if we detect this might fail
        connectivity_checked = False
        if args.quick_check:
            is_reachable, error_msg = quick_connectivity_check(args.host, args.port, timeout=2.0)
            connectivity_checked = True
            
            if not is_reachable:
                elapsed = time.time() - start_time
                print(f"❌ {error_msg}", file=sys.stderr)
                print(f"⏱️  Failed connectivity check after {elapsed:.1f}s", file=sys.stderr)
                
                print_connectivity_troubleshooting(args.host, args.port, error_msg)
                sys.exit(1)

        # Get optimal timeouts based on host type
        connect_timeout, read_timeout = get_optimal_timeouts(args.host)
        final_timeout = (connect_timeout, min(args.timeout, read_timeout))

        # Initialize the client with HTTP compatibility and optimal settings
        client = ArrisStatusClient(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            concurrent=not args.serial,
            max_workers=args.workers,
            max_retries=args.retries,
            timeout=final_timeout
        )

        logger.info(f"Querying modem at {args.host}:{args.port}")

        # Get the modem status
        with client:
            status = client.get_status()

        # Calculate elapsed time
        elapsed = time.time() - start_time

        # Print summary to stderr (unless quiet mode)
        if not args.quiet:
            print_summary_to_stderr(status)

        # Convert channel objects to JSON-serializable format
        json_output = format_channel_data_for_display(status)

        # Add metadata
        json_output["query_timestamp"] = datetime.now().isoformat()
        json_output["query_host"] = args.host
        json_output["client_version"] = "1.3.0"
        json_output["elapsed_time"] = elapsed
        json_output["configuration"] = {
            "max_workers": args.workers,
            "max_retries": args.retries,
            "timeout": final_timeout,
            "concurrent_mode": not args.serial,
            "http_compatibility": True,
            "quick_check_performed": connectivity_checked
        }

        # Output JSON to stdout (this is the primary output)
        print(json.dumps(json_output, indent=2))

        logger.info(f"Modem status retrieved successfully in {elapsed:.2f}s")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        logger.error(f"Operation cancelled by user after {elapsed:.2f}s")
        print(f"Operation cancelled by user after {elapsed:.2f}s", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Failed to get modem status after {elapsed:.2f}s: {e}")

        # Print error to stderr with elapsed time
        print(f"Error after {elapsed:.2f}s: {e}", file=sys.stderr)

        # Check if this looks like a connectivity issue and we haven't done a quick check
        error_str = str(e).lower()
        is_connectivity_error = any(term in error_str for term in [
            'timeout', 'connection', 'refused', 'unreachable', 'network'
        ])

        if is_connectivity_error and not connectivity_checked:
            print_connectivity_troubleshooting(args.host, args.port, str(e))
        elif args.debug:
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
            print("6. Try --quick-check to test connectivity first", file=sys.stderr)
            print("7. HTTP compatibility issues are automatically handled", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
