"""
Main Arris Modem Status Client
==============================

This module contains the main client implementation that orchestrates
all components for querying Arris cable modem status via HNAP.

"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional

from arris_modem_status.client.auth import HNAPAuthenticator
from arris_modem_status.client.error_handler import ErrorAnalyzer
from arris_modem_status.client.http import HNAPRequestHandler
from arris_modem_status.client.parser import HNAPResponseParser
from arris_modem_status.exceptions import (
    ArrisAuthenticationError,
    ArrisConnectionError,
    ArrisHTTPError,
    ArrisOperationError,
    ArrisParsingError,
    ArrisTimeoutError,
)
from arris_modem_status.http_compatibility import create_arris_compatible_session
from arris_modem_status.instrumentation import PerformanceInstrumentation

logger = logging.getLogger("arris-modem-status")


class ArrisModemStatusClient:
    """
    Enhanced Arris modem client with HTTP compatibility and performance instrumentation.

    This client provides high-performance access to Arris cable modem status
    with built-in relaxed HTTP parsing for compatibility with Arris modems'
    non-standard but valid HTTP responses.

    The client operates in two modes:

    * **Serial Mode (default)**: Requests are made sequentially for maximum reliability.
      Slower (~2s) but handles modems with buggy concurrent request handling.

    * **Concurrent Mode**: Multiple requests in parallel for speed (~1.2s) but may
      fail with HTTP 403 errors on modems with firmware issues.

    Features:
        * Browser-compatible HTTP parsing by default for HNAP endpoints
        * Smart retry logic for genuine network errors
        * Comprehensive error analysis and recovery
        * Detailed performance instrumentation and timing
        * Connection pooling optimization
        * Complete HNAP request coverage including GetCustomerStatusSoftware

    Args:
        password: Modem admin password (required)
        username: Login username (default: "admin")
        host: Modem IP address (default: "192.168.100.1")
        port: HTTPS port (default: 443)
        concurrent: Enable concurrent requests (default: False)
            WARNING: Many Arris modems have issues with concurrent HNAP requests
        max_workers: Concurrent request workers when concurrent=True (default: 2)
        max_retries: Max retry attempts for failed requests (default: 3)
        base_backoff: Base backoff time in seconds (default: 0.5)
        capture_errors: Whether to capture error details for analysis (default: True)
        timeout: (connect_timeout, read_timeout) in seconds (default: (3, 12))
        enable_instrumentation: Enable detailed performance instrumentation (default: True)

    Examples:
        Basic usage with context manager (recommended):

        >>> with ArrisModemStatusClient(password="your_password") as client:
        ...     status = client.get_status()
        ...     print(f"Internet: {status['internet_status']}")

        Performance monitoring:

        >>> client = ArrisModemStatusClient(
        ...     password="your_password",
        ...     enable_instrumentation=True
        ... )
        >>> with client:
        ...     status = client.get_status()
        ...     metrics = client.get_performance_metrics()
        ...     print(f"Total time: {metrics['session_metrics']['total_session_time']:.2f}s")

        Custom configuration:

        >>> client = ArrisModemStatusClient(
        ...     password="your_password",
        ...     host="192.168.1.1",
        ...     concurrent=True,
        ...     max_workers=3,
        ...     timeout=(5, 15)
        ... )

    Note:
        This is an unofficial library not affiliated with ARRIS® or CommScope.

    Warning:
        Concurrent mode may cause HTTP 403 errors and inconsistent data on many
        Arris modems due to firmware limitations. Use serial mode for reliability.
    """

    def __init__(
        self,
        password: str,
        username: str = "admin",
        host: str = "192.168.100.1",
        port: int = 443,
        concurrent: bool = False,
        max_workers: int = 2,
        max_retries: int = 3,
        base_backoff: float = 0.5,
        capture_errors: bool = True,
        timeout: tuple = (3, 12),
        enable_instrumentation: bool = True,
    ):
        """
        Initialize the Arris modem client with HTTP compatibility and instrumentation.

        Args:
            password: Modem admin password
            username: Login username (default: "admin")
            host: Modem IP address (default: "192.168.100.1")
            port: HTTPS port (default: 443)
            concurrent: Enable concurrent requests (default: False)
                WARNING: Many Arris modems have issues with concurrent HNAP requests
            max_workers: Concurrent request workers when concurrent=True (default: 2)
            max_retries: Max retry attempts for failed requests (default: 3)
            base_backoff: Base backoff time in seconds (default: 0.5)
            capture_errors: Whether to capture error details for analysis (default: True)
            timeout: (connect_timeout, read_timeout) in seconds (default: (3, 12))
            enable_instrumentation: Enable detailed performance instrumentation (default: True)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"
        self.concurrent = concurrent
        self.max_workers = max_workers if concurrent else 1
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.capture_errors = capture_errors
        self.timeout = timeout
        self.enable_instrumentation = enable_instrumentation

        # Initialize components
        self.authenticator = HNAPAuthenticator(username, password)
        self.error_analyzer = ErrorAnalyzer(capture_errors)
        self.parser = HNAPResponseParser()
        self.instrumentation = PerformanceInstrumentation() if enable_instrumentation else None

        # Configure HTTP session with relaxed parsing for HNAP endpoints
        self.session = create_arris_compatible_session(self.instrumentation)

        # Initialize request handler
        self.request_handler = HNAPRequestHandler(
            self.session,
            self.base_url,
            max_retries,
            base_backoff,
            timeout,
            self.instrumentation,
        )

        mode_str = "concurrent" if concurrent else "serial"
        logger.info(f"🛡️ ArrisModemStatusClient v1.0.0 initialized for {host}:{port}")
        logger.info(f"🔧 Mode: {mode_str}, Workers: {self.max_workers}, Retries: {max_retries}")
        logger.info("🔧 Using relaxed HTTP parsing for HNAP endpoints")
        if not concurrent:
            logger.info("📌 Using serial mode for maximum compatibility (recommended)")
        else:
            logger.warning("⚠️  Using concurrent mode - may cause HTTP 403 errors on some modems")
        if enable_instrumentation:
            logger.info("📊 Performance instrumentation enabled")

    @property
    def authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.authenticator.authenticated

    @authenticated.setter
    def authenticated(self, value: bool) -> None:
        """Set authentication status."""
        self.authenticator.authenticated = value

    @property
    def private_key(self) -> Optional[str]:
        """Get private key from authenticator."""
        return self.authenticator.private_key

    @private_key.setter
    def private_key(self, value: Optional[str]) -> None:
        """Set private key."""
        self.authenticator.private_key = value

    @property
    def uid_cookie(self) -> Optional[str]:
        """Get UID cookie from authenticator."""
        return self.authenticator.uid_cookie

    @uid_cookie.setter
    def uid_cookie(self, value: Optional[str]) -> None:
        """Set UID cookie."""
        self.authenticator.uid_cookie = value

    @property
    def error_captures(self) -> list:
        """Get error captures from analyzer."""
        return self.error_analyzer.error_captures

    @error_captures.setter
    def error_captures(self, value: list) -> None:
        """Get error captures from analyzer."""
        self.error_analyzer.error_captures = value

    def authenticate(self) -> bool:
        """
        Perform HNAP authentication with relaxed HTTP parsing.

        Returns:
            True if authentication successful, False otherwise

        Raises:
            ArrisAuthenticationError: When authentication fails
            ArrisConnectionError: When connection to modem fails
            ArrisTimeoutError: When timeout occurs during authentication
        """
        try:
            logger.info("🔐 Starting authentication...")
            start_time = (
                self.instrumentation.start_timer("authentication_complete") if self.instrumentation else time.time()
            )

            # Step 1: Request challenge
            challenge_start = (
                self.instrumentation.start_timer("authentication_challenge") if self.instrumentation else time.time()
            )

            challenge_request = self.authenticator.build_challenge_request()
            challenge_response = self.request_handler.make_request_with_retry("Login", challenge_request)

            if not challenge_response:
                logger.error("Failed to get authentication challenge after retries")

                if self.instrumentation:
                    self.instrumentation.record_timing(
                        "authentication_complete",
                        start_time,
                        success=False,
                        error_type="challenge_failed",
                    )

                raise ArrisAuthenticationError(
                    "Failed to get authentication challenge", details={"phase": "challenge", "username": self.username}
                )

            if self.instrumentation:
                self.instrumentation.record_timing("authentication_challenge", challenge_start, success=True)

            # Parse challenge response
            challenge, public_key, uid_cookie = self.authenticator.parse_challenge_response(challenge_response)
            self.authenticator.uid_cookie = uid_cookie

            # Step 2: Compute private key and login password
            key_computation_start = (
                self.instrumentation.start_timer("authentication_key_computation")
                if self.instrumentation
                else time.time()
            )

            login_password = self.authenticator.compute_credentials(challenge, public_key)

            if self.instrumentation:
                self.instrumentation.record_timing(
                    "authentication_key_computation",
                    key_computation_start,
                    success=True,
                )

            # Step 3: Send login request
            login_start = (
                self.instrumentation.start_timer("authentication_login") if self.instrumentation else time.time()
            )

            login_request = self.authenticator.build_login_request(login_password)
            login_headers = {"Cookie": f"uid={self.authenticator.uid_cookie}"} if self.authenticator.uid_cookie else {}

            login_response = self.request_handler.make_request_with_retry("Login", login_request, login_headers)

            if login_response and self.authenticator.validate_login_response(login_response):
                auth_time = time.time() - start_time
                mode_str = "concurrent" if self.concurrent else "serial"
                logger.info(f"🎉 Authentication successful ({mode_str} mode)! ({auth_time:.2f}s)")

                if self.instrumentation:
                    self.instrumentation.record_timing("authentication_login", login_start, success=True)
                    self.instrumentation.record_timing("authentication_complete", start_time, success=True)

                return True

            logger.error("Authentication failed after retries")

            if self.instrumentation:
                self.instrumentation.record_timing(
                    "authentication_login",
                    login_start,
                    success=False,
                    error_type="login_failed",
                )
                self.instrumentation.record_timing(
                    "authentication_complete",
                    start_time,
                    success=False,
                    error_type="login_failed",
                )

            raise ArrisAuthenticationError(
                "Authentication failed - invalid credentials or modem response",
                details={
                    "phase": "login",
                    "username": self.username,
                    "response": login_response[:200] if login_response else "None",
                },
            )

        except (
            ArrisAuthenticationError,
            ArrisConnectionError,
            ArrisTimeoutError,
            ArrisHTTPError,
            ArrisParsingError,
        ) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            logger.error(f"Authentication error: {e}")

            if self.instrumentation:
                self.instrumentation.record_timing(
                    "authentication_complete",
                    start_time,
                    success=False,
                    error_type=str(type(e).__name__),
                )

            # Wrap unexpected errors
            raise ArrisAuthenticationError(
                f"Unexpected error during authentication: {e!s}",
                details={"error_type": type(e).__name__, "error": str(e)},
            ) from e

    def get_status(self) -> dict[str, Any]:
        """
        Retrieve comprehensive modem status using relaxed HTTP parsing.

        Returns:
            Dictionary containing modem status information

        Raises:
            ArrisAuthenticationError: When authentication is required but fails
            ArrisOperationError: When status retrieval fails
            ArrisConnectionError: When connection to modem fails
            ArrisTimeoutError: When timeout occurs during status retrieval
        """
        start_time = self.instrumentation.start_timer("get_status_complete") if self.instrumentation else time.time()

        try:
            if not self.authenticated:
                if not self.authenticate():
                    raise ArrisAuthenticationError("Authentication required but failed")

            mode_str = "concurrent" if self.concurrent else "serial"
            logger.info(f"📊 Retrieving modem status with {mode_str} processing...")

            # Define the requests
            request_definitions = [
                (
                    "software_info",
                    {"GetMultipleHNAPs": {"GetCustomerStatusSoftware": ""}},
                ),
                (
                    "startup_connection",
                    {
                        "GetMultipleHNAPs": {
                            "GetCustomerStatusStartupSequence": "",
                            "GetCustomerStatusConnectionInfo": "",
                        }
                    },
                ),
                (
                    "internet_register",
                    {
                        "GetMultipleHNAPs": {
                            "GetInternetConnectionStatus": "",
                            "GetArrisRegisterInfo": "",
                            "GetArrisRegisterStatus": "",
                        }
                    },
                ),
                (
                    "channel_info",
                    {
                        "GetMultipleHNAPs": {
                            "GetCustomerStatusDownstreamChannelInfo": "",
                            "GetCustomerStatusUpstreamChannelInfo": "",
                        }
                    },
                ),
            ]

            responses: dict[str, str] = {}
            successful_requests = 0

            if self.concurrent:
                responses, successful_requests = self._process_concurrent_requests(request_definitions)
            else:
                responses, successful_requests = self._process_serial_requests(request_definitions)

            # Check if we got any responses
            if not responses:
                raise ArrisOperationError(
                    "Failed to retrieve any status data from modem",
                    details={
                        "requests_attempted": len(request_definitions),
                        "successful_requests": successful_requests,
                        "mode": mode_str,
                    },
                )

            # Parse responses
            parsing_start = (
                self.instrumentation.start_timer("response_parsing") if self.instrumentation else time.time()
            )
            parsed_data = self.parser.parse_responses(responses)
            if self.instrumentation:
                self.instrumentation.record_timing("response_parsing", parsing_start, success=True)

            # Add metadata
            parsed_data = self._add_metadata(parsed_data, successful_requests, len(request_definitions), start_time)

            total_time = time.time() - start_time
            downstream_count = len(parsed_data.get("downstream_channels", []))
            upstream_count = len(parsed_data.get("upstream_channels", []))
            channel_count = downstream_count + upstream_count

            logger.info(f"✅ Status retrieved! {channel_count} channels in {total_time:.2f}s ({mode_str} mode)")
            logger.info(f"📊 Success rate: {successful_requests}/{len(request_definitions)} requests")

            if self.instrumentation:
                self.instrumentation.record_timing("get_status_complete", start_time, success=True)

            return parsed_data

        except (
            ArrisAuthenticationError,
            ArrisConnectionError,
            ArrisTimeoutError,
            ArrisHTTPError,
            ArrisParsingError,
        ) as e:
            # Re-raise our custom exceptions
            raise e
        except Exception as e:
            logger.error(f"Status retrieval failed: {e}")

            if self.instrumentation:
                self.instrumentation.record_timing(
                    "get_status_complete",
                    start_time,
                    success=False,
                    error_type=str(type(e).__name__),
                )

            # Wrap unexpected errors
            raise ArrisOperationError(
                f"Unexpected error during status retrieval: {e!s}",
                details={"error_type": type(e).__name__, "error": str(e)},
            ) from e

    def _process_concurrent_requests(self, request_definitions: list) -> tuple[dict, int]:
        """Process requests concurrently."""
        logger.debug("🚀 Using concurrent request processing with relaxed HTTP parsing")
        logger.warning("⚠️  Concurrent mode may cause HTTP 403 errors on some modems")

        concurrent_start = (
            self.instrumentation.start_timer("concurrent_request_processing") if self.instrumentation else time.time()
        )

        responses: dict[str, str] = {}
        successful_requests = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_name = {
                executor.submit(
                    self._make_authenticated_request,
                    "GetMultipleHNAPs",
                    req_body,
                ): req_name
                for req_name, req_body in request_definitions
            }

            for future in as_completed(future_to_name, timeout=30):
                req_name = future_to_name[future]
                try:
                    response = future.result()
                    if response:
                        responses[req_name] = response
                        successful_requests += 1
                        logger.debug(f"✅ {req_name} completed successfully")
                    else:
                        logger.warning(f"⚠️ {req_name} failed after retries")
                except Exception as e:
                    logger.error(f"❌ {req_name} failed with exception: {e}")
                    # Analyze the error
                    self.error_analyzer.analyze_error(e, req_name)

        if self.instrumentation:
            self.instrumentation.record_timing(
                "concurrent_request_processing",
                concurrent_start,
                success=True,
            )

        return responses, successful_requests

    def _process_serial_requests(self, request_definitions: list) -> tuple[dict, int]:
        """Process requests serially."""
        logger.debug("🔄 Using serial request processing with relaxed HTTP parsing (recommended)")

        serial_start = (
            self.instrumentation.start_timer("serial_request_processing") if self.instrumentation else time.time()
        )

        responses: dict[str, str] = {}
        successful_requests = 0

        for req_name, req_body in request_definitions:
            try:
                logger.debug(f"📤 Processing {req_name} serially...")
                response = self._make_authenticated_request("GetMultipleHNAPs", req_body)
                if response:
                    responses[req_name] = response
                    successful_requests += 1
                    logger.debug(f"✅ {req_name} completed successfully")
                else:
                    logger.warning(f"⚠️ {req_name} failed after retries")

                # Small delay between serial requests to avoid overwhelming the modem
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ {req_name} failed with exception: {e}")
                # Analyze the error
                self.error_analyzer.analyze_error(e, req_name)

        if self.instrumentation:
            self.instrumentation.record_timing("serial_request_processing", serial_start, success=True)

        return responses, successful_requests

    def _make_authenticated_request(self, soap_action: str, request_body: dict) -> Optional[str]:
        """Make authenticated HNAP request."""
        auth_token = self.authenticator.generate_auth_token(soap_action)

        return self.request_handler.make_request_with_retry(
            soap_action,
            request_body,
            auth_token=auth_token,
            authenticated=self.authenticated,
            uid_cookie=self.uid_cookie,
            private_key=self.private_key,
        )

    def _add_metadata(
        self, parsed_data: dict, successful_requests: int, total_requests: int, start_time: float
    ) -> dict:
        """Add metadata to parsed data."""
        # Enhanced error analysis - always add when capture_errors is enabled
        if self.capture_errors:
            if self.error_captures:
                error_analysis = self.error_analyzer.get_error_analysis()

                # Simplify for main status output
                parsed_data["_error_analysis"] = {
                    "total_errors": error_analysis["total_errors"],
                    "http_compatibility_issues": error_analysis["http_compatibility_issues"],
                    "other_errors": error_analysis["total_errors"] - error_analysis["http_compatibility_issues"],
                    "recovery_rate": error_analysis["recovery_stats"]["recovery_rate"],
                    "current_mode": ("concurrent" if self.concurrent else "serial"),
                    "error_types": error_analysis["error_types"],
                }

                logger.info(
                    f"🔍 Error analysis: {error_analysis['total_errors']} errors, "
                    f"{error_analysis['recovery_stats']['total_recoveries']} recovered"
                )
            else:
                # Add empty error analysis when no errors captured
                parsed_data["_error_analysis"] = {
                    "total_errors": 0,
                    "http_compatibility_issues": 0,
                    "other_errors": 0,
                    "recovery_rate": 0.0,
                    "current_mode": ("concurrent" if self.concurrent else "serial"),
                    "error_types": {},
                }

        # Add mode and performance information
        parsed_data["_request_mode"] = "concurrent" if self.concurrent else "serial"
        parsed_data["_performance"] = {
            "total_time": time.time() - start_time,
            "requests_successful": successful_requests,
            "requests_total": total_requests,
            "mode": "concurrent" if self.concurrent else "serial",
        }

        # Add instrumentation data if enabled
        if self.instrumentation:
            performance_summary = self.instrumentation.get_performance_summary()
            parsed_data["_instrumentation"] = performance_summary

        return parsed_data

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get detailed performance metrics from instrumentation."""
        if not self.instrumentation:
            return {"error": "Performance instrumentation not enabled"}

        return self.instrumentation.get_performance_summary()

    def get_error_analysis(self) -> dict[str, Any]:
        """Get comprehensive error analysis."""
        return self.error_analyzer.get_error_analysis()

    def validate_parsing(self) -> dict[str, Any]:
        """Validate data parsing and return comprehensive quality metrics."""
        try:
            status = self.get_status()

            downstream_count = len(status.get("downstream_channels", []))
            upstream_count = len(status.get("upstream_channels", []))
            total_channels = downstream_count + upstream_count

            completeness_factors = [
                status.get("model_name", "Unknown") != "Unknown",
                status.get("internet_status", "Unknown") != "Unknown",
                status.get("mac_address", "Unknown") != "Unknown",
                status.get("firmware_version", "Unknown") != "Unknown",
                status.get("system_uptime", "Unknown") != "Unknown",
                downstream_count > 0,
                upstream_count > 0,
            ]
            completeness_score = (sum(completeness_factors) / len(completeness_factors)) * 100

            # Enhanced validation
            channel_quality = {}
            if downstream_count > 0:
                downstream_locked = sum(1 for ch in status["downstream_channels"] if "Locked" in ch.lock_status)
                downstream_modulations = {
                    ch.modulation for ch in status["downstream_channels"] if ch.modulation != "Unknown"
                }

                channel_quality["downstream_validation"] = {
                    "total_channels": downstream_count,
                    "locked_channels": downstream_locked,
                    "all_locked": downstream_locked == downstream_count,
                    "modulation_types": list(downstream_modulations),
                }

            if upstream_count > 0:
                upstream_locked = sum(1 for ch in status["upstream_channels"] if "Locked" in ch.lock_status)
                upstream_modulations = {
                    ch.modulation for ch in status["upstream_channels"] if ch.modulation != "Unknown"
                }

                channel_quality["upstream_validation"] = {
                    "total_channels": upstream_count,
                    "locked_channels": upstream_locked,
                    "all_locked": upstream_locked == upstream_count,
                    "modulation_types": list(upstream_modulations),
                }

            # MAC address validation
            mac_valid = False
            if status.get("mac_address") and status["mac_address"] != "Unknown":
                import re

                mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
                mac_valid = bool(re.match(mac_pattern, status["mac_address"]))

            # Frequency format validation
            freq_formats = {}
            if downstream_count > 0:
                sample_channel = status["downstream_channels"][0]
                freq_formats["downstream_frequency"] = "Hz" in sample_channel.frequency
                freq_formats["downstream_power"] = "dBmV" in sample_channel.power
                freq_formats["downstream_snr"] = "dB" in sample_channel.snr

            return {
                "parsing_validation": {
                    "basic_info_parsed": status.get("model_name", "Unknown") != "Unknown",
                    "internet_status_parsed": status.get("internet_status", "Unknown") != "Unknown",
                    "firmware_version_parsed": status.get("firmware_version", "Unknown") != "Unknown",
                    "system_uptime_parsed": status.get("system_uptime", "Unknown") != "Unknown",
                    "downstream_channels_found": downstream_count,
                    "upstream_channels_found": upstream_count,
                    "mac_address_format": mac_valid,
                    "frequency_formats": freq_formats,
                    "channel_data_quality": channel_quality,
                },
                "performance_metrics": {
                    "data_completeness_score": completeness_score,
                    "total_channels": total_channels,
                    "parsing_errors": len([e for e in self.error_captures if "parsing" in e.error_type.lower()]),
                    "http_compatibility_issues": len([e for e in self.error_captures if e.compatibility_issue]),
                    "request_mode": ("concurrent" if self.concurrent else "serial"),
                },
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e)}

    def close(self) -> None:
        """Clean up resources."""
        if self.capture_errors and self.error_captures:
            mode_str = "concurrent" if self.concurrent else "serial"
            compatibility_issues = len([e for e in self.error_captures if e.compatibility_issue])
            total_errors = len(self.error_captures)
            http_403_errors = len([e for e in self.error_captures if e.error_type == "http_403"])

            logger.info(f"📊 Session captured {total_errors} errors for analysis ({mode_str} mode)")
            if compatibility_issues > 0:
                logger.debug(
                    f"🔧 HTTP compatibility issues: {compatibility_issues} (should be rare with relaxed parsing)"
                )
            if http_403_errors > 0:
                logger.warning(f"⚠️  HTTP 403 errors: {http_403_errors} (modem rejected requests - use serial mode)")

        if self.instrumentation:
            performance_summary = self.instrumentation.get_performance_summary()
            session_time = performance_summary.get("session_metrics", {}).get("total_session_time", 0)
            total_ops = performance_summary.get("session_metrics", {}).get("total_operations", 0)
            logger.info(f"📊 Session performance: {total_ops} operations in {session_time:.2f}s")

        if self.session is not None:
            self.session.close()

    def __enter__(self) -> "ArrisModemStatusClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # Parameters are required by context manager protocol but unused
        _ = (exc_type, exc_val, exc_tb)  # Mark as intentionally unused
        self.close()

    # Legacy method names for compatibility
    def _generate_hnap_auth_token(self, soap_action: str, timestamp: Optional[int] = None) -> str:
        """Legacy method - redirects to authenticator."""
        return self.authenticator.generate_auth_token(soap_action, timestamp)

    def _analyze_error(self, error: Exception, request_type: str, response: Optional[Any] = None) -> Any:
        """Legacy method - redirects to error analyzer."""
        return self.error_analyzer.analyze_error(error, request_type, response)

    def _make_hnap_request_with_retry(
        self, soap_action: str, request_body: dict, extra_headers: Optional[dict] = None
    ) -> Optional[str]:
        """Legacy method - redirects to request handler."""
        auth_token = self.authenticator.generate_auth_token(soap_action) if self.authenticated else None
        return self.request_handler.make_request_with_retry(
            soap_action,
            request_body,
            extra_headers,
            auth_token,
            self.authenticated,
            self.uid_cookie,
            self.private_key,
        )

    def _make_hnap_request_raw(
        self, soap_action: str, request_body: dict, extra_headers: Optional[dict] = None
    ) -> Optional[str]:
        """Legacy method - redirects to request handler."""
        auth_token = self.authenticator.generate_auth_token(soap_action) if self.authenticated else None
        return self.request_handler._make_raw_request(
            soap_action,
            request_body,
            extra_headers,
            auth_token,
            self.authenticated,
            self.uid_cookie,
            self.private_key,
        )

    def _parse_responses(self, responses: dict[str, str]) -> dict[str, Any]:
        """Legacy method - redirects to parser."""
        return self.parser.parse_responses(responses)

    def _parse_channels(self, hnaps_response: dict[str, Any]) -> dict[str, list]:
        """Legacy method - redirects to parser."""
        return self.parser._parse_channels(hnaps_response)

    def _parse_channel_string(self, raw_data: str, channel_type: str) -> list:
        """Legacy method - redirects to parser."""
        return self.parser._parse_channel_string(raw_data, channel_type)
