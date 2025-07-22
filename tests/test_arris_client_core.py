"""Core tests for ArrisModemStatusClient."""

import time
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError
from urllib3.exceptions import HeaderParsingError

from arris_modem_status import ArrisModemStatusClient, ChannelInfo
from arris_modem_status.models import ErrorCapture


@pytest.mark.unit
class TestArrisModemStatusClientInitialization:
    """Test client initialization and configuration."""

    def test_default_initialization(self):
        """Test client with default parameters."""
        client = ArrisModemStatusClient(password="test")

        assert client.password == "test"
        assert client.username == "admin"
        assert client.host == "192.168.100.1"
        assert client.port == 443
        assert client.concurrent is True
        assert client.max_workers == 2
        assert client.max_retries == 3
        assert client.authenticated is False
        assert client.private_key is None
        assert client.uid_cookie is None

    def test_custom_initialization(self, client_kwargs):
        """Test client with custom parameters."""
        client = ArrisModemStatusClient(**client_kwargs)

        assert client.password == "test_password"
        assert client.host == "192.168.100.1"
        assert client.port == 443
        assert client.max_workers == 2
        assert client.max_retries == 2
        assert client.base_backoff == 0.1
        assert client.concurrent is True
        assert client.capture_errors is True

    def test_serial_mode_initialization(self):
        """Test client in serial mode."""
        client = ArrisModemStatusClient(password="test", concurrent=False)

        assert client.concurrent is False
        assert client.max_workers == 1

    def test_context_manager_protocol(self):
        """Test client as context manager."""
        with ArrisModemStatusClient(password="test") as client:
            assert isinstance(client, ArrisModemStatusClient)
            assert hasattr(client, "close")

    def test_base_url_construction(self):
        """Test base URL construction."""
        client = ArrisModemStatusClient(password="test", host="192.168.1.1", port=8443)

        assert client.base_url == "https://192.168.1.1:8443"


