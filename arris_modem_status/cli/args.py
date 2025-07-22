"""
Command Line Argument Parsing Module

This module handles all argument parsing and validation for the Arris Modem
Status CLI. It defines the command-line interface and validates user inputs.

Author: Charles Marshall
License: MIT
"""

import argparse
import logging

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance
    """
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
        """,
    )

    # Connection settings
    parser.add_argument(
        "--host",
        default="192.168.100.1",
        help="Modem hostname or IP address (default: %(default)s)",
    )
    parser.add_argument(
        "--port",
        default=443,
        type=int,
        help="HTTPS port for modem connection (default: %(default)s)",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Modem login username (default: %(default)s)",
    )
    parser.add_argument("--password", required=True, help="Modem login password (required)")

    # Output options
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging output to stderr",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress summary output to stderr (JSON only to stdout)",
    )

    # Performance options
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of concurrent workers (default: %(default)s)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: %(default)s)",
    )
    parser.add_argument(
        "--serial",
        action="store_true",
        help="Use serial requests instead of concurrent (for maximum compatibility)",
    )
    parser.add_argument(
        "--quick-check",
        action="store_true",
        help="Perform quick connectivity check before attempting connection",
    )

    return parser


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = create_parser()
    args = parser.parse_args()

    logger.debug(f"Parsed arguments: {args}")

    # Validate arguments
    validate_args(args)

    return args


def validate_args(args: argparse.Namespace) -> None:
    """
    Validate parsed arguments.

    Args:
        args: Parsed arguments namespace

    Raises:
        ValueError: If arguments are invalid
    """
    # Validate timeout
    if args.timeout <= 0:
        raise ValueError("Timeout must be greater than 0")

    # Validate workers
    if args.workers < 1:
        raise ValueError("Workers must be at least 1")

    # Validate retries
    if args.retries < 0:
        raise ValueError("Retries cannot be negative")

    # Validate port
    if args.port < 1 or args.port > 65535:
        raise ValueError("Port must be between 1 and 65535")

    logger.debug("Arguments validated successfully")
