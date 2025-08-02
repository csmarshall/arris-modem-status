"""
Output Formatting Module

This module provides functions for formatting and displaying modem status
data in various formats, including JSON serialization and human-readable
summaries.

Author: Charles Marshall
License: MIT
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Any

from arris_modem_status import __version__

logger = logging.getLogger(__name__)


def format_channel_data_for_display(status: dict) -> dict:
    """
    Convert ChannelInfo objects to dictionaries for JSON serialization.

    Also filters out Python objects like datetime/timedelta that aren't JSON serializable
    and would be redundant in CLI output.

    The ArrisModemStatusClient returns ChannelInfo dataclass objects which need
    to be converted to dictionaries for JSON output.

    Args:
        status: Status dictionary from ArrisModemStatusClient.get_status()

    Returns:
        Status dictionary with channels converted to JSON-serializable format
        and Python objects filtered out for CLI display
    """
    logger.debug("Converting channel data for JSON serialization")
    output = status.copy()

    # Filter out Python datetime/timedelta objects (not JSON serializable and redundant in CLI)
    for key in list(output.keys()):
        if key.endswith("-datetime"):
            del output[key]
            logger.debug(f"Filtered out {key} for CLI display")

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
                "channel_type": ch.channel_type,
            }
            for ch in output["downstream_channels"]
        ]
        logger.debug(f"Converted {len(output['downstream_channels'])} downstream channels")

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
                "channel_type": ch.channel_type,
            }
            for ch in output["upstream_channels"]
        ]
        logger.debug(f"Converted {len(output['upstream_channels'])} upstream channels")

    return output


def print_summary_to_stderr(status: dict) -> None:
    """
    Print a human-readable summary to stderr (so JSON output to stdout is clean).

    Args:
        status: Parsed status dictionary from the modem
    """
    logger.debug("Printing status summary to stderr")

    print("=" * 60, file=sys.stderr)
    print("ARRIS MODEM STATUS SUMMARY", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Basic Information
    print(f"Model: {status.get('model_name', 'Unknown')}", file=sys.stderr)
    print(f"Hardware Version: {status.get('hardware_version', 'Unknown')}", file=sys.stderr)
    print(f"Firmware: {status.get('firmware_version', 'Unknown')}", file=sys.stderr)
    print(f"Uptime: {status.get('system_uptime', 'Unknown')}", file=sys.stderr)

    # Show enhanced time information if available
    if status.get("system_uptime-seconds"):
        uptime_days = status["system_uptime-seconds"] / 86400  # seconds to days
        print(f"Uptime (days): {uptime_days:.1f}", file=sys.stderr)

    # Connection Status
    print("Connection Status:", file=sys.stderr)
    print(f"  Internet: {status.get('internet_status', 'Unknown')}", file=sys.stderr)
    print(f"  Network Access: {status.get('network_access', 'Unknown')}", file=sys.stderr)
    print(f"  Boot Status: {status.get('boot_status', 'Unknown')}", file=sys.stderr)
    print(
        f"  Security: {status.get('security_status', 'Unknown')} ({status.get('security_comment', 'Unknown')})",
        file=sys.stderr,
    )

    # Downstream Status
    if status.get("downstream_frequency", "Unknown") != "Unknown":
        print("Downstream Status:", file=sys.stderr)
        print(f"  Frequency: {status.get('downstream_frequency', 'Unknown')}", file=sys.stderr)
        print(f"  Comment: {status.get('downstream_comment', 'Unknown')}", file=sys.stderr)

    # System Info
    if status.get("mac_address", "Unknown") != "Unknown":
        print("System Information:", file=sys.stderr)
        print(f"  MAC Address: {status.get('mac_address')}", file=sys.stderr)
        print(f"  Serial Number: {status.get('serial_number')}", file=sys.stderr)
        print(f"  Current Time: {status.get('current_system_time', 'Unknown')}", file=sys.stderr)

        # Show ISO8601 format if available
        if status.get("current_system_time-ISO8601"):
            print(f"  Current Time (ISO): {status.get('current_system_time-ISO8601')}", file=sys.stderr)

    # Channel Summary
    downstream_count = len(status.get("downstream_channels", []))
    upstream_count = len(status.get("upstream_channels", []))

    print("Channel Summary:", file=sys.stderr)
    print(f"  Downstream Channels: {downstream_count}", file=sys.stderr)
    print(f"  Upstream Channels: {upstream_count}", file=sys.stderr)
    print(f"  Channel Data Available: {status.get('channel_data_available', False)}", file=sys.stderr)

    # Show sample channel if available
    if downstream_count > 0:
        sample = status["downstream_channels"][0]
        sample_info = f"ID {sample.channel_id}, {sample.frequency}, {sample.power}, SNR {sample.snr}"
        if hasattr(sample, "corrected_errors") and sample.corrected_errors:
            sample_info += f", Errors: {sample.corrected_errors}/{sample.uncorrected_errors}"
        print(f"  Sample Channel: {sample_info}", file=sys.stderr)

    # Show error analysis if available
    error_analysis = status.get("_error_analysis")
    if error_analysis:
        total_errors = error_analysis.get("total_errors", 0)
        recovery_rate = error_analysis.get("recovery_rate", 0) * 100
        compatibility_issues = error_analysis.get("http_compatibility_issues", 0)
        http_403_errors = error_analysis.get("error_types", {}).get("http_403", 0)

        print("Error Analysis:", file=sys.stderr)
        print(f"  Total Errors: {total_errors}", file=sys.stderr)
        print(f"  Recovery Rate: {recovery_rate:.1f}%", file=sys.stderr)
        if compatibility_issues > 0:
            print(f"  HTTP Compatibility Issues: {compatibility_issues}", file=sys.stderr)
        if http_403_errors > 0:
            print(f"  ⚠️  HTTP 403 Errors: {http_403_errors} (modem rejected concurrent requests)", file=sys.stderr)

    # Mode information
    mode = status.get("_request_mode", "unknown")
    if mode == "concurrent":
        print("Running in PARALLEL mode - may cause data inconsistency!", file=sys.stderr)

    print("=" * 60, file=sys.stderr)


def format_json_output(
    status: dict[str, Any], args: argparse.Namespace, elapsed_time: float, connectivity_checked: bool
) -> dict:
    """
    Format the complete JSON output with metadata.

    Args:
        status: Status dictionary from the modem
        args: Parsed command line arguments
        elapsed_time: Total elapsed time for the operation
        connectivity_checked: Whether connectivity check was performed

    Returns:
        Complete JSON output dictionary
    """
    logger.debug("Formatting complete JSON output")

    # Convert channel objects to JSON-serializable format and filter out Python objects
    json_output = format_channel_data_for_display(status)

    # Get optimal timeouts for metadata
    from .connectivity import get_optimal_timeouts

    connect_timeout, read_timeout = get_optimal_timeouts(args.host)
    final_timeout = (connect_timeout, min(args.timeout, read_timeout))

    # Add metadata
    json_output["query_timestamp"] = datetime.now().isoformat()
    json_output["query_host"] = args.host
    json_output["client_version"] = __version__
    json_output["elapsed_time"] = elapsed_time
    json_output["configuration"] = {
        "max_workers": args.workers,
        "max_retries": args.retries,
        "timeout": final_timeout,
        "concurrent_mode": args.parallel,  # Now based on --parallel flag
        "http_compatibility": True,
        "quick_check_performed": connectivity_checked,
    }

    return json_output


def print_json_output(json_data: dict) -> None:
    """
    Print JSON output to stdout.

    Args:
        json_data: Dictionary to output as JSON
    """
    logger.debug("Outputting JSON to stdout")
    print(json.dumps(json_data, indent=2))


def print_error_suggestions(debug: bool = False) -> None:
    """
    Print helpful error suggestions.

    Args:
        debug: Whether debug mode is enabled
    """
    if debug:
        # Print full traceback in debug mode
        import traceback

        traceback.print_exc(file=sys.stderr)
    else:
        # Provide helpful suggestions for common issues
        print("Troubleshooting suggestions:", file=sys.stderr)
        print("1. Verify the modem password is correct", file=sys.stderr)
        print("2. Check that the modem IP address is reachable", file=sys.stderr)
        print("3. Ensure the modem web interface is enabled", file=sys.stderr)
        print(
            "4. Try with --debug for more detailed error information",
            file=sys.stderr,
        )
        print("5. Try without --parallel flag (serial mode is more reliable)", file=sys.stderr)
        print("6. Try --quick-check to test connectivity first", file=sys.stderr)
        print(
            "7. HTTP compatibility issues are automatically handled",
            file=sys.stderr,
        )
