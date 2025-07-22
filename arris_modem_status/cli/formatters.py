"""
Output Formatting Module

This module provides functions for formatting and displaying modem status
data in various formats, including JSON serialization and human-readable
summaries.

Author: Charles Marshall
License: MIT
"""

import json
import logging
import sys
from datetime import datetime

from arris_modem_status import __version__

logger = logging.getLogger(__name__)


def format_channel_data_for_display(status: dict) -> dict:
    """
    Convert ChannelInfo objects to dictionaries for JSON serialization.

    The ArrisModemStatusClient returns ChannelInfo dataclass objects which need
    to be converted to dictionaries for JSON output.

    Args:
        status: Status dictionary from ArrisModemStatusClient.get_status()

    Returns:
        Status dictionary with channels converted to JSON-serializable format
    """
    logger.debug("Converting channel data for JSON serialization")
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
                "channel_type": ch.channel_type,
            }
            for ch in output["downstream_channels"]
        ]
        logger.debug(
            f"Converted {len(output['downstream_channels'])} downstream channels")

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
        logger.debug(
            f"Converted {len(output['upstream_channels'])} upstream channels")

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
    print(f"Model: {status.get('model_name', 'Unknown')}", file=sys.stderr)
    print(
        f"Internet Status: {status.get('internet_status', 'Unknown')}", file=sys.stderr)
    print(
        f"Connection Status: {status.get('connection_status', 'Unknown')}", file=sys.stderr)

    if status.get("mac_address", "Unknown") != "Unknown":
        print(f"MAC Address: {status.get('mac_address')}", file=sys.stderr)

    downstream_count = len(status.get("downstream_channels", []))
    upstream_count = len(status.get("upstream_channels", []))

    print(f"Downstream Channels: {downstream_count}", file=sys.stderr)
    print(f"Upstream Channels: {upstream_count}", file=sys.stderr)
    print(
        f"Channel Data Available: {status.get('channel_data_available', False)}", file=sys.stderr)

    # Show sample channel if available
    if downstream_count > 0:
        sample = status["downstream_channels"][0]
        sample_info = f"ID {sample.channel_id}, {sample.frequency}, {sample.power}, SNR {sample.snr}"
        print(f"Sample Channel: {sample_info}", file=sys.stderr)

    # Show error analysis if available
    error_analysis = status.get("_error_analysis")
    if error_analysis:
        total_errors = error_analysis.get("total_errors", 0)
        recovery_rate = error_analysis.get("recovery_rate", 0) * 100
        compatibility_issues = error_analysis.get(
            "http_compatibility_issues", 0)

        print(
            f"Error Analysis: {total_errors} errors, {recovery_rate:.1f}% recovery", file=sys.stderr)
        if compatibility_issues > 0:
            print(
                f"HTTP Compatibility Issues Handled: {compatibility_issues}", file=sys.stderr)

    print("=" * 60, file=sys.stderr)


def format_json_output(status: dict, args, elapsed_time: float, connectivity_checked: bool) -> dict:
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

    # Convert channel objects to JSON-serializable format
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
        "concurrent_mode": not args.serial,
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
        print("\nTroubleshooting suggestions:", file=sys.stderr)
        print("1. Verify the modem password is correct", file=sys.stderr)
        print("2. Check that the modem IP address is reachable", file=sys.stderr)
        print("3. Ensure the modem web interface is enabled", file=sys.stderr)
        print("4. Try with --debug for more detailed error information",
              file=sys.stderr)
        print("5. Try --serial mode for maximum compatibility", file=sys.stderr)
        print("6. Try --quick-check to test connectivity first", file=sys.stderr)
        print("7. HTTP compatibility issues are automatically handled", file=sys.stderr)
