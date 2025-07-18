"""Enhanced tests for HTTP compatibility layer."""

import pytest
import socket
import ssl
from unittest.mock import Mock, patch, MagicMock
from urllib3.exceptions import HeaderParsingError
import requests

from arris_modem_status.http_compatibility import (
    ArrisCompatibleHTTPAdapter,
    create_arris_compatible_session
)
from arris_modem_status.instrumentation import PerformanceInstrumentation
from arris_modem_status.models import ErrorCapture


@pytest.mark.unit
@pytest.mark.http_compatibility
class TestArrisCompatibleHTTPAdapter:
    """Test ArrisCompatibleHTTPAdapter functionality."""

    def test_adapter_initialization(self):
        """Test adapter initialization."""
        instrumentation = PerformanceInstrumentation()
        adapter = ArrisCompatibleHTTPAdapter(instrumentation=instrumentation)

        assert adapter.instrumentation is instrumentation

    def test_adapter_initialization_without_instrumentation(self):
        """Test adapter initialization without instrumentation."""
        adapter = ArrisCompatibleHTTPAdapter()

        assert adapter.instrumentation is None

    def test_normal_request_success(self):
        """Test normal request without compatibility issues."""
        adapter = ArrisCompatibleHTTPAdapter()

        # Mock the parent send method to return a successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"

        with patch('requests.adapters.HTTPAdapter.send', return_value=mock_response):
            request = Mock()
            request.url = "https://192.168.100.1/test"
            request.headers = {}

            response = adapter.send(request)

            # Should return the mocked response as-is (normal case)
            assert response.status_code == 200
            assert response.content == b"test content"

    def test_header_parsing_error_recovery(self):
        """Test recovery from HeaderParsingError."""
        instrumentation = PerformanceInstrumentation()
        adapter = ArrisCompatibleHTTPAdapter(instrumentation=instrumentation)

        # Mock the parent send to raise HeaderParsingError
        with patch('requests.adapters.HTTPAdapter.send') as mock_parent_send:
            mock_parent_send.side_effect = HeaderParsingError("3.500000 |Content-type: text/html", b"unparsed_data")

            # Mock the fallback method to succeed
            with patch.object(adapter, '_raw_socket_fallback') as mock_fallback:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.content = b"fallback content"
                mock_fallback.return_value = mock_response

                request = Mock()
                request.url = "https://192.168.100.1/test"
                request.headers = {}

                response = adapter.send(request)

                # Should return the fallback response (recovery successful)
                assert response.status_code == 200
                assert response.content == b"fallback content"
                mock_fallback.assert_called_once()

    def test_extract_parsing_artifacts(self):
        """Test extraction of parsing artifacts from error messages."""
        adapter = ArrisCompatibleHTTPAdapter()

        test_cases = [
            ("HeaderParsingError: 3.500000 |Content-type: text/html", ["3.500000"]),
            ("Error: 2.100000 |Accept: application/json", ["2.100000"]),
            ("Multiple: 1.234567 |Header1 and 9.876543 |Header2", ["1.234567", "9.876543"]),
            ("No artifacts here", []),
            ("", [])
        ]

        for error_message, expected_artifacts in test_cases:
            artifacts = adapter._extract_parsing_artifacts(error_message)
            assert artifacts == expected_artifacts

    def test_build_raw_http_request(self):
        """Test building raw HTTP request string."""
        adapter = ArrisCompatibleHTTPAdapter()

        request = Mock()
        request.method = "POST"
        request.headers = {"Content-Type": "application/json", "Authorization": "Bearer token"}
        request.body = '{"test": "data"}'

        http_request = adapter._build_raw_http_request(request, "192.168.100.1", "/HNAP1/")

        assert "POST /HNAP1/ HTTP/1.1" in http_request
        assert "Host: 192.168.100.1" in http_request
        assert "Content-Type: application/json" in http_request
        assert "Authorization: Bearer token" in http_request
        assert "Content-Length: 16" in http_request
        assert '{"test": "data"}' in http_request

    def test_build_raw_http_request_no_body(self):
        """Test building raw HTTP request without body."""
        adapter = ArrisCompatibleHTTPAdapter()

        request = Mock()
        request.method = "GET"
        request.headers = {"User-Agent": "TestAgent"}
        request.body = None

        http_request = adapter._build_raw_http_request(request, "192.168.100.1", "/")

        assert "GET / HTTP/1.1" in http_request
        assert "Host: 192.168.100.1" in http_request
        assert "User-Agent: TestAgent" in http_request
        assert "Content-Length" not in http_request

    @patch('socket.socket')
    def test_raw_socket_fallback_https(self, mock_socket_class):
        """Test raw socket fallback for HTTPS."""
        adapter = ArrisCompatibleHTTPAdapter()

        # Mock socket and SSL context
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        mock_ssl_context = Mock()
        mock_wrapped_socket = Mock()
        mock_ssl_context.wrap_socket.return_value = mock_wrapped_socket

        with patch('ssl.create_default_context', return_value=mock_ssl_context):
            with patch.object(adapter, '_receive_response_tolerantly') as mock_receive:
                mock_receive.return_value = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>"

                with patch.object(adapter, '_parse_response_tolerantly') as mock_parse:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_parse.return_value = mock_response

                    request = Mock()
                    request.url = "https://192.168.100.1/test"
                    request.method = "GET"
                    request.headers = {}
                    request.body = None

                    response = adapter._raw_socket_fallback(request)

                    # Should return the parsed response
                    assert response.status_code == 200
                    mock_ssl_context.wrap_socket.assert_called_once()

    @patch('socket.socket')
    def test_raw_socket_fallback_http(self, mock_socket_class):
        """Test raw socket fallback for HTTP."""
        adapter = ArrisCompatibleHTTPAdapter()

        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket

        with patch.object(adapter, '_receive_response_tolerantly') as mock_receive:
            mock_receive.return_value = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<html></html>"

            with patch.object(adapter, '_parse_response_tolerantly') as mock_parse:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_parse.return_value = mock_response

                request = Mock()
                request.url = "http://192.168.100.1/test"
                request.method = "GET"
                request.headers = {}
                request.body = None

                response = adapter._raw_socket_fallback(request)

                # Should return the parsed response
                assert response.status_code == 200
                # Should not use SSL for HTTP
                mock_socket.connect.assert_called_with(('192.168.100.1', 80))

    def test_parse_response_tolerantly_standard(self):
        """Test tolerant response parsing with standard HTTP."""
        adapter = ArrisCompatibleHTTPAdapter()

        raw_response = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 26\r\n"
            b"\r\n"
            b'{"status": "success"}'
        )

        request = Mock()
        request.url = "https://192.168.100.1/test"

        response = adapter._parse_response_tolerantly(raw_response, request)

        # Should parse standard response correctly
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        assert b'{"status": "success"}' == response.content

    def test_parse_response_tolerantly_nonstandard(self):
        """Test tolerant response parsing with non-standard HTTP."""
        adapter = ArrisCompatibleHTTPAdapter()

        # Non-standard line endings and formatting
        raw_response = (
            b"HTTP/1.1 200 OK\n"
            b"Content-Type: text/html\n"
            b"Some-Weird-Header:value_without_space\n"
            b"\n"
            b"<html><body>content</body></html>"
        )

        request = Mock()
        request.url = "https://192.168.100.1/test"

        response = adapter._parse_response_tolerantly(raw_response, request)

        # Should handle non-standard formatting gracefully
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/html'
        assert b"<html><body>content</body></html>" == response.content

    def test_parse_response_tolerantly_malformed(self):
        """Test tolerant response parsing with malformed HTTP."""
        adapter = ArrisCompatibleHTTPAdapter()

        # Malformed response
        raw_response = b"Not really HTTP at all"

        request = Mock()
        request.url = "https://192.168.100.1/test"

        response = adapter._parse_response_tolerantly(raw_response, request)

        # The tolerant parser is designed to handle even malformed content gracefully
        # It defaults to 200 for anything it can process, with empty body for malformed content
        assert response.status_code == 200
        assert response.content == b''  # Malformed content results in empty body

    def test_receive_response_tolerantly_with_content_length(self):
        """Test tolerant response receiving with Content-Length."""
        adapter = ArrisCompatibleHTTPAdapter()

        mock_socket = Mock()
        # Simulate receiving response in chunks
        response_chunks = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Length: 11\r\n",
            b"\r\n",
            b"Hello World"
        ]
        mock_socket.recv.side_effect = response_chunks + [b""]  # End with empty to stop

        response_data = adapter._receive_response_tolerantly(mock_socket)

        expected = b"HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\nHello World"
        assert response_data == expected

    def test_receive_response_tolerantly_timeout(self):
        """Test tolerant response receiving with timeout."""
        adapter = ArrisCompatibleHTTPAdapter()

        mock_socket = Mock()
        mock_socket.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\n\r\n",
            socket.timeout("Timeout")
        ]

        response_data = adapter._receive_response_tolerantly(mock_socket)

        assert b"HTTP/1.1 200 OK\r\n\r\n" in response_data


