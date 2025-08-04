"""Tests for exception module coverage."""

import pytest

from arris_modem_status.exceptions import (
    ArrisConnectionError,
    ArrisHTTPError,
    ArrisModemError,
    wrap_connection_error,
)


@pytest.mark.unit
class TestExceptionsCoverage:
    """Test exception edge cases for coverage."""

    def test_arris_modem_error_str_with_details(self):
        """Test ArrisModemError string representation with details."""
        error = ArrisModemError("Test error", details={"key": "value", "number": 42})

        error_str = str(error)
        assert "Test error" in error_str
        assert "details:" in error_str
        assert "key" in error_str
        assert "value" in error_str

    def test_arris_http_error_without_status_code(self):
        """Test ArrisHTTPError without explicit status code."""
        error = ArrisHTTPError("HTTP error occurred")

        assert error.status_code is None
        assert error.details is not None
        assert "status_code" not in error.details

    def test_arris_http_error_with_status_code_no_details(self):
        """Test ArrisHTTPError with status code but no initial details."""
        error = ArrisHTTPError("HTTP error", status_code=500)

        assert error.status_code == 500
        assert error.details["status_code"] == 500

    def test_wrap_connection_error_generic(self):
        """Test wrapping generic connection error."""
        original = OSError("Network is unreachable")
        wrapped = wrap_connection_error(original, "192.168.1.1", 443)

        assert isinstance(wrapped, ArrisConnectionError)
        assert "192.168.1.1:443" in str(wrapped)
        assert wrapped.details["error_type"] == "OSError"
