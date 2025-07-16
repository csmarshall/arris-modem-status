"""Test HTTP compatibility layer."""

import pytest
from unittest.mock import Mock
from urllib3.exceptions import HeaderParsingError
import requests

try:
    from arris_modem_status import ArrisStatusClient
    from arris_modem_status.arris_status_client import (
        ArrisCompatibleHTTPAdapter,
        create_arris_compatible_session,
        PerformanceInstrumentation,
        ErrorCapture
    )
    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisStatusClient not available", allow_module_level=True)


class TestHTTPCompatibility:
    """Test HTTP compatibility layer and urllib3 parsing fixes."""

    def test_header_parsing_error_detection(self):
        """Test detection of HeaderParsingError as compatibility issue."""
        error = HeaderParsingError("3.500000 |Content-type: text/html")

        client = ArrisStatusClient(password="test", host="test",
                                   quick_check=False)

        is_compat_error = client._is_http_compatibility_error(error)
        assert is_compat_error is True

    def test_parsing_artifact_extraction(self):
        """Test extraction of parsing artifacts from error messages."""
        test_cases = [
            ("HeaderParsingError: 3.500000 |Content-type: text/html",
             ["3.500000"]),
            ("Error: 2.100000 |Accept: application/json", ["2.100000"]),
            ("No artifacts here", [])
        ]

        adapter = ArrisCompatibleHTTPAdapter()

        for error_message, expected_artifacts in test_cases:
            artifacts = adapter._extract_parsing_artifacts(error_message)
            assert artifacts == expected_artifacts

    def test_browser_compatible_session_creation(self):
        """Test creation of browser-compatible session."""
        instrumentation = PerformanceInstrumentation()
        session = create_arris_compatible_session(instrumentation)

        assert isinstance(session, requests.Session)
        assert session.verify is False
        assert "ArrisStatusClient" in session.headers["User-Agent"]
