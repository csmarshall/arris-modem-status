"""
Test utilities and helpers.

Provides utility classes and functions for testing the Arris Modem Status
Client.
"""

import time
from contextlib import contextmanager
from unittest.mock import Mock, patch


class MockArrisModem:
    """Mock Arris modem for testing HTTP compatibility scenarios."""

    def __init__(self, port=8443):
        """Initialize mock modem."""
        self.port = port
        self.responses = {}
        self.compatibility_issues = False

    def set_response(self, endpoint, response):
        """Set mock response for endpoint."""
        self.responses[endpoint] = response

    def enable_compatibility_issues(self, enabled=True):
        """Enable HTTP compatibility issues in responses."""
        self.compatibility_issues = enabled

    def get_response(self, endpoint):
        """Get response with optional compatibility issues."""
        response = self.responses.get(endpoint, '{"error": "not found"}')

        if self.compatibility_issues:
            # Simulate urllib3 parsing strictness issues
            from urllib3.exceptions import HeaderParsingError

            raise HeaderParsingError("3.500000 |Content-type: text/html", b"unparsed_data")

        return response


@contextmanager
def mock_http_compatibility_error():
    """Context manager that simulates HTTP compatibility errors."""
    from urllib3.exceptions import HeaderParsingError

    with patch("requests.Session.post") as mock_post:
        mock_post.side_effect = HeaderParsingError("3.500000 |Content-type: text/html")
        yield mock_post


@contextmanager
def mock_network_timeout(timeout_duration=1.0):
    """Context manager that simulates network timeouts."""
    from requests.exceptions import ConnectTimeout

    def slow_response(*args, **kwargs):
        time.sleep(timeout_duration)
        raise ConnectTimeout("Connection timeout")

    with patch("requests.Session.post", side_effect=slow_response):
        yield


class TimingValidator:
    """Utility for validating operation timing."""

    def __init__(self, expected_duration, tolerance=0.1):
        """Initialize timing validator."""
        self.expected_duration = expected_duration
        self.tolerance = tolerance
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Enter context manager."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.end_time = time.time()
        self.actual_duration = self.end_time - self.start_time

    @property
    def duration(self):
        """Get actual duration."""
        return self.actual_duration

    def validate(self):
        """Validate timing is within expected range."""
        min_time = self.expected_duration - self.tolerance
        max_time = self.expected_duration + self.tolerance

        return min_time <= self.actual_duration <= max_time


def assert_valid_channel_data(channels, channel_type="downstream"):
    """Assert that channel data is valid."""
    assert isinstance(channels, list)
    assert len(channels) > 0

    for channel in channels:
        assert hasattr(channel, "channel_id")
        assert hasattr(channel, "frequency")
        assert hasattr(channel, "power")
        assert hasattr(channel, "lock_status")

        # Check formatting
        assert " Hz" in channel.frequency
        assert " dBmV" in channel.power

        if channel_type == "downstream":
            assert hasattr(channel, "snr")
            assert " dB" in channel.snr or channel.snr == "N/A"


def create_mock_status_response():
    """Create a complete mock status response."""
    return {
        "model_name": "S34",
        "firmware_version": "S34_01.50.001.R",
        "system_uptime": "7 days 14:23:56",
        "internet_status": "Connected",
        "connection_status": "Allowed",
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "serial_number": "ABCD12345678",
        "downstream_channels": [
            Mock(
                channel_id="1",
                frequency="549000000 Hz",
                power="0.6 dBmV",
                snr="39.0 dB",
                modulation="256QAM",
                lock_status="Locked",
                corrected_errors="15",
                uncorrected_errors="0",
                channel_type="downstream",
            )
        ],
        "upstream_channels": [
            Mock(
                channel_id="1",
                frequency="30600000 Hz",
                power="46.5 dBmV",
                snr="N/A",
                modulation="SC-QAM",
                lock_status="Locked",
                channel_type="upstream",
            )
        ],
        "channel_data_available": True,
        "_error_analysis": {
            "total_errors": 2,
            "http_compatibility_issues": 2,
            "recovery_rate": 1.0,
        },
    }
