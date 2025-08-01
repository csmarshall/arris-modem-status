"""
Command Line Argument Parsing Module

This module handles all argument parsing and validation for the Arris Modem
Status CLI. It defines the command-line interface and validates user inputs.

Author: Charles Marshall
License: MIT
"""

import argparse
import logging

from arris_modem_status.exceptions import ArrisConfigurationError

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser for the CLI.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog="arris-modem-status",  # Explicitly set prog to avoid issues
        description="Query Arris cable modem status and output JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  arris-modem-status --password "your_password"
  arris-modem-status --password "password" --host 192.168.1.1
  arris-modem-status --password "password" --debug
  arris-modem-status --password "password" --parallel  # Use concurrent mode (may cause issues)

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

Serial vs Parallel Mode:
  DEFAULT: Serial mode (sequential requests) for maximum compatibility.
  Many Arris modems have issues with concurrent HNAP requests, causing
  HTTP 403 errors and inconsistent data. Serial mode is slower but more
  reliable. Use --parallel at your own risk for ~30%% speed improvement
  if your modem supports it.

Quick Check:
  Use --quick-check to perform a fast connectivity test before attempting
  the full connection. This helps identify unreachable devices quickly.

Complete Data:
  The library now retrieves ALL modem information including:
  - Model name and hardware version
  - Firmware version
  - System uptime
  - Boot status and security status
  - Channel information with error counts
  - Connection states and timing
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
        help="Number of concurrent workers when using --parallel (default: %(default)s)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Maximum retry attempts (default: %(default)s)",
    )

    # Changed: --serial is now deprecated, --parallel enables concurrent mode
    parser.add_argument(
        "--serial",
        action="store_true",
        help="DEPRECATED: Serial mode is now the default. This flag does nothing.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use parallel/concurrent requests (WARNING: May cause HTTP 403 errors and inconsistent data on many modems)",
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

    Raises:
        ArrisConfigurationError: If arguments are invalid
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
        ArrisConfigurationError: If arguments are invalid
    """
    # Validate timeout
    if args.timeout <= 0:
        raise ArrisConfigurationError(
            "Timeout must be greater than 0",
            details={"parameter": "timeout", "value": args.timeout, "valid_range": "> 0"},
        )

    # Validate workers
    if args.workers < 1:
        raise ArrisConfigurationError(
            "Workers must be at least 1",
            details={"parameter": "workers", "value": args.workers, "valid_range": ">= 1"},
        )

    # Validate retries
    if args.retries < 0:
        raise ArrisConfigurationError(
            "Retries cannot be negative",
            details={"parameter": "retries", "value": args.retries, "valid_range": ">= 0"},
        )

    # Validate port
    if args.port < 1 or args.port > 65535:
        raise ArrisConfigurationError(
            "Port must be between 1 and 65535",
            details={"parameter": "port", "value": args.port, "valid_range": "1-65535"},
        )

    # Warn about --parallel mode
    if args.parallel:
        logger.warning("⚠️  Using --parallel mode may cause HTTP 403 errors and inconsistent data on many modems!")

    logger.debug("Arguments validated successfully")
