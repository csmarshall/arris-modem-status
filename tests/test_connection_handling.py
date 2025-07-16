"""Test connection handling and quick checks."""

import pytest
import socket
from unittest.mock import Mock, patch
from requests.exceptions import ConnectTimeout, ConnectionError

try:
    from arris_modem_status import ArrisStatusClient
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisStatusClient not available", allow_module_level=True)


class TestConnectionHandling:
    """Test connection handling, quick checks, and fail-fast behavior."""

    def test_quick_connectivity_check_success(self):
        """Test quick connectivity check with reachable host."""
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.return_value = None  # Success

            client = ArrisStatusClient(
                password="test",
                host="192.168.100.1",
                quick_check=True,
                quick_timeout=2.0
            )

            # Should complete without exception
            assert client.host == "192.168.100.1"
            mock_sock.connect.assert_called_once()
            mock_sock.close.assert_called_once()

    def test_quick_connectivity_check_failure(self):
        """Test quick connectivity check with unreachable host."""
        with patch('socket.socket') as mock_socket:
            mock_sock = Mock()
            mock_socket.return_value = mock_sock
            mock_sock.connect.side_effect = socket.timeout("Timeout")

            with pytest.raises(ConnectionError):
                ArrisStatusClient(
                    password="test",
                    host="192.168.1.99",  # Unreachable IP
                    quick_check=True,
                    fail_fast=True,
                    quick_timeout=2.0
                )

    def test_quick_check_disabled(self):
        """Test that client works when quick check is disabled."""
        client = ArrisStatusClient(
            password="test",
            host="192.168.100.1",
            quick_check=False
        )

        assert client.host == "192.168.100.1"
