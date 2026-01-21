"""
Unit tests for log parsing functionality.
"""

import json
import time

import pytest

from arris_modem_status.client.parser import HNAPResponseParser
from arris_modem_status.models import LogEntry


class TestLogParsing:
    """Test log parsing functionality."""

    def test_parse_logs_basic(self):
        """Test basic log parsing with valid data."""
        parser = HNAPResponseParser()

        # Sample log response with correct format: ID^DateTime^Empty^Severity^Message
        hnaps_response = "0^01/13/2026 14:23:45^^Warning^T3 timeout}-{1^01/13/2026 14:24:00^^Info^Connection restored"

        logs = parser._parse_logs(hnaps_response)

        assert len(logs) == 2
        assert isinstance(logs[0], LogEntry)
        assert logs[0].severity == "Warning"
        assert logs[0].message == "T3 timeout"
        assert logs[1].severity == "Info"
        assert logs[1].message == "Connection restored"

    def test_parse_logs_empty(self):
        """Test parsing with empty log data."""
        parser = HNAPResponseParser()

        hnaps_response = ""

        logs = parser._parse_logs(hnaps_response)
        assert logs == []

    def test_parse_logs_malformed_entry(self):
        """Test parsing with malformed entries."""
        parser = HNAPResponseParser()

        # Entry with insufficient fields (should be skipped)
        hnaps_response = "0^01/13/2026 14:23:45^^Warning}-{1^01/13/2026 14:24:00^^Info^Valid message"

        logs = parser._parse_logs(hnaps_response)

        # Should only parse the valid entry
        assert len(logs) == 1
        assert logs[0].severity == "Info"
        assert logs[0].message == "Valid message"

    def test_parse_logs_timestamp_conversion(self):
        """Test timestamp conversion to Unix format."""
        parser = HNAPResponseParser()

        hnaps_response = "0^01/13/2026 14:23:45^^Info^Test message"

        logs = parser._parse_logs(hnaps_response)

        assert len(logs) == 1
        log = logs[0]

        # Verify timestamp is Unix timestamp (integer)
        assert isinstance(log.timestamp, int)
        assert log.timestamp > 0

        # Verify timestamp_str is preserved
        assert log.timestamp_str == "01/13/2026 14:23:45"

    def test_log_entry_is_critical(self):
        """Test LogEntry.is_critical() method."""
        critical_log = LogEntry(
            timestamp=int(time.time()),
            severity="Critical",
            message="Test critical",
            timestamp_str="01/13/2026 14:23:45",
        )

        error_log = LogEntry(
            timestamp=int(time.time()), severity="Error", message="Test error", timestamp_str="01/13/2026 14:23:45"
        )

        warning_log = LogEntry(
            timestamp=int(time.time()), severity="Warning", message="Test warning", timestamp_str="01/13/2026 14:23:45"
        )

        assert critical_log.is_critical()
        assert error_log.is_critical()
        assert not warning_log.is_critical()

    def test_log_entry_is_warning_or_higher(self):
        """Test LogEntry.is_warning_or_higher() method."""
        critical_log = LogEntry(
            timestamp=int(time.time()), severity="Critical", message="Test", timestamp_str="01/13/2026 14:23:45"
        )

        warning_log = LogEntry(
            timestamp=int(time.time()), severity="Warning", message="Test", timestamp_str="01/13/2026 14:23:45"
        )

        info_log = LogEntry(
            timestamp=int(time.time()), severity="Info", message="Test", timestamp_str="01/13/2026 14:23:45"
        )

        assert critical_log.is_warning_or_higher()
        assert warning_log.is_warning_or_higher()
        assert not info_log.is_warning_or_higher()

    def test_log_entry_format_for_display(self):
        """Test LogEntry.format_for_display() method."""
        log = LogEntry(
            timestamp=int(time.time()), severity="Warning", message="Test message", timestamp_str="01/13/2026 14:23:45"
        )

        formatted = log.format_for_display()

        assert "[01/13/2026 14:23:45]" in formatted
        assert "Warning" in formatted
        assert "Test message" in formatted

    def test_parse_responses_includes_logs(self):
        """Test that parse_responses handles system_log response."""
        parser = HNAPResponseParser()

        responses = {
            "system_log": json.dumps(
                {
                    "GetCustomerStatusLogResponse": {
                        "CustomerStatusLogList": "0^01/13/2026 14:23:45^^Warning^T3 timeout}-{1^01/13/2026 14:24:00^^Info^Connection OK"
                    }
                }
            )
        }

        parsed_data = parser.parse_responses(responses)

        assert "log_entries" in parsed_data
        assert len(parsed_data["log_entries"]) == 2
        assert parsed_data["log_entries"][0].severity == "Warning"
        assert parsed_data["log_entries"][1].severity == "Info"

    def test_parse_responses_empty_logs(self):
        """Test that parse_responses handles missing log data gracefully."""
        parser = HNAPResponseParser()

        responses = {}

        parsed_data = parser.parse_responses(responses)

        # Should have empty list for log_entries
        assert "log_entries" in parsed_data
        assert parsed_data["log_entries"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
