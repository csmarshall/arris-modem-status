"""
Tests for time parsing functionality.

This module tests the time parsing utilities and their integration with
the Arris Modem Status Client.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from arris_modem_status.time_utils import (
    datetime_to_iso8601,
    enhance_status_with_time_fields,
    parse_modem_datetime,
    parse_modem_duration,
    timedelta_to_seconds,
)


@pytest.mark.unit
class TestDateTimeParsing:
    """Test datetime parsing functions."""

    def test_parse_modem_datetime_valid(self):
        """Test parsing valid datetime formats."""
        test_cases = [
            ("07/30/2025 23:31:23", datetime(2025, 7, 30, 23, 31, 23)),  # noqa: DTZ001
            ("01/01/2024 00:00:00", datetime(2024, 1, 1, 0, 0, 0)),  # noqa: DTZ001
            ("12/31/2023 12:30:45", datetime(2023, 12, 31, 12, 30, 45)),  # noqa: DTZ001
        ]

        for input_str, expected_dt in test_cases:
            result = parse_modem_datetime(input_str)
            assert result == expected_dt

    def test_parse_modem_datetime_invalid(self):
        """Test parsing invalid datetime formats."""
        invalid_cases = [
            "",
            "Unknown",
            None,
            "not a date",
            "2025-07-30 23:31:23",  # Wrong format
            "07/30/25 23:31:23",  # Wrong year format
            "13/30/2025 23:31:23",  # Invalid month
        ]

        for invalid_input in invalid_cases:
            result = parse_modem_datetime(invalid_input)
            assert result is None

    def test_parse_modem_datetime_with_whitespace(self):
        """Test parsing datetime with extra whitespace."""
        result = parse_modem_datetime("  07/30/2025 23:31:23  ")
        expected = datetime(2025, 7, 30, 23, 31, 23)  # noqa: DTZ001
        assert result == expected

    def test_datetime_to_iso8601(self):
        """Test datetime to ISO8601 conversion."""
        dt = datetime(2025, 7, 30, 23, 31, 23)  # noqa: DTZ001
        result = datetime_to_iso8601(dt)
        assert result == "2025-07-30T23:31:23"

    def test_datetime_to_iso8601_microseconds(self):
        """Test ISO8601 conversion with microseconds."""
        dt = datetime(2025, 7, 30, 23, 31, 23, 123456)  # noqa: DTZ001
        result = datetime_to_iso8601(dt)
        assert result == "2025-07-30T23:31:23.123456"


@pytest.mark.unit
class TestDurationParsing:
    """Test duration parsing functions."""

    def test_parse_modem_duration_format1(self):
        """Test parsing duration format: 'X days HH:MM:SS'."""
        test_cases = [
            ("7 days 14:23:56", timedelta(days=7, hours=14, minutes=23, seconds=56)),
            ("1 day 00:00:00", timedelta(days=1)),
            ("0 days 01:30:45", timedelta(hours=1, minutes=30, seconds=45)),
            ("365 days 23:59:59", timedelta(days=365, hours=23, minutes=59, seconds=59)),
        ]

        for input_str, expected_td in test_cases:
            result = parse_modem_duration(input_str)
            assert result == expected_td

    def test_parse_modem_duration_format2(self):
        """Test parsing duration format: 'X day(s) Xh:Xm:Xs'."""
        test_cases = [
            ("27 day(s) 10h:12m:37s", timedelta(days=27, hours=10, minutes=12, seconds=37)),
            ("1 day(s) 0h:0m:0s", timedelta(days=1)),
            ("100 day(s) 23h:59m:59s", timedelta(days=100, hours=23, minutes=59, seconds=59)),
        ]

        for input_str, expected_td in test_cases:
            result = parse_modem_duration(input_str)
            assert result == expected_td

    def test_parse_modem_duration_invalid(self):
        """Test parsing invalid duration formats."""
        invalid_cases = [
            "",
            "Unknown",
            None,
            "not a duration",
            "7 days",  # Incomplete
            "14:23:56",  # Missing days
            "invalid format",
        ]

        for invalid_input in invalid_cases:
            result = parse_modem_duration(invalid_input)
            assert result is None

    def test_parse_modem_duration_with_whitespace(self):
        """Test parsing duration with extra whitespace."""
        result = parse_modem_duration("  7 days 14:23:56  ")
        expected = timedelta(days=7, hours=14, minutes=23, seconds=56)
        assert result == expected

    def test_timedelta_to_seconds(self):
        """Test timedelta to seconds conversion."""
        test_cases = [
            (timedelta(days=1), 86400.0),
            (timedelta(hours=1), 3600.0),
            (timedelta(minutes=1), 60.0),
            (timedelta(seconds=1), 1.0),
            (timedelta(days=7, hours=14, minutes=23, seconds=56), 656636.0),
        ]

        for td, expected_seconds in test_cases:
            result = timedelta_to_seconds(td)
            assert result == expected_seconds


@pytest.mark.unit
class TestStatusEnhancement:
    """Test status enhancement with time fields."""

    def test_enhance_status_with_time_fields_complete(self):
        """Test enhancement with both datetime and duration fields."""
        input_status = {
            "model_name": "S34",
            "current_system_time": "07/30/2025 23:31:23",
            "system_uptime": "7 days 14:23:56",
            "other_field": "unchanged",
        }

        result = enhance_status_with_time_fields(input_status)

        # Original fields should be preserved
        assert result["model_name"] == "S34"
        assert result["current_system_time"] == "07/30/2025 23:31:23"
        assert result["system_uptime"] == "7 days 14:23:56"
        assert result["other_field"] == "unchanged"

        # New datetime fields should be added
        assert "current_system_time-datetime" in result
        assert "current_system_time-ISO8601" in result
        assert result["current_system_time-ISO8601"] == "2025-07-30T23:31:23"

        # New duration fields should be added
        assert "system_uptime-datetime" in result
        assert "system_uptime-seconds" in result
        assert result["system_uptime-seconds"] == 656636.0  # 7 days 14:23:56 in seconds

        # Check datetime object
        expected_dt = datetime(2025, 7, 30, 23, 31, 23)  # noqa: DTZ001
        assert result["current_system_time-datetime"] == expected_dt

        # Check timedelta object
        expected_td = timedelta(days=7, hours=14, minutes=23, seconds=56)
        assert result["system_uptime-datetime"] == expected_td

    def test_enhance_status_with_partial_time_fields(self):
        """Test enhancement with only some time fields present."""
        input_status = {
            "model_name": "S34",
            "current_system_time": "07/30/2025 23:31:23",
            # No system_uptime
        }

        result = enhance_status_with_time_fields(input_status)

        # Should add datetime fields
        assert "current_system_time-datetime" in result
        assert "current_system_time-ISO8601" in result

        # Should not add duration fields
        assert "system_uptime-datetime" not in result
        assert "system_uptime-seconds" not in result

    def test_enhance_status_with_invalid_time_fields(self):
        """Test enhancement with invalid time values."""
        input_status = {
            "model_name": "S34",
            "current_system_time": "invalid datetime",
            "system_uptime": "invalid duration",
        }

        result = enhance_status_with_time_fields(input_status)

        # Original fields should be preserved
        assert result["current_system_time"] == "invalid datetime"
        assert result["system_uptime"] == "invalid duration"

        # No new fields should be added for invalid data
        assert "current_system_time-datetime" not in result
        assert "current_system_time-ISO8601" not in result
        assert "system_uptime-datetime" not in result
        assert "system_uptime-seconds" not in result

    def test_enhance_status_with_unknown_values(self):
        """Test enhancement with 'Unknown' values."""
        input_status = {
            "model_name": "S34",
            "current_system_time": "Unknown",
            "system_uptime": "Unknown",
        }

        result = enhance_status_with_time_fields(input_status)

        # Should not add parsed fields for Unknown values
        assert "current_system_time-datetime" not in result
        assert "system_uptime-datetime" not in result

    def test_enhance_status_with_empty_input(self):
        """Test enhancement with empty status dictionary."""
        input_status = {}

        result = enhance_status_with_time_fields(input_status)

        # Should return empty dict with no additional fields
        assert result == {}


@pytest.mark.integration
class TestTimeParsingIntegration:
    """Test integration of time parsing with the main client."""

    def test_parser_integration(self):
        """Test that parser properly calls time enhancement."""
        from arris_modem_status.client.parser import HNAPResponseParser

        parser = HNAPResponseParser()

        # Mock responses that would contain time data
        mock_responses = {
            "software_info": '{"GetMultipleHNAPsResponse": {"GetCustomerStatusSoftwareResponse": {"StatusSoftwareModelName": "S34", "CustomerConnSystemUpTime": "7 days 14:23:56"}}}',
            "startup_connection": '{"GetMultipleHNAPsResponse": {"GetCustomerStatusConnectionInfoResponse": {"CustomerCurSystemTime": "07/30/2025 23:31:23"}}}',
        }

        result = parser.parse_responses(mock_responses)

        # Should have original fields
        assert result["system_uptime"] == "7 days 14:23:56"
        assert result["current_system_time"] == "07/30/2025 23:31:23"

        # Should have enhanced fields
        assert "system_uptime-datetime" in result
        assert "system_uptime-seconds" in result
        assert "current_system_time-datetime" in result
        assert "current_system_time-ISO8601" in result

        # Verify values
        assert result["system_uptime-seconds"] == 656636.0
        assert result["current_system_time-ISO8601"] == "2025-07-30T23:31:23"

    def test_cli_filtering(self):
        """Test that CLI formatter filters out datetime objects."""
        from arris_modem_status.cli.formatters import format_channel_data_for_display

        input_status = {
            "model_name": "S34",
            "current_system_time": "07/30/2025 23:31:23",
            "current_system_time-datetime": datetime(2025, 7, 30, 23, 31, 23),  # noqa: DTZ001
            "current_system_time-ISO8601": "2025-07-30T23:31:23",
            "system_uptime": "7 days 14:23:56",
            "system_uptime-datetime": timedelta(days=7, hours=14, minutes=23, seconds=56),
            "system_uptime-seconds": 656636.0,
            "downstream_channels": [],
            "upstream_channels": [],
        }

        result = format_channel_data_for_display(input_status)

        # Should keep original and formatted string/number fields
        assert "current_system_time" in result
        assert "current_system_time-ISO8601" in result
        assert "system_uptime" in result
        assert "system_uptime-seconds" in result

        # Should filter out Python objects
        assert "current_system_time-datetime" not in result
        assert "system_uptime-datetime" not in result


@pytest.mark.unit
class TestLogging:
    """Test logging behavior in time parsing."""

    @patch("arris_modem_status.time_utils.logger")
    def test_parse_datetime_logs_debug_on_success(self, mock_logger):
        """Test that successful parsing logs debug message."""
        # Test via enhance_status_with_time_fields which calls the logging
        status = {"current_system_time": "07/30/2025 23:31:23"}

        enhance_status_with_time_fields(status)

        # Should have logged debug message
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Parsed current_system_time" in call_args

    @patch("arris_modem_status.time_utils.logger")
    def test_parse_duration_logs_debug_on_success(self, mock_logger):
        """Test that successful duration parsing logs debug message."""
        status = {"system_uptime": "7 days 14:23:56"}

        enhance_status_with_time_fields(status)

        # Should have logged debug message
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Parsed system_uptime" in call_args

    @patch("arris_modem_status.time_utils.logger")
    def test_parse_invalid_datetime_logs_debug(self, mock_logger):
        """Test that failed parsing logs debug message."""
        result = parse_modem_datetime("invalid date")

        assert result is None
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Failed to parse datetime" in call_args

    @patch("arris_modem_status.time_utils.logger")
    def test_parse_invalid_duration_logs_debug(self, mock_logger):
        """Test that failed duration parsing logs debug message."""
        result = parse_modem_duration("invalid duration")

        assert result is None
        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Failed to parse duration" in call_args


@pytest.mark.performance
class TestTimeParsingPerformance:
    """Test performance characteristics of time parsing."""

    def test_parsing_performance(self):
        """Test that time parsing is reasonably fast."""
        import time

        # Test with a reasonable number of iterations
        iterations = 1000
        test_datetime = "07/30/2025 23:31:23"
        test_duration = "7 days 14:23:56"

        # Time datetime parsing
        start_time = time.time()
        for _ in range(iterations):
            parse_modem_datetime(test_datetime)
        datetime_duration = time.time() - start_time

        # Time duration parsing
        start_time = time.time()
        for _ in range(iterations):
            parse_modem_duration(test_duration)
        duration_duration = time.time() - start_time

        # Should be fast enough (arbitrary reasonable limits)
        assert datetime_duration < 1.0  # Less than 1 second for 1000 iterations
        assert duration_duration < 1.0  # Less than 1 second for 1000 iterations

    def test_enhance_status_performance(self):
        """Test that status enhancement doesn't significantly impact performance."""
        import time

        large_status = {
            "current_system_time": "07/30/2025 23:31:23",
            "system_uptime": "7 days 14:23:56",
            # Add many other fields to simulate real status
            **{f"field_{i}": f"value_{i}" for i in range(100)},
        }

        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            enhance_status_with_time_fields(large_status)
        total_time = time.time() - start_time

        # Should be very fast
        assert total_time < 0.5  # Less than 0.5 seconds for 100 enhancements
