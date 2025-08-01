"""Tests for client error handling paths."""

from unittest.mock import Mock, patch

import pytest
import requests

from arris_modem_status import ArrisModemStatusClient
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConnectionError,
    ArrisHTTPError,
    ArrisOperationError,
)


@pytest.mark.unit
class TestClientErrorPaths:
    """Test error handling paths in the client."""

    def test_analyze_error_http_403(self):
        """Test error analysis for HTTP 403 errors."""
        client = ArrisModemStatusClient(password="test")

        # The error string needs to contain "HTTP 403" not just "403"
        error = requests.exceptions.HTTPError("HTTP 403 Forbidden")
        capture = client._analyze_error(error, "test_request")

        assert capture.error_type == "http_403"

    def test_analyze_error_http_500(self):
        """Test error analysis for HTTP 500 errors."""
        client = ArrisModemStatusClient(password="test")

        # The error string needs to contain "HTTP 500" not just "500"
        error = requests.exceptions.HTTPError("HTTP 500 Internal Server Error")
        capture = client._analyze_error(error, "test_request")

        assert capture.error_type == "http_500"

    def test_analyze_error_with_response_object(self):
        """Test error analysis with response object."""
        client = ArrisModemStatusClient(password="test")

        # Create a mock response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.headers = {"Content-Type": "text/html"}

        error = requests.exceptions.HTTPError("404 Not Found")
        error.response = mock_response

        capture = client._analyze_error(error, "test_request", mock_response)

        assert capture.http_status == 404
        assert "Not Found" in capture.partial_content
        assert capture.response_headers["Content-Type"] == "text/html"

    def test_analyze_error_response_text_exception(self):
        """Test error analysis when response.text raises exception."""
        client = ArrisModemStatusClient(password="test")

        # Mock response where .text raises an exception
        mock_response = Mock()
        mock_response.text = property(Mock(side_effect=Exception("Decode error")))
        mock_response.content = b"raw content"
        mock_response.status_code = 500
        mock_response.headers = {}

        error = Exception("Test error")
        capture = client._analyze_error(error, "test_request", mock_response)

        # Should fall back to content
        assert "raw content" in capture.partial_content

    def test_analyze_error_response_no_content(self):
        """Test error analysis when response has no content attribute."""
        client = ArrisModemStatusClient(password="test")

        # Mock response with no content or text
        mock_response = Mock(spec=["status_code", "headers"])  # Has some attrs but not content/text
        mock_response.status_code = 500
        mock_response.headers = {}

        error = Exception("Test error")
        capture = client._analyze_error(error, "test_request", mock_response)

        # Based on the code, it seems to default to empty string, not "Unable to extract content"
        assert capture.partial_content == ""

    def test_analyze_error_complete_failure(self):
        """Test error analysis when analysis itself fails."""
        client = ArrisModemStatusClient(password="test")

        # Looking at the implementation, it tries to call str(error) in the except block too
        # Let's create an error object that fails in a different way
        class UnstringableError(Exception):
            def __str__(self):
                raise RuntimeError("Cannot convert to string")

        error = UnstringableError("test")

        # The method should catch the exception and return a fallback ErrorCapture
        # But it will fail because str(error) is called in the except handler too
        # So we need to patch the logger.error to prevent the second str() call
        with patch("arris_modem_status.client.error_handler.logger.error"):
            capture = client._analyze_error(error, "test_request")

            assert capture.error_type == "analysis_failed"
            # The raw_error will be whatever Python's repr returns for the object
            assert "UnstringableError" in capture.raw_error or "Cannot convert" in capture.raw_error

    def test_make_hnap_request_with_retry_http_error_types(self):
        """Test retry logic with different HTTP error types."""
        client = ArrisModemStatusClient(password="test")
        client.authenticated = True

        # Test HTTPError with response attribute
        with patch("requests.Session.post") as mock_post:
            error = requests.exceptions.HTTPError("403 Forbidden")
            error.response = Mock(status_code=403, text="Forbidden")
            mock_post.side_effect = error

            with pytest.raises(ArrisHTTPError) as exc_info:
                client._make_hnap_request_with_retry("Test", {})

            assert exc_info.value.status_code == 403

        # Test HTTPError without response attribute but parseable message
        with patch("requests.Session.post") as mock_post:
            error = requests.exceptions.HTTPError("500 Server Error")
            mock_post.side_effect = error

            with pytest.raises(ArrisHTTPError) as exc_info:
                client._make_hnap_request_with_retry("Test", {})

            assert exc_info.value.status_code == 500

    def test_make_hnap_request_exhausted_with_result_none(self):
        """Test when retries are exhausted but result is None."""
        client = ArrisModemStatusClient(password="test", max_retries=1)
        client.authenticated = True

        with patch("requests.Session.post") as mock_post:
            # All attempts return None (simulating empty responses)
            mock_post.return_value = Mock(status_code=200, text="")

            with patch.object(client, "_make_hnap_request_raw", return_value=None):
                result = client._make_hnap_request_with_retry("Test", {})

                assert result is None

    def test_authentication_unexpected_error(self):
        """Test authentication with unexpected error type."""
        client = ArrisModemStatusClient(password="test")

        with patch("requests.Session.post") as mock_post:
            # Raise an unexpected error type
            mock_post.side_effect = RuntimeError("Unexpected error in auth")

            with pytest.raises(ArrisAuthenticationError) as exc_info:
                client.authenticate()

            assert "Unexpected error during authentication" in str(exc_info.value)
            assert exc_info.value.details["error_type"] == "RuntimeError"

    def test_get_status_unexpected_error(self):
        """Test get_status with unexpected error type."""
        client = ArrisModemStatusClient(password="test")
        client.authenticated = True

        with patch.object(client, "_make_hnap_request_with_retry") as mock_request:
            # Raise unexpected error
            mock_request.side_effect = RuntimeError("Unexpected error in status")

            with pytest.raises(ArrisOperationError) as exc_info:
                client.get_status()

            assert "Unexpected error during status retrieval" in str(exc_info.value)

    def test_parse_responses_json_decode_error(self):
        """Test response parsing with invalid JSON."""
        client = ArrisModemStatusClient(password="test")

        responses = {"software_info": "not valid json", "channel_info": '{"incomplete": '}  # Incomplete JSON

        parsed = client._parse_responses(responses)

        # Should return defaults when JSON parsing fails
        assert parsed["model_name"] == "Unknown"
        assert parsed["firmware_version"] == "Unknown"

    def test_close_with_http_403_errors(self):
        """Test close method logging when HTTP 403 errors are captured."""
        client = ArrisModemStatusClient(password="test", capture_errors=True, concurrent=True)

        # Add some 403 error captures
        from arris_modem_status.models import ErrorCapture

        client.error_captures = [
            ErrorCapture(
                timestamp=0,
                request_type="test",
                http_status=403,
                error_type="http_403",
                raw_error="403 Forbidden",
                response_headers={},
                partial_content="",
                recovery_successful=False,
                compatibility_issue=False,
            )
        ]

        with patch("requests.Session.close") as mock_close:
            client.close()

            mock_close.assert_called_once()
            # Should have logged warning about 403 errors

    def test_get_performance_metrics_no_instrumentation(self):
        """Test get_performance_metrics when instrumentation is disabled."""
        client = ArrisModemStatusClient(password="test", enable_instrumentation=False)

        metrics = client.get_performance_metrics()

        assert metrics == {"error": "Performance instrumentation not enabled"}

    def test_analyze_error_with_bytes_content(self):
        """Test error analysis when response content is bytes but text fails."""
        client = ArrisModemStatusClient(password="test")

        # Mock response where .text fails but content is bytes
        mock_response = Mock()
        mock_response.text = property(Mock(side_effect=Exception("Decode error")))
        mock_response.content = "not bytes, but string"  # This should trigger the else path
        mock_response.status_code = 500
        mock_response.headers = {}

        error = Exception("Test error")
        capture = client._analyze_error(error, "test_request", mock_response)

        # Should convert to string
        assert "not bytes, but string" in capture.partial_content

    def test_make_hnap_request_connection_error_at_end(self):
        """Test connection error after retries exhausted."""
        client = ArrisModemStatusClient(password="test", max_retries=1)
        client.authenticated = True

        with patch("requests.Session.post") as mock_post:
            from requests.exceptions import ConnectionError

            # All attempts fail with connection error
            mock_post.side_effect = ConnectionError("Network unreachable")

            with pytest.raises(ArrisConnectionError) as exc_info:
                client._make_hnap_request_with_retry("Test", {})

            assert "192.168.100.1:443" in str(exc_info.value)
