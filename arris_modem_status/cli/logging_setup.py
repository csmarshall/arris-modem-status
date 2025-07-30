"""
Logging Configuration Module

This module provides logging setup and configuration for the Arris Modem
Status CLI application.

Author: Charles Marshall
License: MIT
"""

import logging
import sys
from typing import Optional

_logging_configured = False


def setup_logging(
    debug: bool = False, quiet: bool = False, silent: bool = False, log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the CLI application.

    Args:
        debug: If True, enable debug-level logging
        quiet: If True, only show warnings and errors
        silent: If True, suppress all console output (like curl -s)
        log_file: Optional path to log file for output
    """
    global _logging_configured

    # Only configure logging once
    if _logging_configured:
        return

    _logging_configured = True

    # Determine log level based on flags
    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    # Base logging configuration
    handlers: list[logging.Handler] = []

    # Console handler (stderr) - only if not silent
    if not silent:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)

        # Create formatter
        if debug:
            # More detailed format for debug mode
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(funcName)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Simpler format for normal mode
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        handlers.append(console_handler)

    # File handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Configure the root logger
    # Replace any existing handlers
    logging.basicConfig(level=level, handlers=handlers, force=True)

    # Configure third-party libraries to be less verbose unless debug is enabled
    if not debug:
        # Reduce noise from urllib3 and requests
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
    else:
        # In debug mode, show more details from HTTP libraries
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)
        logging.getLogger("arris-modem-status").setLevel(logging.DEBUG)

    # Log initial setup
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured: level={logging.getLevelName(level)}, debug={debug}")
    if log_file:
        logger.debug(f"Logging to file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
