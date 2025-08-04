"""Tests for HTTP compatibility coverage."""

from unittest.mock import Mock, patch

import pytest

from arris_modem_status.http_compatibility import ArrisCompatibleHTTPAdapter


@pytest.mark.unit
@pytest.mark.http_compatibility
class TestHTTPCompatibilityCoverage:
    """Test HTTP compatibility edge cases for coverage."""

    def test_adapter_send_none_url(self):
        """Test adapter send with None URL."""
        adapter = ArrisCompatibleHTTPAdapter()

        request = Mock()
        request.url = None
        request.headers = {}

        # Should use standard processing for None URL
        with patch("requests.adapters.HTTPAdapter.send") as mock_parent_send:
            mock_response = Mock()
            mock_parent_send.return_value = mock_response

            response = adapter.send(request)

            assert response == mock_response
            mock_parent_send.assert_called_once()

    def test_raw_socket_request_no_url(self):
        """Test raw socket request with missing URL."""
        adapter = ArrisCompatibleHTTPAdapter()

        request = Mock()
        request.url = None

        with pytest.raises(ValueError, match="Request URL is None"):
            adapter._raw_socket_request(request)

    def test_receive_response_tolerantly_unicode_decode_error(self):
        """Test receive response with unicode decode error in headers."""
        adapter = ArrisCompatibleHTTPAdapter()

        mock_socket = Mock()
        # Response with invalid UTF-8 in headers
        mock_socket.recv.side_effect = [
            b"HTTP/1.1 200 OK\r\n",
            b"Content-Length: \xff\xfe\r\n",  # Invalid UTF-8
            b"\r\n",
            b"body",
            b"",
        ]

        response_data = adapter._receive_response_tolerantly(mock_socket)

        # Should still receive response despite decode error
        assert b"HTTP/1.1 200 OK" in response_data

    def test_parse_response_tolerantly_empty_status_line(self):
        """Test parse response with empty status line."""
        adapter = ArrisCompatibleHTTPAdapter()

        raw_response = b"\r\nContent-Type: text/html\r\n\r\n<html></html>"
        request = Mock()
        request.url = "https://test.com"

        response = adapter._parse_response_tolerantly(raw_response, request)

        # Should use default status
        assert response.status_code == 200

    def test_parse_response_tolerantly_invalid_status_code(self):
        """Test parse response with invalid status code."""
        adapter = ArrisCompatibleHTTPAdapter()

        raw_response = b"HTTP/1.1 ABC OK\r\n\r\n"  # Non-numeric status
        request = Mock()
        request.url = "https://test.com"

        response = adapter._parse_response_tolerantly(raw_response, request)

        # Should default to 200
        assert response.status_code == 200

    def test_build_raw_http_request_skip_content_length(self):
        """Test that existing Content-Length headers are skipped."""
        adapter = ArrisCompatibleHTTPAdapter()

        request = Mock()
        request.method = "POST"
        request.headers = {"Content-Type": "application/json", "Content-Length": "999"}  # Should be recalculated
        request.body = '{"test": "data"}'

        http_request = adapter._build_raw_http_request(request, "test.com", "/api")

        # Should not have duplicate Content-Length
        assert http_request.count("Content-Length:") == 1
        assert "Content-Length: 16" in http_request  # Actual length
        assert "Content-Length: 999" not in http_request  # Original skipped
