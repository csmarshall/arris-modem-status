"""Core tests for ArrisModemStatusClient."""

import time
from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import ConnectionError
from urllib3.exceptions import HeaderParsingError

from arris_modem_status import ArrisModemStatusClient, ChannelInfo
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConnectionError,
    ArrisHTTPError,
    ArrisOperationError,
    ArrisParsingError,
    ArrisTimeoutError,
)
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
        assert client.concurrent is False  # Changed from True to False
        assert client.max_workers == 1  # Changed from 2 to 1 (since concurrent=False)
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
        assert client.max_workers == 1  # Changed to 1 since concurrent=False
        assert client.max_retries == 2
        assert client.base_backoff == 0.1
        assert client.concurrent is False  # Changed from True to False
        assert client.capture_errors is True

    def test_serial_mode_initialization(self):
        """Test client in serial mode."""
        client = ArrisModemStatusClient(password="test", concurrent=False)

        assert client.concurrent is False
        assert client.max_workers == 1

    def test_concurrent_mode_initialization(self):
        """Test client in concurrent mode."""
        client = ArrisModemStatusClient(password="test", concurrent=True)

        assert client.concurrent is True
        assert client.max_workers == 2  # Default when concurrent=True

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

            with pytest.raises(ArrisConnectionError) as exc_info:
                client.authenticate()

            assert "Connection failed" in str(exc_info.value)
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

            with pytest.raises(ArrisAuthenticationError) as exc_info:
                client.authenticate()

            assert "invalid credentials" in str(exc_info.value).lower()
            assert client.authenticated is False

    def test_authentication_json_parse_error(self):
        """Test authentication with invalid JSON response."""
        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, text="invalid json")

            client = ArrisModemStatusClient(password="test")

            with pytest.raises(ArrisParsingError) as exc_info:
                client.authenticate()

            assert "parse" in str(exc_info.value).lower()

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

    def test_make_hnap_request_is_challenge_request(self):
        """Test that challenge requests don't include HNAP_AUTH header."""
        client = ArrisModemStatusClient(password="test")

        challenge_request_body = {
            "Login": {
                "Action": "request",
                "Username": "admin",
                "LoginPassword": "",
                "Captcha": "",
                "PrivateLogin": "LoginPassword",
            }
        }

        with patch("requests.Session.post") as mock_post:
            mock_post.return_value = Mock(status_code=200, text='{"LoginResponse": {}}')

            client._make_hnap_request_raw("Login", challenge_request_body)

            # Check that HNAP_AUTH header was not included
            call_kwargs = mock_post.call_args[1]
            assert "HNAP_AUTH" not in call_kwargs["headers"]


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
                Mock(status_code=200, text='{"GetMultipleHNAPsResponse": {}}'),  # Added 4th request
            ]

            client = ArrisModemStatusClient(password="test")
            assert client.authenticated is False

            # Just call get_status() without assigning the result
            client.get_status()

            assert client.authenticated is True
            assert mock_post.call_count >= 4  # Changed from 3 to 4 (auth + 4 status requests)

    def test_get_status_authentication_failure(self):
        """Test status retrieval when authentication fails."""
        with patch("requests.Session.post") as mock_post:
            mock_post.side_effect = ConnectionError("Connection failed")

            client = ArrisModemStatusClient(password="test")

            with pytest.raises(ArrisConnectionError):
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
        with patch.object(requests.Session, "post") as mock_post:
            # Use a network error that will trigger retries and be captured
            from requests.exceptions import ConnectionError

            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text=mock_modem_responses["challenge_response"],
                ),
                Mock(status_code=200, text=mock_modem_responses["login_success"]),
                # First status request fails with network error, then succeeds
                ConnectionError("Network error"),
                Mock(
                    status_code=200,
                    text=mock_modem_responses["software_info"],  # software_info
                ),
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

            # Ensure error analyzer is passed to request handler
            client.request_handler.error_analyzer = client.error_analyzer

            status = client.get_status()

            assert "_error_analysis" in status
            error_analysis = status["_error_analysis"]
            # Should have captured the ConnectionError
            assert error_analysis["total_errors"] > 0

    def test_get_status_no_responses(self):
        """Test get_status when no responses are received."""
        with patch("requests.Session.post") as mock_post:
            # Mock authentication success
            mock_post.side_effect = [
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"Challenge": "test", "PublicKey": "test", "Cookie": "test"}}',
                ),
                Mock(
                    status_code=200,
                    text='{"LoginResponse": {"LoginResult": "SUCCESS"}}',
                ),
                # All status requests fail
                Mock(status_code=500, text="Server error"),
                Mock(status_code=500, text="Server error"),
                Mock(status_code=500, text="Server error"),
                Mock(status_code=500, text="Server error"),  # Added 4th failed request
            ]

            client = ArrisModemStatusClient(password="test")

            with pytest.raises(ArrisOperationError) as exc_info:
                client.get_status()

            assert "Failed to retrieve any status data" in str(exc_info.value)

    def test_get_status_partial_responses(self):
        """Test get_status with only some requests succeeding."""
        client = ArrisModemStatusClient(password="test")
        client.authenticated = True

        # Mock responses where only some succeed
        with patch.object(client.request_handler, "make_request_with_retry") as mock_request:
            # First request succeeds, others fail
            mock_request.side_effect = [
                '{"GetCustomerStatusSoftwareResponse": {"StatusSoftwareModelName": "S34"}}',
                None,  # This one fails
                None,  # This one fails
                '{"GetMultipleHNAPsResponse": {"GetCustomerStatusDownstreamChannelInfoResponse": {"CustomerConnDownstreamChannel": ""}}}',
            ]

            # Should still return partial data
            status = client.get_status()

            assert status["model_name"] == "S34"
            assert len(status["downstream_channels"]) == 0


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
        with patch.object(requests.Session, "post") as mock_post:
            from requests.exceptions import ConnectionError

            mock_post.side_effect = [
                ConnectionError("Network error"),
                Mock(status_code=200, text='{"success": true}'),
            ]

            client = ArrisModemStatusClient(password="test", max_retries=2, capture_errors=True)
            client.authenticated = True

            # Ensure error analyzer is connected
            client.request_handler.error_analyzer = client.error_analyzer

            result = client.request_handler.make_request_with_retry("Test", {"Test": {}})

            assert result is not None
            assert mock_post.call_count == 2
            # Error should have been captured
            assert len(client.error_captures) > 0

    def test_make_hnap_request_exhausted_retries(self):
        """Test HNAP request when all retries are exhausted."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import Timeout

            # Timeout should retry until exhausted
            mock_post.side_effect = [
                Timeout("Connection timeout"),
                Timeout("Connection timeout"),
                Timeout("Connection timeout"),
            ]

            client = ArrisModemStatusClient(password="test", max_retries=2)
            client.authenticated = True

            with pytest.raises(ArrisTimeoutError):
                client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert mock_post.call_count == 3  # Initial + 2 retries

    def test_make_hnap_request_http_error_no_retry(self):
        """Test that HTTP errors don't trigger retries."""
        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_post.return_value = mock_response

            client = ArrisModemStatusClient(password="test", max_retries=3)
            client.authenticated = True

            with pytest.raises(ArrisHTTPError) as exc_info:
                client._make_hnap_request_with_retry("Test", {"Test": {}})

            # Should only call once (no retries for HTTP errors)
            assert mock_post.call_count == 1
            assert exc_info.value.status_code == 403

    def test_make_hnap_request_raw_http_error_response_text(self):
        """Test _make_hnap_request_raw handling response with text."""
        client = ArrisModemStatusClient(password="test")
        client.authenticated = True

        # Mock response with status != 200
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Page not found"

        with patch("requests.Session.post", return_value=mock_response):
            with pytest.raises(ArrisHTTPError) as exc_info:
                client._make_hnap_request_raw("Test", {})

            assert exc_info.value.status_code == 404
            assert "Page not found" in exc_info.value.details["response_text"]

    def test_make_hnap_request_non_200_response(self):
        """Test handling of non-200 responses."""
        client = ArrisModemStatusClient(password="test")
        client.authenticated = True

        with patch.object(client.request_handler, "_make_raw_request") as mock_raw:
            # Return None to simulate empty response from raw request
            mock_raw.return_value = None

            result = client.request_handler.make_request_with_retry("Test", {})
            assert result is None


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

    def test_close_without_errors(self):
        """Test close method when no errors were captured."""
        with patch("requests.Session.close") as mock_close:
            client = ArrisModemStatusClient(password="test", capture_errors=False)
            client.close()

            mock_close.assert_called_once()

    def test_close_with_instrumentation(self):
        """Test close method with instrumentation enabled."""
        with patch("requests.Session.close") as mock_close:
            client = ArrisModemStatusClient(password="test", enable_instrumentation=True)

            # Add some metrics
            client.instrumentation.record_timing("test_op", 0, success=True)

            client.close()

            mock_close.assert_called_once()


