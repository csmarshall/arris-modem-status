"""
HTTP Compatibility Layer for Arris Modem Status Client
=====================================================

This module provides HTTP compatibility handling for Arris modem responses
by using relaxed parsing by default, avoiding urllib3's strict standards.

Author: Charles Marshall
Version: 1.3.0
"""

import logging
import socket
import ssl
import time
import warnings

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
    "ignore",
    message=".*Failed to parse headers.*HeaderParsingError.*",
    category=UserWarning,
    module="urllib3",
)

# Reduce urllib3 logging noise for HTTP compatibility issues we handle
logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)

logger = logging.getLogger("arris-modem-status")


class ArrisCompatibleHTTPAdapter(HTTPAdapter):
    """
    Custom HTTPAdapter that uses relaxed HTTP parsing for Arris modems.

    This adapter bypasses urllib3's strict HTTP parsing and uses a browser-like
    tolerant parser that handles the non-standard but valid HTTP responses from
    Arris modems.

    Root cause: urllib3 is overly strict compared to browsers. Arris modems send
    valid HTTP that browsers handle fine, but urllib3 rejects with HeaderParsingError.

    Solution: Use relaxed parsing by default for all /HNAP1/ requests.
    """

    def __init__(self, instrumentation=None, *args, **kwargs):
        """Initialize the Arris-compatible HTTP adapter."""
        super().__init__(*args, **kwargs)
        self.instrumentation = instrumentation
        logger.debug("🔧 Initialized ArrisCompatibleHTTPAdapter with relaxed HTTP parsing")

    def send(
        self,
        request,
        stream=False,
        timeout=None,
        verify=None,
        cert=None,
        proxies=None,
    ):
        """
        Send HTTP request using relaxed parsing for HNAP endpoints.

        For /HNAP1/ endpoints, we skip urllib3's strict parsing and use our
        browser-compatible parser directly.
        """
        start_time = time.time() if self.instrumentation else None

        # Always use relaxed parsing for HNAP endpoints
        if "/HNAP1/" in request.url:
            logger.debug("🔧 Using relaxed HTTP parsing for HNAP endpoint")

            try:
                response = self._raw_socket_request(request, timeout, verify)

                # Record successful timing
                if self.instrumentation:
                    response_size = len(response.content) if hasattr(response, "content") else 0
                    self.instrumentation.record_timing(
                        "http_request_relaxed",
                        start_time,
                        success=True,
                        http_status=response.status_code,
                        response_size=response_size,
                    )

                return response

            except Exception as e:
                logger.error(f"❌ Relaxed parsing failed: {e}")

                # Record failed timing
                if self.instrumentation:
                    self.instrumentation.record_timing(
                        "http_request_relaxed",
                        start_time,
                        success=False,
                        error_type=str(type(e).__name__),
                    )

                raise

        # For non-HNAP endpoints, use standard urllib3 processing
        try:
            response = super().send(request, stream, timeout, verify, cert, proxies)

            if self.instrumentation:
                response_size = len(response.content) if hasattr(response, "content") else 0
                self.instrumentation.record_timing(
                    "http_request_standard",
                    start_time,
                    success=True,
                    http_status=response.status_code,
                    response_size=response_size,
                )

            return response

        except Exception as e:
            if self.instrumentation:
                self.instrumentation.record_timing(
                    "http_request_standard",
                    start_time,
                    success=False,
                    error_type=str(type(e).__name__),
                )
            raise

    def _raw_socket_request(self, request, timeout=None, verify=None) -> Response:
        """
        Make HTTP request using raw socket with browser-like tolerance.

        This method replicates what browsers do: parse HTTP more tolerantly
        than urllib3's strict standards.
        """
        logger.debug("🔌 Making request with browser-compatible HTTP parsing")

        # Parse URL components
        url_parts = request.url.split("://", 1)[1].split("/", 1)
        host_port = url_parts[0]
        path = "/" + (url_parts[1] if len(url_parts) > 1 else "")

        if ":" in host_port:
            host, port = host_port.split(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 443 if request.url.startswith("https") else 80

        # Create raw socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set timeout
        if timeout:
            if isinstance(timeout, tuple):
                sock.settimeout(timeout[0])  # Use connect timeout
            else:
                sock.settimeout(timeout)

        try:
            # SSL wrap for HTTPS BEFORE connecting
            if request.url.startswith("https"):
                context = ssl.create_default_context()
                if not verify:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=host)

            # Connect to server (now with SSL if HTTPS)
            sock.connect((host, port))

            # Build HTTP request
            http_request = self._build_raw_http_request(request, host, path)

            # Send request
            sock.send(http_request.encode("utf-8"))

            # Receive response with relaxed parsing
            raw_response = self._receive_response_tolerantly(sock)

            # Parse response with browser-like tolerance
            return self._parse_response_tolerantly(raw_response, request)

        finally:
            # Always close the socket
            sock.close()

    def _build_raw_http_request(self, request, host: str, path: str) -> str:
        """Build raw HTTP request string from requests.Request object."""
        lines = [f"{request.method} {path} HTTP/1.1"]
        lines.append(f"Host: {host}")

        # Add headers, but skip Content-Length as we'll calculate it ourselves
        for name, value in request.headers.items():
            if name.lower() != "content-length":  # Skip Content-Length
                lines.append(f"{name}: {value}")

        # Add body length if present
        if request.body:
            body_bytes = request.body.encode("utf-8") if isinstance(request.body, str) else request.body
            lines.append(f"Content-Length: {len(body_bytes)}")

        lines.append("")  # End headers

        # Add body if present
        if request.body:
            if isinstance(request.body, str):
                lines.append(request.body)
            else:
                try:
                    lines.append(request.body.decode("utf-8"))
                except UnicodeDecodeError:
                    # For binary data that can't be decoded, we shouldn't include it in the request
                    # This is a limitation of our text-based HTTP request building
                    logger.warning("Binary body data cannot be included in raw HTTP request")
                    lines.append("")  # Empty body

        return "\r\n".join(lines)

    def _receive_response_tolerantly(self, sock) -> bytes:
        """
        Receive HTTP response with browser-like tolerance.

        This method is more forgiving than urllib3's strict parsing and
        handles the same responses that work fine in browsers.
        """
        response_data = b""
        content_length = None
        headers_complete = False

        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break

                response_data += chunk

                # Check if headers are complete
                if not headers_complete and b"\r\n\r\n" in response_data:
                    headers_complete = True
                    header_end = response_data.find(b"\r\n\r\n") + 4
                    headers_part = response_data[:header_end]

                    # Extract content-length with tolerance for formatting variations
                    try:
                        headers_str = headers_part.decode("utf-8", errors="replace")
                        for line in headers_str.split("\r\n"):
                            # More tolerant header parsing than urllib3
                            if line.lower().startswith("content-length"):
                                # Handle various separators and whitespace
                                parts = line.split(":", 1)
                                if len(parts) == 2:
                                    content_length = int(parts[1].strip())
                                    break
                    except (ValueError, UnicodeDecodeError):
                        # If we can't parse content-length, continue reading until timeout
                        pass

                # Check if we have complete response
                if headers_complete and content_length is not None:
                    header_end = response_data.find(b"\r\n\r\n") + 4
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
            response_str = raw_response.decode("utf-8", errors="replace")

            # Split headers and body with tolerance
            if "\r\n\r\n" in response_str:
                headers_part, body_part = response_str.split("\r\n\r\n", 1)
            elif "\n\n" in response_str:
                # Handle non-standard line endings
                headers_part, body_part = response_str.split("\n\n", 1)
            else:
                headers_part = response_str
                body_part = ""

            # Parse status line with tolerance
            header_lines = headers_part.replace("\r\n", "\n").split("\n")
            status_line = header_lines[0] if header_lines else "HTTP/1.1 200 OK"

            # Extract status code with tolerance for variations
            status_code = 200  # Default
            if status_line.startswith("HTTP/"):
                try:
                    parts = status_line.split(" ")
                    if len(parts) >= 2:
                        status_code = int(parts[1])
                except (ValueError, IndexError):
                    logger.debug(f"🔍 Tolerant parsing: Using default status 200 for: {status_line}")

            # Parse headers with tolerance for formatting variations
            headers = {}
            for line in header_lines[1:]:
                if ":" in line:
                    # More tolerant header parsing
                    key, value = line.split(":", 1)
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
                response._content = body_part.encode("utf-8")
            else:
                response._content = b""

            # Mark as successful (anything that parses is considered success)
            response.reason = "OK"

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
            response.reason = "Internal Server Error"  # Add this line
            return response


def create_arris_compatible_session(instrumentation=None) -> requests.Session:
    """
    Create a requests Session optimized for Arris modem compatibility.

    This session uses relaxed HTTP parsing by default for HNAP endpoints,
    providing browser-like tolerance for non-standard but valid HTTP.

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
        respect_retry_after_header=False,
    )

    # Use the Arris-compatible adapter with relaxed parsing
    adapter = ArrisCompatibleHTTPAdapter(
        instrumentation=instrumentation,
        pool_connections=1,
        pool_maxsize=5,
        max_retries=retry_strategy,
        pool_block=False,
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Session configuration
    session.verify = False
    session.headers.update(
        {
            "User-Agent": "ArrisModemStatusClient/1.3.0-Compatible",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

    logger.debug("🔧 Created Arris-compatible session with relaxed HTTP parsing for HNAP endpoints")
    return session


# Export HTTP compatibility components
__all__ = ["ArrisCompatibleHTTPAdapter", "create_arris_compatible_session"]
