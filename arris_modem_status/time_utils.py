"""
Time Parsing Utilities for Arris Modem Status Client
===================================================

This module provides utilities for parsing time-related data from Arris modems
and converting them to Python datetime/timedelta objects and standardized formats.

The Arris modems return time data in various human-readable formats that need to be
parsed into structured Python objects for programmatic use. This module handles:

- System uptime parsing from formats like "7 days 14:23:56" or "27 day(s) 10h:12m:37s"
- Current system time parsing from MM/DD/YYYY HH:MM:SS format
- Conversion to ISO8601 standardized format
- Enhancement of status dictionaries with parsed time fields

Examples:
    Basic usage for parsing individual time values:

    >>> from arris_modem_status.time_utils import parse_modem_datetime, parse_modem_duration
    >>> dt = parse_modem_datetime("07/30/2025 23:31:23")
    >>> td = parse_modem_duration("7 days 14:23:56")
    >>> print(f"Parsed: {dt}, Duration: {td}")

    Automatic enhancement of status data:

    >>> status = {"system_uptime": "27 day(s) 10h:12m:37s"}
    >>> enhanced = enhance_status_with_time_fields(status)
    >>> print(f"Uptime in seconds: {enhanced['system_uptime-seconds']}")

The module automatically enhances status dictionaries returned by the main client,
adding Python datetime/timedelta objects alongside the original string values.
This provides both human-readable and programmatically-accessible time data.

Author: Charles Marshall
License: MIT
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Compiled regex patterns for duration parsing - compiled once for performance
DURATION_PATTERN_1 = re.compile(r"(\d+)\s+days?\s+(\d+):(\d+):(\d+)")  # "7 days 14:23:56"
DURATION_PATTERN_2 = re.compile(r"(\d+)\s+day\(s\)\s+(\d+)h:(\d+)m:(\d+)s")  # "27 day(s) 10h:12m:37s"


def parse_modem_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse modem datetime string to Python datetime object.

    Arris modems return system time in MM/DD/YYYY HH:MM:SS format. This function
    converts that format into a Python datetime object for programmatic use.

    Args:
        date_str: Date/time string from modem in format "MM/DD/YYYY HH:MM:SS"
                 Example: "07/30/2025 23:31:23"

    Returns:
        datetime object if parsing succeeds, None if parsing fails or input is invalid

    Examples:
        >>> dt = parse_modem_datetime("07/30/2025 23:31:23")
        >>> print(dt.year, dt.month, dt.day)
        2025 7 30

        >>> dt = parse_modem_datetime("Unknown")
        >>> print(dt)
        None

    Note:
        The function is tolerant of whitespace and handles "Unknown" values gracefully.
        Invalid date strings will return None rather than raising exceptions.
    """
    if not date_str or date_str == "Unknown":
        return None

    try:
        # Handle the format used by Arris modems: MM/DD/YYYY HH:MM:SS
        return datetime.strptime(date_str.strip(), "%m/%d/%Y %H:%M:%S")  # noqa: DTZ007
    except ValueError as e:
        logger.debug(f"Failed to parse datetime '{date_str}': {e}")
        return None


def parse_modem_duration(duration_str: str) -> Optional[timedelta]:
    """
    Parse modem duration string to Python timedelta object.

    Arris modems return system uptime in various human-readable formats. This function
    converts those formats into Python timedelta objects for calculations and comparisons.

    Supported formats:
        - "7 days 14:23:56" (days with HH:MM:SS)
        - "27 day(s) 10h:12m:37s" (parenthetical days with h:m:s notation)
        - Both singular and plural "day"/"days" forms

    Args:
        duration_str: Duration string from modem
                     Examples: "7 days 14:23:56", "27 day(s) 10h:12m:37s"

    Returns:
        timedelta object if parsing succeeds, None if parsing fails or input is invalid

    Examples:
        >>> td = parse_modem_duration("7 days 14:23:56")
        >>> print(f"Total seconds: {td.total_seconds()}")
        656636.0

        >>> td = parse_modem_duration("27 day(s) 10h:12m:37s")
        >>> print(f"Days: {td.days}, Hours: {td.seconds // 3600}")
        27 10

        >>> td = parse_modem_duration("Unknown")
        >>> print(td)
        None

    Note:
        The function uses compiled regex patterns for performance and handles
        both format variations that different Arris firmware versions produce.
    """
    if not duration_str or duration_str == "Unknown":
        return None

    duration_str = duration_str.strip()

    # Try format 1: "7 days 14:23:56"
    match = DURATION_PATTERN_1.match(duration_str)
    if match:
        days, hours, minutes, seconds = map(int, match.groups())
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    # Try format 2: "27 day(s) 10h:12m:37s"
    match = DURATION_PATTERN_2.match(duration_str)
    if match:
        days, hours, minutes, seconds = map(int, match.groups())
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    logger.debug(f"Failed to parse duration '{duration_str}': unknown format")
    return None