@pytest.mark.unit
class TestArrisModemStatusClientExceptionIntegration:
    """Test integration of custom exceptions in client."""

    def test_timeout_error_conversion(self):
        """Test that timeout errors are properly converted."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import Timeout

            mock_post.side_effect = Timeout("Read timeout")

            client = ArrisModemStatusClient(password="test", max_retries=0)
            client.authenticated = True

            with pytest.raises(ArrisTimeoutError) as exc_info:
                client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert "timed out" in str(exc_info.value)
            assert exc_info.value.details["operation"] == "Test"

    def test_connection_error_conversion(self):
        """Test that connection errors are properly converted."""
        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import ConnectionError

            mock_post.side_effect = ConnectionError("Network unreachable")

            client = ArrisModemStatusClient(password="test", max_retries=0)
            client.authenticated = True

            with pytest.raises(ArrisConnectionError) as exc_info:
                client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert exc_info.value.details["host"] == "192.168.100.1"
            assert exc_info.value.details["port"] == 443

    def test_http_error_creation(self):
        """Test that HTTP errors are properly created."""
        with patch("requests.Session.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            mock_post.return_value = mock_response

            client = ArrisModemStatusClient(password="test")
            client.authenticated = True

            with pytest.raises(ArrisHTTPError) as exc_info:
                client._make_hnap_request_with_retry("Test", {"Test": {}})

            assert exc_info.value.status_code == 404
            assert "404" in str(exc_info.value)
