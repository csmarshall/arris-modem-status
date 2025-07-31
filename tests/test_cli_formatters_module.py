"""Additional tests for formatters module coverage."""

from io import StringIO
from unittest.mock import patch

import pytest

from arris_modem_status.cli.formatters import print_summary_to_stderr


@pytest.mark.unit
@pytest.mark.cli
class TestFormattersCoverage:
    """Test formatters module edge cases for coverage."""

    def test_print_summary_with_downstream_frequency_known(self):
        """Test summary with known downstream frequency to trigger that section."""
        status = {
            "model_name": "S34",
            "internet_status": "Connected",
            "downstream_frequency": "549000000 Hz",  # Known value, not "Unknown"
            "downstream_comment": "Locked",
            "mac_address": "AA:BB:CC:DD:EE:FF",  # Known MAC
            "serial_number": "ABCD12345",
            "current_system_time": "2023-01-01 12:00:00",
            "downstream_channels": [],
            "upstream_channels": [],
        }

        with patch("sys.stderr", StringIO()) as mock_stderr:
            print_summary_to_stderr(status)

            output = mock_stderr.getvalue()
            # Should include downstream status section
            assert "Downstream Status:" in output
            assert "Frequency: 549000000 Hz" in output
            assert "Comment: Locked" in output
            # Should include system info section
            assert "System Information:" in output
            assert "MAC Address: AA:BB:CC:DD:EE:FF" in output