@pytest.mark.unit
@pytest.mark.http_compatibility
class TestHttpCompatibilitySession:
    """Test HTTP compatibility session creation."""

    def test_create_arris_compatible_session(self):
        """Test creation of Arris-compatible session."""
        session = create_arris_compatible_session()

        assert isinstance(session, requests.Session)
        assert session.verify is False
        assert "ArrisModemStatusClient" in session.headers["User-Agent"]
        assert session.headers["Accept"] == "application/json"
        assert session.headers["Cache-Control"] == "no-cache"

    def test_create_arris_compatible_session_with_instrumentation(self):
        """Test session creation with instrumentation."""
        instrumentation = PerformanceInstrumentation()
        session = create_arris_compatible_session(instrumentation)

        assert isinstance(session, requests.Session)
        # Check that HTTPS adapter is ArrisCompatibleHTTPAdapter
        https_adapter = session.get_adapter("https://example.com")
        assert isinstance(https_adapter, ArrisCompatibleHTTPAdapter)
        assert https_adapter.instrumentation is instrumentation

    def test_session_retry_configuration(self):
        """Test session retry strategy configuration."""
        session = create_arris_compatible_session()

        # Get the adapter to check retry configuration
        adapter = session.get_adapter("https://example.com")

        # Should have conservative retry strategy
        assert hasattr(adapter, 'max_retries')

    def test_session_mounting(self):
        """Test that adapters are mounted correctly."""
        session = create_arris_compatible_session()

        # Check that both HTTP and HTTPS are using compatible adapters
        http_adapter = session.get_adapter("http://example.com")
        https_adapter = session.get_adapter("https://example.com")

        assert isinstance(http_adapter, ArrisCompatibleHTTPAdapter)
        assert isinstance(https_adapter, ArrisCompatibleHTTPAdapter)


