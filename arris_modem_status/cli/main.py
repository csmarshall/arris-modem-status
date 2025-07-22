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

from arris_modem_status import ArrisModemStatusClient, __version__

from .args import parse_args
from .connectivity import (
    get_optimal_timeouts,
    print_connectivity_troubleshooting,
    quick_connectivity_check,
)
from .formatters import (
    format_json_output,
    print_error_suggestions,
    print_json_output,
    print_summary_to_stderr,
)
from .logging_setup import setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the CLI application."""
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
        connectivity_checked = False
        if args.quick_check:
            is_reachable, error_msg = quick_connectivity_check(args.host, args.port, timeout=2.0)
            connectivity_checked = True

            if not is_reachable:
                elapsed = time.time() - start_time
                print(f"❌ {error_msg}", file=sys.stderr)
                print(
                    f"⏱️  Failed connectivity check after {elapsed:.1f}s",
                    file=sys.stderr,
                )

                # error_msg is guaranteed to be a string from quick_connectivity_check
                if error_msg:
                    print_connectivity_troubleshooting(args.host, args.port, error_msg)
                sys.exit(1)

        # Get optimal timeouts based on host type
        connect_timeout, read_timeout = get_optimal_timeouts(args.host)
        final_timeout = (connect_timeout, min(args.timeout, read_timeout))

        # Initialize the client with HTTP compatibility and optimal settings
        logger.info(f"Initializing ArrisModemStatusClient for {args.host}:{args.port}")
        client = ArrisModemStatusClient(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            concurrent=not args.serial,
            max_workers=args.workers,
            max_retries=args.retries,
            timeout=final_timeout,
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

        # Format and output JSON
        json_output = format_json_output(status, args, elapsed, connectivity_checked)
        print_json_output(json_output)

        logger.info(f"Modem status retrieved successfully in {elapsed:.2f}s")

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        logger.error(f"Operation cancelled by user after {elapsed:.2f}s")
        print(
            f"Operation cancelled by user after {elapsed:.2f}s",
            file=sys.stderr,
        )
        sys.exit(1)

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

        sys.exit(1)


if __name__ == "__main__":
    main()