@pytest.mark.unit
class TestArrisModemStatusClientAuthentication:
    """Test authentication functionality."""

    def test_generate_hnap_auth_token_no_key(self):
        """Test HNAP auth token generation without private key."""
        client = ArrisModemStatusClient(password="test")

        token = client._generate_hnap_auth_token("Login", 1234567890123)

        assert " " in token
        parts = token.split(" ")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA256 hex length
        assert parts[1] == "1234567890123"

    def test_generate_hnap_auth_token_with_key(self):
        """Test HNAP auth token generation with private key."""
        client = ArrisModemStatusClient(password="test")
        client.private_key = "test_private_key"

        token = client._generate_hnap_auth_token("GetMultipleHNAPs", 1234567890123)

        assert " " in token
        parts = token.split(" ")
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA256 hex length
        assert parts[1] == "1234567890123"

    def test_successful_authentication(self, mock_successful_auth_flow):
        """Test successful authentication flow."""
        client = ArrisModemStatusClient(password="test")

        result = client.authenticate()

        assert result is True
        assert client.authenticated is True
        assert client.private_key is not None
        assert client.uid_cookie is not None
        assert mock_successful_auth_flow.call_count == 2

    def test_authentication_challenge_failure(self):
        """Test authentication failure at challenge stage."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectionError("Connection failed")

            client = ArrisModemStatusClient(password="test")
            result = client.authenticate()

            assert result is False
            assert client.authenticated is False

    def test_authentication_login_failure(self, mock_modem_responses):
        """Test authentication failure at login stage."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text=mock_modem_responses["challenge_response"],
                ),
                Mock(status_code=200, text=mock_modem_responses["login_failure"]),
            ]

            client = ArrisModemStatusClient(password="test")
            result = client.authenticate()

            assert result is False
            assert client.authenticated is False

    def test_authentication_json_parse_error(self):
        """Test authentication with invalid JSON response."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, text="invalid json")

            client = ArrisModemStatusClient(password="test")
            result = client.authenticate()

            assert result is False

    def test_authentication_with_instrumentation(self, mock_performance_instrumentation):
        """Test authentication with performance instrumentation."""
        mock_start, mock_record = mock_performance_instrumentation

        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"Challenge": "test", "PublicKey": "test", "Cookie": "test"}}',
                ),
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"LoginResult": "SUCCESS"}}',
                ),
            ]

            client = ArrisModemStatusClient(password="test", enable_instrumentation=True)
            result = client.authenticate()

            assert result is True
            assert mock_start.called
            assert mock_record.called


@pytest.mark.unit
class TestArrisModemStatusClientDataRetrieval:
    """Test data retrieval functionality."""

    def test_get_status_success(self, mock_successful_status_flow):
        """Test successful status retrieval."""
        client = ArrisModemStatusClient(password="test")

        status = client.get_status()

        assert isinstance(status, dict)
        assert "model_name" in status
        assert "internet_status" in status
        assert "downstream_channels" in status
        assert "upstream_channels" in status
        assert status["model_name"] == "S34"
        assert status["internet_status"] == "Connected"
        assert len(status["downstream_channels"]) == 3
        assert len(status["upstream_channels"]) == 3

    def test_get_status_channel_data_structure(self, mock_successful_status_flow):
        """Test channel data structure in status response."""
        client = ArrisModemStatusClient(password="test")

        status = client.get_status()

        # Test downstream channels
        downstream = status["downstream_channels"]
        assert len(downstream) > 0

        first_channel = downstream[0]
        assert isinstance(first_channel, ChannelInfo)
        assert first_channel.channel_id == "1"
        assert first_channel.lock_status == "Locked"
        assert first_channel.modulation == "256QAM"
        assert "Hz" in first_channel.frequency
        assert "dBmV" in first_channel.power
        assert "dB" in first_channel.snr

        # Test upstream channels
        upstream = status["upstream_channels"]
        assert len(upstream) > 0

        first_upstream = upstream[0]
        assert isinstance(first_upstream, ChannelInfo)
        assert first_upstream.channel_id == "1"
        assert first_upstream.lock_status == "Locked"

    def test_get_status_without_authentication(self):
        """Test status retrieval triggers authentication."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"Challenge": "test", "PublicKey": "test", "Cookie": "test"}}',
                ),
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"LoginResult": "SUCCESS"}}',
                ),
                Mock(status_code=200, text='{"GetMultipleHNAPsResponse": {}}'),
                Mock(status_code=200, text='{"GetMultipleHNAPsResponse": {}}'),
                Mock(status_code=200, text='{"GetMultipleHNAPsResponse": {}}'),
            ]

            client = ArrisModemStatusClient(password="test")
            assert client.authenticated is False

            # Call get_status() to trigger authentication
            status = client.get_status()

            assert client.authenticated is True
            assert mock_post.call_count >= 3  # At least auth + status requests

    def test_get_status_authentication_failure(self):
        """Test status retrieval when authentication fails."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectionError("Connection failed")

            client = ArrisModemStatusClient(password="test")

            with pytest.raises(RuntimeError, match="Authentication failed"):
                client.get_status()

    def test_get_status_concurrent_mode(self, mock_successful_status_flow):
        """Test status retrieval in concurrent mode."""
        client = ArrisModemStatusClient(password="test", concurrent=True, max_workers=3)

        status = client.get_status()

        assert status["_request_mode"] == "concurrent"
        assert "_performance" in status

    def test_get_status_serial_mode(self, mock_successful_status_flow):
        """Test status retrieval in serial mode."""
        client = ArrisModemStatusClient(password="test", concurrent=False)

        status = client.get_status()

        assert status["_request_mode"] == "serial"

    def test_get_status_with_error_capture(self, mock_modem_responses):
        """Test status retrieval with error capture enabled."""
        with patch("requests.Session.post") as mock_post:
            # Use a network error that will trigger retries
            from requests.exceptions import ConnectionError

            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text=mock_modem_responses["challenge_response"],
                ),
                Mock(status_code=200, text=mock_modem_responses["login_success"]),
                ConnectionError("Network error"),  # This will trigger retry
                Mock(
                    status_code=200,
                    text=mock_modem_responses["complete_status"],
                ),
                Mock(
                    status_code=200,
                    text=mock_modem_responses["complete_status"],
                ),
                Mock(
                    status_code=200,
                    text=mock_modem_responses["complete_status"],
                ),
            ]

            client = ArrisModemStatusClient(password="test", capture_errors=True)
            status = client.get_status()

            assert "_error_analysis" in status
            error_analysis = status["_error_analysis"]
            assert error_analysis["total_errors"] > 0


@pytest.mark.unit
class TestArrisModemStatusClientErrorHandling:
    """Test error handling and recovery."""

    def test_error_classification(self):
        """Test error classification for different error types."""
        client = ArrisModemStatusClient(password="test")

        # Test network error detection
        from requests.exceptions import ConnectionError, Timeout

        # Test connection error with "connection" in message
        connection_error = ConnectionError("Connection refused")
        capture = client._analyze_error(connection_error, "test_request")
        assert capture.error_type == "connection"

        # Test timeout error
        timeout_error = Timeout("Request timeout")
        capture = client._analyze_error(timeout_error, "test_request")
        assert capture.error_type == "timeout"

        # Test HeaderParsingError (will be "unknown" since we can't detect it from string)
        header_error = HeaderParsingError("3.500000 |Content-type: text/html", b"unparsed_data")
        capture = client._analyze_error(header_error, "test_request")
        # Can't detect from string representation
        assert capture.error_type == "unknown"

    def test_make_hnap_request_with_retry_success(self, mock_modem_responses):
        """Test HNAP request with retry on success."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                text=mock_modem_responses["challenge_response"],
            )

            client = ArrisModemStatusClient(password="test")
            client.authenticated = True

            result = client._make_hnap_request_with_retry("Login", {"Login": {"Action": "request"}})

            assert result is not None
            assert mock_post.call_count == 1

    def test_make_hnap_request_with_retry_network_error(self):
        """Test HNAP request retry with network errors."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import ConnectionError

            mock_post.side_effect = [
                ConnectionError("Network error"),
                Mock(status_code=200, text='{"success": true}'),
            ]

            client = ArrisModemStatusClient(password="test", max_retries=2, capture_errors=True)
            client.authenticated = True

            result = client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert result is not None
            assert mock_post.call_count == 2
            assert len(client.error_captures) > 0

    def test_make_hnap_request_exhausted_retries(self):
        """Test HNAP request when all retries are exhausted."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import Timeout

            mock_post.side_effect = Timeout("Connection timeout")

            client = ArrisModemStatusClient(password="test", max_retries=2)
            client.authenticated = True

            result = client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert result is None
            assert mock_post.call_count == 3  # Initial + 2 retries