def datetime_to_iso8601(dt: datetime) -> str:
    """
    Convert datetime to ISO8601 string format.

    Provides a standardized string representation of datetime objects suitable
    for APIs, logging, and data exchange. ISO8601 is the international standard
    for date/time representation.

    Args:
        dt: datetime object to convert

    Returns:
        ISO8601 formatted string (e.g., "2025-07-30T23:31:23")

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2025, 7, 30, 23, 31, 23)
        >>> iso_str = datetime_to_iso8601(dt)
        >>> print(iso_str)
        2025-07-30T23:31:23

        >>> # With microseconds
        >>> dt = datetime(2025, 7, 30, 23, 31, 23, 123456)
        >>> iso_str = datetime_to_iso8601(dt)
        >>> print(iso_str)
        2025-07-30T23:31:23.123456

    Note:
        The function preserves microseconds if present in the original datetime.
        This format is compatible with most modern APIs and database systems.
    """
    return dt.isoformat()


def timedelta_to_seconds(td: timedelta) -> float:
    """
    Convert timedelta to total seconds.

    Provides a simple numeric representation of time durations for calculations,
    monitoring systems, and APIs that expect duration in seconds.

    Args:
        td: timedelta object to convert

    Returns:
        Total seconds as float (includes fractional seconds if present)

    Examples:
        >>> from datetime import timedelta
        >>> td = timedelta(days=1, hours=2, minutes=30)
        >>> seconds = timedelta_to_seconds(td)
        >>> print(f"Duration: {seconds} seconds")
        Duration: 95400.0 seconds

        >>> # With fractional seconds
        >>> td = timedelta(seconds=30, microseconds=500000)
        >>> seconds = timedelta_to_seconds(td)
        >>> print(f"Duration: {seconds} seconds")
        Duration: 30.5 seconds

    Note:
        This is a convenience wrapper around timedelta.total_seconds() for
        consistency with the module's API and explicit type annotation.
    """
    return td.total_seconds()


def enhance_status_with_time_fields(status_data: dict) -> dict:
    """
    Enhance status data with parsed time fields.

    This function takes the parsed status data from the modem and adds additional
    time-related fields with Python objects and standardized formats. It creates
    a "batteries included" experience where time data is available in multiple
    useful formats without replacing the original string values.

    The function processes these fields if present:
        - 'current_system_time': Adds datetime object and ISO8601 string
        - 'system_uptime': Adds timedelta object and total seconds

    Generated fields use suffixes to avoid conflicts:
        - '-datetime': Python datetime/timedelta object
        - '-ISO8601': ISO8601 formatted string
        - '-seconds': Total seconds (for durations)

    Args:
        status_data: Dictionary with modem status data containing time strings

    Returns:
        Enhanced dictionary with original data plus parsed time fields

    Examples:
        Basic enhancement:

        >>> status = {
        ...     "model_name": "S34",
        ...     "current_system_time": "07/30/2025 23:31:23",
        ...     "system_uptime": "7 days 14:23:56"
        ... }
        >>> enhanced = enhance_status_with_time_fields(status)
        >>> print(enhanced["current_system_time-ISO8601"])
        2025-07-30T23:31:23
        >>> print(enhanced["system_uptime-seconds"])
        656636.0

        Graceful handling of missing/invalid data:

        >>> status = {"system_uptime": "Unknown", "other_field": "preserved"}
        >>> enhanced = enhance_status_with_time_fields(status)
        >>> print("system_uptime-datetime" in enhanced)
        False
        >>> print(enhanced["other_field"])
        preserved

    Note:
        The function is conservative - it only adds fields when parsing succeeds.
        Original fields are never modified or removed. Invalid time strings
        simply don't generate additional fields rather than causing errors.

        This approach allows monitoring systems to access time data as Python
        objects for calculations while preserving the original string format
        for display and debugging purposes.
    """
    enhanced_data = status_data.copy()

    # Process current_system_time
    if "current_system_time" in enhanced_data:
        current_time_str = enhanced_data["current_system_time"]

        # Parse to datetime object
        parsed_datetime = parse_modem_datetime(current_time_str)
        if parsed_datetime:
            enhanced_data["current_system_time-datetime"] = parsed_datetime
            enhanced_data["current_system_time-ISO8601"] = datetime_to_iso8601(parsed_datetime)
            logger.debug(f"Parsed current_system_time: {current_time_str} -> {parsed_datetime}")

    # Process system_uptime
    if "system_uptime" in enhanced_data:
        uptime_str = enhanced_data["system_uptime"]

        # Parse to timedelta object
        parsed_duration = parse_modem_duration(uptime_str)
        if parsed_duration:
            enhanced_data["system_uptime-datetime"] = parsed_duration
            enhanced_data["system_uptime-seconds"] = timedelta_to_seconds(parsed_duration)
            logger.debug(
                f"Parsed system_uptime: {uptime_str} -> {parsed_duration} ({parsed_duration.total_seconds()}s)"
            )

    return enhanced_data


# Export all public functions
__all__ = [
    "datetime_to_iso8601",
    "enhance_status_with_time_fields",
    "parse_modem_datetime",
    "parse_modem_duration",
    "timedelta_to_seconds",
]
