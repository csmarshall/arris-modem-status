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
from typing import Any, Optional

from arris_modem_status import ArrisModemStatusClient, __version__
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConfigurationError,
    ArrisConnectionError,
    ArrisModemError,
    ArrisOperationError,
    ArrisTimeoutError,
)

from .args import parse_args
from .connectivity import get_optimal_timeouts, print_connectivity_troubleshooting, quick_connectivity_check
from .formatters import format_json_output, print_error_suggestions, print_json_output, print_summary_to_stderr
from .logging_setup import setup_logging

logger = logging.getLogger(__name__)


def create_client(args: Any, client_class: Optional[type[ArrisModemStatusClient]] = None) -> ArrisModemStatusClient:
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

    # Handle the new default: serial mode unless --parallel is specified
    concurrent_mode = args.parallel  # Only concurrent if --parallel flag is used

    return client_class(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        concurrent=concurrent_mode,
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


def main(client_class: Optional[type[ArrisModemStatusClient]] = None) -> Optional[int]:  # noqa: PLR0911
    """
    Main entry point for the CLI application.

    Orchestrates argument parsing, client creation, status retrieval, and output
    formatting. Designed for robust error handling and clean JSON output suitable
    for monitoring systems.

    Args:
        client_class: Optional client class to use (primarily for testing)

    Returns:
        Exit code (0 for success, 1 for error), or None for successful completion

    Output:
        The CLI outputs JSON to stdout and human-readable summaries to stderr.
        This design allows for easy integration with monitoring tools:

        * stdout: Clean JSON data for programmatic use
        * stderr: Human-readable status summaries and error messages

    Examples:
        Basic usage:

        >>> main()  # Uses sys.argv for arguments

        Testing with mock client:

        >>> mock_client = Mock()
        >>> exit_code = main(client_class=mock_client)

    Exit Codes:
        * 0 or None: Success
        * 1: Any error (authentication, connection, operation, etc.)

    Error Handling:
        The function provides specific error messages for different failure modes:

        * ArrisAuthenticationError: Password verification suggestions
        * ArrisConnectionError: Network troubleshooting information
        * ArrisTimeoutError: Timeout adjustment recommendations
        * ArrisOperationError: Mode-specific suggestions (serial vs concurrent)

    Note:
        Uses start_time at function scope to avoid variable scoping issues
        in error handling paths.
    """
    # IMPORTANT: Define start_time at function scope to avoid variable scoping issues
    start_time = time.time()

    # Initialize args to None to handle error cases
    args = None

    try:
        # Parse command line arguments
        args = parse_args()

        # Configure logging based on debug flag
        setup_logging(debug=args.debug)

        # Log startup information (to stderr)
        if not args.quiet:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            mode_str = "parallel" if args.parallel else "serial"
            print(
                f"Arris Modem Status Client v{__version__} - {timestamp}",
                file=sys.stderr,
            )
            print(
                f"Connecting to {args.host}:{args.port} as {args.username} ({mode_str} mode)",
                file=sys.stderr,
            )
            if args.parallel:
                print(
                    "⚠️  WARNING: Parallel mode may cause HTTP 403 errors and inconsistent data!",
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

    except ArrisConfigurationError as e:
        # Configuration errors - show the error and usage help
        elapsed = time.time() - start_time
        logger.error(f"Configuration error after {elapsed:.2f}s: {e}")
        print(f"Configuration error: {e}", file=sys.stderr)
        print("Run with --help for usage information", file=sys.stderr)
        return 1

    except ArrisAuthenticationError as e:
        # Authentication failures - likely wrong password
        elapsed = time.time() - start_time
        logger.error(f"Authentication failed after {elapsed:.2f}s: {e}")
        print(f"❌ Authentication error: {e}", file=sys.stderr)
        print("Please verify your password is correct", file=sys.stderr)
        return 1

    except ArrisTimeoutError as e:
        # Timeout errors - network or modem too slow
        elapsed = time.time() - start_time
        logger.error(f"Timeout after {elapsed:.2f}s: {e}")
        print(f"⏱️  Timeout error: {e}", file=sys.stderr)
        print("Try increasing --timeout or check network connectivity", file=sys.stderr)
        return 1

    except ArrisConnectionError as e:
        # Connection errors - can't reach modem
        elapsed = time.time() - start_time
        logger.error(f"Connection failed after {elapsed:.2f}s: {e}")
        print(f"🔌 Connection error: {e}", file=sys.stderr)

        # Show connectivity troubleshooting if not already done
        # Only use args if it was successfully parsed
        if args and not args.quick_check and hasattr(e, "details"):
            host = e.details.get("host", args.host)
            port = e.details.get("port", args.port)
            print_connectivity_troubleshooting(host, port, str(e))

        return 1

    except ArrisOperationError as e:
        # Operation failures - modem returned errors or invalid data
        elapsed = time.time() - start_time
        logger.error(f"Operation failed after {elapsed:.2f}s: {e}")
        print(f"⚠️  Operation error: {e}", file=sys.stderr)

        # Only use args if it was successfully parsed
        if args and args.parallel:
            print("Try removing --parallel flag for better compatibility", file=sys.stderr)
        else:
            print("The modem may be unresponsive. Try increasing --retries", file=sys.stderr)

        return 1

    except ArrisModemError as e:
        # Other Arris-specific errors
        elapsed = time.time() - start_time
        logger.error(f"Modem error after {elapsed:.2f}s: {e}")
        print(f"Error: {e}", file=sys.stderr)
        # Only use args.debug if args was successfully parsed
        print_error_suggestions(debug=args.debug if args else False)
        return 1

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        logger.error(f"Operation cancelled by user after {elapsed:.2f}s")
        print(
            f"Operation cancelled by user after {elapsed:.2f}s",
            file=sys.stderr,
        )
        return 1

    except SystemExit:
        # This is expected when argparse handles --help or errors
        # Just re-raise it without wrapping
        raise

    except Exception as e:
        # Unexpected errors - show full details in debug mode
        elapsed = time.time() - start_time
        logger.error(f"Unexpected error after {elapsed:.2f}s: {e}")

        # Use repr() to avoid string formatting issues
        error_msg = repr(e) if hasattr(e, "__repr__") else str(type(e))

        # Print error to stderr with elapsed time
        print(f"Unexpected error after {elapsed:.2f}s: {error_msg}", file=sys.stderr)

        # Check if this looks like a connectivity issue and we haven't done a quick check
        error_str = str(e).lower() if hasattr(e, "__str__") else ""
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

        # Only use args if it was successfully parsed
        if args and is_connectivity_error and not args.quick_check:
            print_connectivity_troubleshooting(args.host, args.port, str(e))

        # Only use args.debug if args was successfully parsed
        print_error_suggestions(debug=args.debug if args else False)

        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