@pytest.mark.integration
@pytest.mark.http_compatibility
class TestHttpCompatibilityIntegration:
    """Integration tests for HTTP compatibility."""

    def test_compatibility_issue_detection_and_recovery(self):
        """Test end-to-end compatibility issue detection and recovery."""
        from arris_modem_status import ArrisModemStatusClient
        import time

        client = ArrisModemStatusClient(password="test", capture_errors=True, max_retries=2)

        # Manually simulate an HTTP compatibility error capture
        mock_capture = ErrorCapture(
            timestamp=time.time(),
            request_type="Login",
            http_status=0,
            error_type="http_compatibility",
            raw_error="3.500000 |Content-type: text/html",
            response_headers={},
            partial_content="",
            recovery_successful=True,
            compatibility_issue=True
        )

        client.error_captures.append(mock_capture)

        # Test that error analysis works
        analysis = client.get_error_analysis()

        assert analysis['total_errors'] > 0
        assert analysis['http_compatibility_issues'] > 0

        # Check that the error was classified as compatibility issue
        compatibility_errors = [e for e in client.error_captures if e.compatibility_issue]
        assert len(compatibility_errors) > 0

    def test_multiple_compatibility_issues(self):
        """Test handling multiple compatibility issues."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test", capture_errors=True)

        # Manually add multiple error captures
        client.error_captures = [
            ErrorCapture(
                timestamp=1234567890,
                request_type="Login",
                http_status=0,
                error_type="http_compatibility",
                raw_error="3.500000 |Content-type: text/html",
                response_headers={},
                partial_content="",
                recovery_successful=True,
                compatibility_issue=True
            ),
            ErrorCapture(
                timestamp=1234567891,
                request_type="GetStatus",
                http_status=0,
                error_type="http_compatibility",
                raw_error="2.100000 |Accept: application/json",
                response_headers={},
                partial_content="",
                recovery_successful=True,
                compatibility_issue=True
            )
        ]

        analysis = client.get_error_analysis()

        assert analysis['total_errors'] == 2
        assert analysis['http_compatibility_issues'] == 2
        assert analysis['recovery_stats']['recovery_rate'] == 1.0
        assert len(analysis['parsing_artifacts']) == 2

    def test_compatibility_vs_genuine_errors(self):
        """Test distinction between compatibility issues and genuine errors."""
        from arris_modem_status import ArrisModemStatusClient

        client = ArrisModemStatusClient(password="test")

        # Test compatibility error detection
        header_error = HeaderParsingError("3.500000 |Content-type: text/html", b"unparsed_data")
        assert client._is_http_compatibility_error(header_error) is True

        # Test genuine error detection
        from requests.exceptions import ConnectionError, Timeout
        connection_error = ConnectionError("Network unreachable")
        assert client._is_http_compatibility_error(connection_error) is False

        timeout_error = Timeout("Request timeout")
        assert client._is_http_compatibility_error(timeout_error) is False
