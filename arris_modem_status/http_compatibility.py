"""
HTTP Compatibility Layer for Arris Modem Status Client
=====================================================

This module provides HTTP compatibility handling for urllib3 parsing strictness
issues with Arris modem responses.

Author: Charles Marshall
Version: 1.3.0
"""

import logging
import socket
import ssl
import time
import warnings
from typing import List, Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from requests.models import Response
from urllib3.exceptions import HeaderParsingError, InsecureRequestWarning
from urllib3.util.retry import Retry

# Configure HTTP compatibility warnings suppression
urllib3.disable_warnings(InsecureRequestWarning)
urllib3.disable_warnings(HeaderParsingError)

# Suppress specific HTTP compatibility warnings using warnings module
warnings.filterwarnings(
    'ignore',
    message='.*Failed to parse headers.*HeaderParsingError.*',
    category=UserWarning,
    module='urllib3'
)

# Reduce urllib3 logging noise for HTTP compatibility issues we handle
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

logger = logging.getLogger("arris-modem-status")


class HttpCompatibilityFilter(logging.Filter):
    """Filter to suppress urllib3 HeaderParsingError warnings that we handle intentionally."""

    def filter(self, record):
        # Suppress HeaderParsingError warnings since we handle them gracefully
        if record.name.startswith('urllib3'):
            message = record.getMessage()
            if any(phrase in message for phrase in [
                'Failed to parse headers',
                'HeaderParsingError',
                'FirstHeaderLineIsContinuationDefect'
            ]):
                return False  # Suppress these warnings
        return True  # Allow all other log messages


# Apply the filter immediately to prevent warnings during import
for logger_name in ['urllib3.connectionpool', 'urllib3', 'urllib3.util.retry']:
    logger_obj = logging.getLogger(logger_name)
    logger_obj.addFilter(HttpCompatibilityFilter())


class ArrisCompatibleHTTPAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter that handles Arris modem HTTP parsing compatibility.

    This adapter catches urllib3 HeaderParsingError exceptions and falls back
    to raw socket parsing for Arris modems that send valid but non-standard HTTP.

    Root cause: urllib3 is overly strict compared to browsers. Arris modems send
    valid HTTP that browsers handle fine, but urllib3 rejects with HeaderParsingError.

    Solution: Catch parsing errors and use raw socket fallback that mirrors
    browser tolerance for non-standard but valid HTTP formatting.
    """

    def __init__(self, instrumentation=None, *args, **kwargs):
        """Initialize the Arris-compatible HTTP adapter."""
        super().__init__(*args, **kwargs)
        self.instrumentation = instrumentation
        logger.debug("🔧 Initialized ArrisCompatibleHTTPAdapter for relaxed HTTP parsing")

    def send(self, request, stream=False, timeout=None, verify=None, cert=None, proxies=None):
        """
        Send HTTP request with fallback to raw parsing for HeaderParsingError.

        This method first attempts normal requests/urllib3 processing. If that
        fails with HeaderParsingError (urllib3 being too strict), it falls back
        to raw socket communication that mirrors browser tolerance.
        """
        start_time = time.time() if self.instrumentation else None

        try:
            # First attempt: Standard requests/urllib3 processing
            response = super().send(request, stream, timeout, verify, cert, proxies)

            # Record successful timing
            if self.instrumentation:
                response_size = len(response.content) if hasattr(response, 'content') else 0
                self.instrumentation.record_timing(
                    "http_request_standard",
                    start_time,
                    success=True,
                    http_status=response.status_code,
                    response_size=response_size
                )

            return response

        except HeaderParsingError as e:
            # HeaderParsingError indicates urllib3 is too strict for this response
            logger.debug(f"🔧 HTTP compatibility issue detected, using browser-compatible parsing")

            # Extract parsing artifacts for analysis
            parsing_artifacts = self._extract_parsing_artifacts(str(e))
            if parsing_artifacts:
                logger.debug(f"🔍 Parsing artifacts detected: {parsing_artifacts}")
                logger.debug("💡 These are urllib3 parsing strictness issues, not data corruption")

            # Fallback: Raw socket request with relaxed parsing
            try:
                fallback_start = time.time() if self.instrumentation else None
                response = self._raw_socket_fallback(request, timeout, verify)

                # Record fallback timing
                if self.instrumentation:
                    response_size = len(response.content) if hasattr(response, 'content') else 0
                    self.instrumentation.record_timing(
                        "http_request_compatibility_fallback",
                        fallback_start,
                        success=True,
                        http_status=response.status_code,
                        response_size=response_size,
                        retry_count=1
                    )

                return response

            except Exception as fallback_error:
                logger.error(f"❌ Browser-compatible parsing fallback failed: {fallback_error}")

                # Record failed fallback timing
                if self.instrumentation:
                    self.instrumentation.record_timing(
                        "http_request_compatibility_fallback",
                        fallback_start if 'fallback_start' in locals() else start_time,
                        success=False,
                        error_type=str(type(fallback_error).__name__),
                        retry_count=1
                    )

                # Re-raise original HeaderParsingError if fallback fails
                raise e

    def _extract_parsing_artifacts(self, error_message: str) -> List[str]:
        """
        Extract parsing artifacts from HeaderParsingError for analysis.

        These patterns were originally thought to be data injection but are
        actually urllib3 parsing artifacts from strict header validation.
        """
        import re
        # Look for the classic pattern: "3.500000 |Content-type"
        pattern = r'(\d+\.?\d*)\s*\|'
        return re.findall(pattern, error_message)

    def _raw_socket_fallback(self, request, timeout=None, verify=None) -> Response:
        """
        Raw socket fallback that mirrors browser HTTP tolerance.

        This method replicates what browsers do: parse HTTP more tolerantly
        than urllib3's strict standards. It handles the same responses that
        cause HeaderParsingError but work fine in browsers.
        """
        logger.debug("🔌 Using browser-compatible HTTP parsing fallback")

        # Parse URL components
        url_parts = request.url.split('://', 1)[1].split('/', 1)
        host_port = url_parts[0]
        path = '/' + (url_parts[1] if len(url_parts) > 1 else '')

        if ':' in host_port:
            host, port = host_port.split(':', 1)
            port = int(port)
        else:
            host = host_port
            port = 443 if request.url.startswith('https') else 80

        # Create raw socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set timeout
        if timeout:
            if isinstance(timeout, tuple):
                sock.settimeout(timeout[0])  # Use connect timeout
            else:
                sock.settimeout(timeout)

        try:
            # SSL wrap for HTTPS
            if request.url.startswith('https'):
                context = ssl.create_default_context()
                if not verify:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=host)

            # Connect to server
            sock.connect((host, port))

            # Build HTTP request
            http_request = self._build_raw_http_request(request, host, path)

            # Send request
            sock.send(http_request.encode('utf-8'))

            # Receive response with relaxed parsing
            raw_response = self._receive_response_tolerantly(sock)

            # Parse response with browser-like tolerance
            return self._parse_response_tolerantly(raw_response, request)

        finally:
            sock.close()

    def _build_raw_http_request(self, request, host: str, path: str) -> str:
        """Build raw HTTP request string from requests.Request object."""
        lines = [f"{request.method} {path} HTTP/1.1"]
        lines.append(f"Host: {host}")

        # Add headers
        for name, value in request.headers.items():
            lines.append(f"{name}: {value}")

        # Add body length if present
        if request.body:
            body_bytes = request.body.encode('utf-8') if isinstance(request.body, str) else request.body
            lines.append(f"Content-Length: {len(body_bytes)}")

        lines.append("")  # End headers

        # Add body if present
        if request.body:
            if isinstance(request.body, str):
                lines.append(request.body)
            else:
                lines.append(request.body.decode('utf-8'))

        return "\r\n".join(lines)

    def _receive_response_tolerantly(self, sock) -> bytes:
        """
        Receive HTTP response with browser-like tolerance.

        This method is more forgiving than urllib3's strict parsing and
        handles the same responses that work fine in browsers.
        """
        response_data = b''
        content_length = None
        headers_complete = False

        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break

                response_data += chunk

                # Check if headers are complete
                if not headers_complete and b'\r\n\r\n' in response_data:
                    headers_complete = True
                    header_end = response_data.find(b'\r\n\r\n') + 4
                    headers_part = response_data[:header_end]

                    # Extract content-length with tolerance for formatting variations
                    try:
                        headers_str = headers_part.decode('utf-8', errors='replace')
                        for line in headers_str.split('\r\n'):
                            # More tolerant header parsing than urllib3
                            if line.lower().startswith('content-length'):
                                # Handle various separators and whitespace
                                parts = line.split(':', 1)
                                if len(parts) == 2:
                                    content_length = int(parts[1].strip())
                                    break
                    except (ValueError, UnicodeDecodeError):
                        # If we can't parse content-length, continue reading until timeout
                        pass

                # Check if we have complete response
                if headers_complete and content_length is not None:
                    header_end = response_data.find(b'\r\n\r\n') + 4
                    body_received = len(response_data) - header_end
                    if body_received >= content_length:
                        break

            except socket.timeout:
                # Timeout reached, assume response is complete
                logger.debug("🕐 Socket timeout during response, assuming complete")
                break
            except Exception as e:
                logger.debug(f"🔍 Socket receive error: {e}")
                break

        logger.debug(f"📥 Raw response received: {len(response_data)} bytes")
        return response_data

    def _parse_response_tolerantly(self, raw_response: bytes, original_request) -> Response:
        """
        Parse raw HTTP response with browser-like tolerance.

        This parsing is more forgiving than urllib3 and handles the formatting
        variations that Arris modems use in their HTTP responses.
        """
        try:
            # Decode with error tolerance
            response_str = raw_response.decode('utf-8', errors='replace')

            # Split headers and body with tolerance
            if '\r\n\r\n' in response_str:
                headers_part, body_part = response_str.split('\r\n\r\n', 1)
            elif '\n\n' in response_str:
                # Handle non-standard line endings
                headers_part, body_part = response_str.split('\n\n', 1)
            else:
                headers_part = response_str
                body_part = ''

            # Parse status line with tolerance
            header_lines = headers_part.replace('\r\n', '\n').split('\n')
            status_line = header_lines[0] if header_lines else 'HTTP/1.1 200 OK'

            # Extract status code with tolerance for variations
            status_code = 200  # Default
            if status_line.startswith('HTTP/'):
                try:
                    parts = status_line.split(' ')
                    if len(parts) >= 2:
                        status_code = int(parts[1])
                except (ValueError, IndexError):
                    logger.debug(f"🔍 Tolerant parsing: Using default status 200 for: {status_line}")

            # Parse headers with tolerance for formatting variations
            headers = {}
            for line in header_lines[1:]:
                if ':' in line:
                    # More tolerant header parsing
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()

                    # Handle duplicate headers by taking the last value
                    headers[key] = value
                elif line.strip():
                    # Non-standard header line, log but continue
                    logger.debug(f"🔍 Tolerant parsing: Skipping non-standard header: {line}")

            # Create Response object
            response = Response()
            response.status_code = status_code
            response.headers.update(headers)
            response.url = original_request.url
            response.request = original_request

            # Set content with proper encoding handling
            if body_part:
                response._content = body_part.encode('utf-8')
            else:
                response._content = b''

            # Mark as successful (anything that parses is considered success)
            response.reason = 'OK'

            logger.debug(f"✅ Browser-compatible parsing successful: {status_code} ({len(body_part)} bytes)")
            return response

        except Exception as e:
            logger.error(f"❌ Browser-compatible parsing failed: {e}")
            # Create minimal error response
            response = Response()
            response.status_code = 500
            response._content = b'{"error": "Parsing failed with browser-compatible parser"}'
            response.url = original_request.url
            response.request = original_request
            return response


def create_arris_compatible_session(instrumentation=None) -> requests.Session:
    """
    Create a requests Session with Arris modem HTTP compatibility.

    This session uses the ArrisCompatibleHTTPAdapter that handles urllib3's
    strict HTTP parsing by falling back to browser-like tolerant parsing
    when HeaderParsingError occurs.

    Returns:
        requests.Session configured for Arris modem HTTP compatibility
    """
    session = requests.Session()

    # Conservative retry strategy
    retry_strategy = Retry(
        total=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST", "GET"],
        backoff_factor=0.3,
        respect_retry_after_header=False
    )

    # Use the Arris-compatible adapter with instrumentation
    adapter = ArrisCompatibleHTTPAdapter(
        instrumentation=instrumentation,
        pool_connections=1,
        pool_maxsize=5,
        max_retries=retry_strategy,
        pool_block=False
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Session configuration
    session.verify = False
    session.headers.update({
        "User-Agent": "ArrisModemStatusClient/1.3.0-Compatible",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    })

    logger.debug("🔧 Created Arris-compatible session with browser-like HTTP parsing")
    return session


# Export HTTP compatibility components
__all__ = ["ArrisCompatibleHTTPAdapter", "create_arris_compatible_session", "HttpCompatibilityFilter"]
