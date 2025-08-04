"""Tests for CLI edge cases and error paths."""

import argparse
from io import StringIO
from unittest.mock import Mock, patch

import pytest

from arris_modem_status.cli.args import validate_args
from arris_modem_status.cli.connectivity import print_connectivity_troubleshooting
from arris_modem_status.cli.formatters import format_channel_data_for_display, print_summary_to_stderr
from arris_modem_status.cli.logging_setup import setup_logging
from arris_modem_status.cli.main import main


@pytest.mark.unit
@pytest.mark.cli
class TestCLIEdgeCases:
    """Test edge cases in CLI modules."""

    def test_validate_args_negative_retries(self):
        """Test validation with negative retries value."""
        args = argparse.Namespace(timeout=30, workers=2, retries=-1, port=443, parallel=False)

        # Should raise error for negative retries
        from arris_modem_status.exceptions import ArrisConfigurationError

        with pytest.raises(ArrisConfigurationError) as exc_info:
            validate_args(args)

        assert "Retries cannot be negative" in str(exc_info.value)

    def test_connectivity_troubleshooting_dns_error(self):
        """Test troubleshooting output for DNS errors."""
        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_connectivity_troubleshooting(
                "invalid.hostname.local", 443, "DNS resolution failed for invalid.hostname.local"
            )

            output = mock_stderr.getvalue()
            assert "DNS resolution failed" in output
            assert "Use IP address instead" in output

    def test_connectivity_troubleshooting_generic_error(self):
        """Test troubleshooting output for generic network errors."""
        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_connectivity_troubleshooting("192.168.100.1", 443, "Some other network error")

            output = mock_stderr.getvalue()
            assert "Network connectivity issue" in output
            assert "ping 192.168.100.1" in output

    def test_logging_setup_with_file(self, tmp_path):
        """Test logging setup with file output."""
        log_file = tmp_path / "test.log"

        setup_logging(debug=True, log_file=str(log_file))

        # Log something
        import logging

        logger = logging.getLogger("test_logger")
        logger.info("Test message")

        # Check log file was created and contains message
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Test message" in log_content

    def test_formatters_with_error_analysis_http_403(self):
        """Test summary formatting with HTTP 403 errors in error analysis."""
        mock_channel = Mock()
        mock_channel.channel_id = "1"
        mock_channel.frequency = "549000000 Hz"
        mock_channel.power = "0.6 dBmV"
        mock_channel.snr = "39.0 dB"
        mock_channel.corrected_errors = "15"
        mock_channel.uncorrected_errors = "0"

        status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_channels": [mock_channel],
            "upstream_channels": [],
            "_error_analysis": {
                "total_errors": 5,
                "recovery_rate": 0.6,
                "http_compatibility_issues": 0,
                "error_types": {"http_403": 3, "timeout": 2},
            },
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            assert "HTTP 403 Errors: 3" in output
            assert "modem rejected concurrent requests" in output

    def test_formatters_with_no_channel_data(self):
        """Test formatting when channel data is completely missing."""
        status = {
            "model_name": "S34",
            "internet_status": "Connected",
            # No channel data at all
        }

        formatted = format_channel_data_for_display(status)

        # Should handle missing channel data gracefully
        assert "downstream_channels" not in formatted
        assert "upstream_channels" not in formatted

    def test_formatters_with_unknown_values(self):
        """Test summary formatting with all unknown values."""
        status = {
            # All values are "Unknown"
            "model_name": "Unknown",
            "firmware_version": "Unknown",
            "hardware_version": "Unknown",
            "system_uptime": "Unknown",
            "internet_status": "Unknown",
            "downstream_frequency": "Unknown",
            "mac_address": "Unknown",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            # Should still print summary even with unknown values
            assert "Model: Unknown" in output
            assert "Firmware: Unknown" in output
            # Should skip sections with unknown values
            assert "Downstream Status:" not in output  # Skipped because frequency is Unknown
            assert "System Information:" not in output  # Skipped because MAC is Unknown

    def test_main_unexpected_error_with_network_keywords(self):
        """Test main handling of unexpected errors that look like network issues."""
        MockClientClass = Mock()
        MockClientClass.side_effect = RuntimeError("Connection timeout while initializing")

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            # Should detect network-like error and show troubleshooting
            assert "TROUBLESHOOTING" in stderr_output

    def test_main_unexpected_error_non_network(self):
        """Test main handling of unexpected non-network errors."""
        MockClientClass = Mock()
        MockClientClass.side_effect = ValueError("Invalid configuration parameter")

        with patch("sys.argv", ["arris-modem-status", "--password", "test123"]):
            stderr_capture = StringIO()

            with patch("sys.stderr", stderr_capture):
                result = main(client_class=MockClientClass)

            assert result == 1
            stderr_output = stderr_capture.getvalue()
            # Should show error suggestions but not network troubleshooting
            assert "Troubleshooting suggestions:" in stderr_output
            assert "TROUBLESHOOTING" not in stderr_output  # Network-specific troubleshooting

    def test_connectivity_os_error(self):
        """Test connectivity check with OS error."""
        from arris_modem_status.cli.connectivity import quick_connectivity_check

        with patch("socket.create_connection") as mock_create:
            mock_create.side_effect = OSError("Generic network error")

            is_reachable, error_msg = quick_connectivity_check("192.168.100.1", 443)

            assert is_reachable is False
            assert "Network error" in error_msg

    def test_formatters_downstream_status_section(self):
        """Test that downstream status section is included when frequency is known."""
        from arris_modem_status.cli.formatters import print_summary_to_stderr

        status = {
            "model_name": "S34",
            "downstream_frequency": "549000000 Hz",
            "downstream_comment": "Locked",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            assert "Downstream Status:" in output
            assert "549000000 Hz" in output

    def test_formatters_system_info_section(self):
        """Test that system info section is included when MAC is known."""
        from arris_modem_status.cli.formatters import print_summary_to_stderr

        status = {
            "model_name": "S34",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "serial_number": "12345",
            "current_system_time": "2023-01-01",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            assert "System Information:" in output
            assert "AA:BB:CC:DD:EE:FF" in output

    def test_formatters_error_analysis_no_403(self):
        """Test error analysis formatting without HTTP 403 errors."""
        from arris_modem_status.cli.formatters import print_summary_to_stderr

        status = {
            "model_name": "S34",
            "downstream_channels": [],
            "upstream_channels": [],
            "_error_analysis": {
                "total_errors": 3,
                "recovery_rate": 0.66,
                "http_compatibility_issues": 1,
                "error_types": {"timeout": 2, "http_compatibility": 1},
            },
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            # Should show error analysis but not 403 warning
            assert "Error Analysis:" in output
            assert "HTTP 403" not in output
