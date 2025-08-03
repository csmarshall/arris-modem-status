"""
Time Parsing Utilities for Arris Modem Status Client
===================================================

This module provides utilities for parsing time-related data from Arris modems
and converting them to Python datetime/timedelta objects and standardized formats.

Author: Charles Marshall
License: MIT
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Compiled regex patterns for duration parsing
DURATION_PATTERN_1 = re.compile(r"(\d+)\s+days?\s+(\d+):(\d+):(\d+)")  # "7 days 14:23:56"
DURATION_PATTERN_2 = re.compile(r"(\d+)\s+day\(s\)\s+(\d+)h:(\d+)m:(\d+)s")  # "27 day(s) 10h:12m:37s"


def parse_modem_datetime(date_str: str) -> Optional[datetime]:
    """
    Parse modem datetime string to Python datetime object.

    Expected format: "MM/DD/YYYY HH:MM:SS" (e.g., "07/30/2025 23:31:23")

    Args:
        date_str: Date/time string from modem

    Returns:
        datetime object or None if parsing fails
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

    Handles multiple formats:
    - "7 days 14:23:56"
    - "27 day(s) 10h:12m:37s"

    Args:
        duration_str: Duration string from modem

    Returns:
        timedelta object or None if parsing fails
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

    Args:
        dt: datetime object

    Returns:
        ISO8601 formatted string (e.g., "2025-07-30T23:31:23")
    """
    return dt.isoformat()


def timedelta_to_seconds(td: timedelta) -> float:
    """
    Convert timedelta to total seconds.

    Args:
        td: timedelta object

    Returns:
        Total seconds as float
    """
    return td.total_seconds()


def enhance_status_with_time_fields(status_data: dict) -> dict:
    """
    Enhance status data with parsed time fields.

    This function takes the parsed status data and adds additional time-related
    fields for any datetime or duration values found.

    Args:
        status_data: Dictionary with modem status data

    Returns:
        Enhanced dictionary with additional time fields
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
