"""
Main CLI Orchestration Module

This module provides the main entry point and orchestration logic for the
Arris Modem Status CLI. It coordinates all other CLI modules to provide
a cohesive command-line interface.

Author: Charles Marshall
License: MIT
"""

import logging
import sys
import time
from datetime import datetime
from typing import Any, Optional, Type

from arris_modem_status import ArrisModemStatusClient, __version__

from .args import parse_args
from .connectivity import get_optimal_timeouts, print_connectivity_troubleshooting, quick_connectivity_check
from .formatters import format_json_output, print_error_suggestions, print_json_output, print_summary_to_stderr
from .logging_setup import setup_logging

logger = logging.getLogger(__name__)


def create_client(args: Any, client_class: Optional[Type[ArrisModemStatusClient]] = None) -> ArrisModemStatusClient:
    """
    Factory function to create the Arris client.

    This is separated out to make testing easier - tests can mock this function
    or pass a different client_class.

    Args:
        args: Parsed command line arguments
        client_class: Optional client class to use (for testing)

    Returns:
        Configured ArrisModemStatusClient instance
    """
    if client_class is None:
        client_class = ArrisModemStatusClient

    # Get optimal timeouts based on host type
    connect_timeout, read_timeout = get_optimal_timeouts(args.host)
    final_timeout = (connect_timeout, min(args.timeout, read_timeout))

    logger.info(f"Initializing ArrisModemStatusClient for {args.host}:{args.port}")

    return client_class(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        concurrent=not args.serial,
        max_workers=args.workers,
        max_retries=args.retries,
        timeout=final_timeout,
    )


def perform_connectivity_check(args: Any) -> bool:
    """
    Perform connectivity check if requested.

    Args:
        args: Parsed command line arguments

    Returns:
        True if connectivity check passed or not requested, False otherwise
    """
    if not args.quick_check:
        return True

    is_reachable, error_msg = quick_connectivity_check(args.host, args.port, timeout=2.0)

    if not is_reachable:
        print(f"❌ {error_msg}", file=sys.stderr)
        if error_msg:
            print_connectivity_troubleshooting(args.host, args.port, error_msg)
        return False

    return True


def process_modem_status(
    client: ArrisModemStatusClient, args: Any, start_time: float, connectivity_checked: bool
) -> None:
    """
    Process the modem status request and output results.

    Args:
        client: Configured ArrisModemStatusClient
        args: Parsed command line arguments
        start_time: Start time of the operation
        connectivity_checked: Whether connectivity check was performed
    """
    # Get the modem status
    with client:
        status = client.get_status()

    # Calculate elapsed time
    elapsed = time.time() - start_time

    # Print summary to stderr (unless quiet mode)
    if not args.quiet:
        print_summary_to_stderr(status)

    # Format and output JSON
    json_output = format_json_output(status, args, elapsed, connectivity_checked)
    print_json_output(json_output)


def main(client_class: Optional[Type[ArrisModemStatusClient]] = None) -> Optional[int]:
    """
    Main entry point for the CLI application.

    Args:
        client_class: Optional client class to use (for testing)

    Returns:
        Exit code (0 for success, 1 for error), or None for successful completion
    """
    # IMPORTANT: Define start_time at function scope to avoid variable scoping issues
    start_time = time.time()

    try:
        # Parse command line arguments
        args = parse_args()

        # Configure logging based on debug flag
        setup_logging(debug=args.debug)

        # Log startup information (to stderr)
        if not args.quiet:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            mode_str = "serial" if args.serial else "concurrent"
            print(
                f"Arris Modem Status Client v{__version__} - {timestamp}",
                file=sys.stderr,
            )
            print(
                f"Connecting to {args.host}:{args.port} as {args.username} ({mode_str} mode)",
                file=sys.stderr,
            )

        # Perform connectivity check if requested
        connectivity_checked = args.quick_check
        if not perform_connectivity_check(args):
            elapsed = time.time() - start_time
            print(
                f"⏱️  Failed connectivity check after {elapsed:.1f}s",
                file=sys.stderr,
            )
            return 1

        # Create the client
        client = create_client(args, client_class)

        logger.info(f"Querying modem at {args.host}:{args.port}")

        # Process the modem status
        process_modem_status(client, args, start_time, connectivity_checked)

        elapsed = time.time() - start_time
        logger.info(f"Modem status retrieved successfully in {elapsed:.2f}s")

        # Successful completion returns None (implicitly 0)
        return None

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        logger.error(f"Operation cancelled by user after {elapsed:.2f}s")
        print(
            f"Operation cancelled by user after {elapsed:.2f}s",
            file=sys.stderr,
        )
        return 1

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Failed to get modem status after {elapsed:.2f}s: {e}")

        # Print error to stderr with elapsed time
        print(f"Error after {elapsed:.2f}s: {e}", file=sys.stderr)

        # Check if this looks like a connectivity issue and we haven't done a quick check
        error_str = str(e).lower()
        is_connectivity_error = any(
            term in error_str
            for term in [
                "timeout",
                "connection",
                "refused",
                "unreachable",
                "network",
            ]
        )

        if is_connectivity_error and not connectivity_checked:
            print_connectivity_troubleshooting(args.host, args.port, str(e))

        print_error_suggestions(debug=args.debug)

        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
