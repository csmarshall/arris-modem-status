"""Test connection handling."""

from unittest.mock import patch

import pytest
from requests.exceptions import ConnectionError, ConnectTimeout

from arris_modem_status.exceptions import ArrisConnectionError, ArrisTimeoutError

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

            client = ArrisModemStatusClient(password="test")

            # With the new exception handling, this should raise ArrisTimeoutError
            from arris_modem_status.exceptions import ArrisTimeoutError

            with pytest.raises(ArrisTimeoutError):
                client.authenticate()

    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectionError("Network unreachable")

            client = ArrisModemStatusClient(password="test")

            # With the new exception handling, this should raise ArrisTimeoutError
            from arris_modem_status.exceptions import ArrisTimeoutError

            with pytest.raises(ArrisTimeoutError):
                client.authenticate()
