"""Additional tests for connectivity module coverage."""

from unittest.mock import patch

import pytest

from arris_modem_status.cli.connectivity import quick_connectivity_check


@pytest.mark.unit
@pytest.mark.cli
class TestConnectivityCoverage:
    """Test connectivity module edge cases for coverage."""

    def test_quick_connectivity_check_os_error(self):
        """Test connectivity check with generic OS error."""
        with patch("socket.create_connection") as mock_create:
            # Simulate a generic OS error (not timeout, gaierror, or ConnectionRefusedError)
            mock_create.side_effect = OSError("Network is down")

            is_reachable, error_msg = quick_connectivity_check("192.168.100.1", 443, 2.0)

            assert is_reachable is False
            assert "Network error" in error_msg
            assert "Network is down" in error_msg