@pytest.mark.unit
class TestArrisModemStatusClientUtilities:
    """Test utility methods."""

    def test_get_error_analysis_no_errors(self):
        """Test error analysis with no captured errors."""
        client = ArrisModemStatusClient(password="test")

        analysis = client.get_error_analysis()

        assert analysis["message"] == "No errors captured yet"

    def test_get_error_analysis_with_errors(self):
        """Test error analysis with captured errors."""
        client = ArrisModemStatusClient(password="test", capture_errors=True)

        # Manually add some error captures for testing
        client.error_captures = [
            ErrorCapture(
                timestamp=time.time(),
                request_type="test",
                http_status=500,
                error_type="http_compatibility",
                raw_error="3.500000 |Content-type",
                response_headers={},
                partial_content="",
                recovery_successful=True,
                compatibility_issue=True,
            )
        ]

        analysis = client.get_error_analysis()

        assert analysis["total_errors"] == 1
        assert analysis["http_compatibility_issues"] == 1
        assert analysis["recovery_stats"]["recovery_rate"] == 1.0

    def test_validate_parsing_success(self, mock_successful_status_flow):
        """Test parsing validation with successful status."""
        client = ArrisModemStatusClient(password="test")

        validation = client.validate_parsing()

        assert "parsing_validation" in validation
        assert "performance_metrics" in validation
        assert validation["parsing_validation"]["basic_info_parsed"] is True

    def test_validate_parsing_error(self):
        """Test parsing validation when get_status fails."""
        with patch.object(ArrisModemStatusClient, "get_status") as mock_get_status:
            mock_get_status.side_effect = Exception("Test error")

            client = ArrisModemStatusClient(password="test")
            validation = client.validate_parsing()

            assert "error" in validation

    def test_close_method(self):
        """Test client close method."""
        with patch("requests.Session.close") as mock_close:
            client = ArrisModemStatusClient(password="test", capture_errors=True)
            client.error_captures = [Mock()]  # Add some captures

            client.close()

            mock_close.assert_called_once()
