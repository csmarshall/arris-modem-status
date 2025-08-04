"""Test connection handling."""

from unittest.mock import patch

import pytest
from requests.exceptions import ConnectionError, ConnectTimeout

try:
    from arris_modem_status import ArrisModemStatusClient

    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisModemStatusClient not available", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.connection
class TestConnectionHandling:
    """Test connection handling and basic functionality."""

    def test_basic_client_creation(self):
        """Test basic client creation."""
        client = ArrisModemStatusClient(password="test", host="192.168.100.1")
        assert client.host == "192.168.100.1"
        assert client.password == "test"

    def test_client_with_custom_host(self):
        """Test client creation with custom host."""
        client = ArrisModemStatusClient(password="test", host="192.168.1.1")
        assert client.host == "192.168.1.1"

    def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectTimeout("Connection timeout")

            client = ArrisModemStatusClient(password="test", max_retries=0)

            # ConnectTimeout is a timeout exception, so it should raise ArrisTimeoutError
            from arris_modem_status.exceptions import ArrisTimeoutError

            with pytest.raises(ArrisTimeoutError) as exc_info:
                client.authenticate()

            # Verify it's a timeout error
            assert "timed out" in str(exc_info.value)

    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unreachable")

            client = ArrisModemStatusClient(password="test", max_retries=0)

            # With the new exception handling, this should raise ArrisConnectionError
            from arris_modem_status.exceptions import ArrisConnectionError

            with pytest.raises(ArrisConnectionError) as exc_info:
                client.authenticate()

            # Verify it's a connection error - check for host:port in message
            assert "192.168.100.1:443" in str(exc_info.value)
