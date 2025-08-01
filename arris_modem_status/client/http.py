"""
HTTP Request Handling for Arris Modem Status Client
===================================================

This module handles HTTP requests, retries, and HNAP protocol specifics.

"""

import logging
import random
import time
from typing import Any, Optional

import requests

from arris_modem_status.exceptions import (
    ArrisHTTPError,
    ArrisTimeoutError,
    wrap_connection_error,
)

logger = logging.getLogger("arris-modem-status")


class HNAPRequestHandler:
    """Handles HNAP HTTP requests with retry logic."""

    def __init__(
        self,
        session: requests.Session,
        base_url: str,
        max_retries: int = 3,
        base_backoff: float = 0.5,
        timeout: tuple = (3, 12),
        instrumentation: Optional[Any] = None,
    ):
        """
        Initialize HNAP request handler.

        Args:
            session: HTTP session to use
            base_url: Base URL for the modem
            max_retries: Maximum retry attempts
            base_backoff: Base backoff time in seconds
            timeout: Request timeout (connect, read)
            instrumentation: Optional performance instrumentation
        """
        self.session = session
        self.base_url = base_url
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.timeout = timeout
        self.instrumentation = instrumentation

    def make_request_with_retry(
        self,
        soap_action: str,
        request_body: dict[str, Any],
        extra_headers: Optional[dict[str, str]] = None,
        auth_token: Optional[str] = None,
        authenticated: bool = False,
        uid_cookie: Optional[str] = None,
        private_key: Optional[str] = None,
    ) -> Optional[str]:
        """
        Make HNAP request with retry logic for network errors.

        Args:
            soap_action: SOAP action name
            request_body: Request body as dictionary
            extra_headers: Additional headers
            auth_token: HNAP auth token
            authenticated: Whether user is authenticated
            uid_cookie: UID cookie value
            private_key: Private key for cookies

        Returns:
            Response text or None if failed
        """
        last_exception = None
        result = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    backoff_time = self._exponential_backoff(attempt - 1)
                    logger.info(f"🔄 Retry {attempt}/{self.max_retries} for {soap_action} after {backoff_time:.2f}s")
                    time.sleep(backoff_time)

                response = self._make_raw_request(
                    soap_action,
                    request_body,
                    extra_headers,
                    auth_token,
                    authenticated,
                    uid_cookie,
                    private_key,
                )

                if response is not None:
                    result = response
                    break

            except requests.exceptions.RequestException as e:
                last_exception = e
                response_obj = getattr(e, "response", None)

                # Check if this is a retryable error
                error_str = str(e).lower()
                is_timeout = isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout))
                is_network_error = isinstance(e, requests.exceptions.ConnectionError) or any(
                    term in error_str for term in ["timeout", "connection", "network"]
                )

                # If it's a timeout and we've exhausted retries, raise TimeoutError
                if is_timeout and attempt >= self.max_retries:
                    raise ArrisTimeoutError(
                        f"Request to {soap_action} timed out",
                        details={"operation": soap_action, "attempt": attempt + 1, "timeout": self.timeout},
                    ) from e

                # Handle ConnectionError
                if isinstance(e, requests.exceptions.ConnectionError):
                    if attempt < self.max_retries:
                        logger.debug(f"🔧 Connection error, attempt {attempt + 1}")
                        continue
                    host = self.base_url.split("://")[1].split(":")[0]
                    port = int(self.base_url.split(":")[-1].split("/")[0])
                    raise wrap_connection_error(e, host, port) from e

                # HTTP errors should not be retried - but for certain operations, return None instead of raising
                if response_obj is not None:
                    status_code = getattr(response_obj, "status_code", None)
                    if status_code:
                        # For non-critical operations (like status requests), return None instead of raising
                        # This allows partial data retrieval to continue
                        if soap_action in ["GetMultipleHNAPs", "GetCustomerStatusSoftware"] and status_code in [403, 404, 500]:
                            logger.warning(f"HTTP {status_code} for {soap_action}, returning None to allow partial data retrieval")
                            return None

                        response_text = ""
                        if hasattr(response_obj, "text") and isinstance(getattr(response_obj, "text", ""), str):
                            response_text = response_obj.text[:500]

                        raise ArrisHTTPError(
                            f"HTTP {status_code} error for {soap_action}",
                            status_code=status_code,
                            details={"operation": soap_action, "response_text": response_text},
                        ) from e

                # Handle HTTPError specifically
                if isinstance(e, requests.exceptions.HTTPError):
                    status_code = None
                    if hasattr(e, "response") and hasattr(e.response, "status_code"):
                        status_code = e.response.status_code
                    elif response_obj is not None and hasattr(response_obj, "status_code"):
                        status_code = response_obj.status_code
                    else:
                        # Try to parse from error message
                        import re

                        match = re.search(r"(\d{3})", str(e))
                        if match:
                            status_code = int(match.group(1))

                    if status_code:
                        # For non-critical operations, return None to allow partial data retrieval
                        if soap_action in ["GetMultipleHNAPs", "GetCustomerStatusSoftware"] and status_code in [403, 404, 500]:
                            logger.warning(f"HTTP {status_code} for {soap_action}, returning None to allow partial data retrieval")
                            return None

                        response_text = ""
                        if hasattr(response_obj, "text") and isinstance(getattr(response_obj, "text", ""), str):
                            response_text = response_obj.text[:500]

                        raise ArrisHTTPError(
                            f"HTTP {status_code} error for {soap_action}",
                            status_code=status_code,
                            details={"operation": soap_action, "response_text": str(e)[:500]},
                        ) from e

                # For network/timeout errors, check if we should retry
                if is_network_error:
                    logger.debug(f"🔧 Network error, attempt {attempt + 1}")

                    if attempt < self.max_retries:
                        continue
                    # For connection errors at the end, raise ArrisConnectionError
                    if isinstance(e, requests.exceptions.ConnectionError) and not is_timeout:
                        host = self.base_url.split("://")[1].split(":")[0]
                        port = int(self.base_url.split(":")[-1].split("/")[0])
                        raise wrap_connection_error(e, host, port) from e
                else:
                    # Re-raise non-retryable errors
                    raise

            except Exception as e:
                # For unexpected errors during status requests, return None to allow partial data
                if soap_action in ["GetMultipleHNAPs", "GetCustomerStatusSoftware"]:
                    logger.warning(f"Unexpected error for {soap_action}: {e}, returning None to allow partial data retrieval")
                    return None
                raise

        if result is None:
            logger.error(f"💥 All retry attempts exhausted for {soap_action}")

        return result

    def _make_raw_request(
        self,
        soap_action: str,
        request_body: dict[str, Any],
        extra_headers: Optional[dict[str, str]] = None,
        auth_token: Optional[str] = None,
        authenticated: bool = False,
        uid_cookie: Optional[str] = None,
        private_key: Optional[str] = None,
    ) -> Optional[str]:
        """Make raw HNAP request using HTTP session."""
        start_time = (
            self.instrumentation.start_timer(f"hnap_request_{soap_action}") if self.instrumentation else time.time()
        )

        # Build headers
        headers = {"Content-Type": "application/json"}

        # Check if this is the initial challenge request
        is_challenge_request = (
            soap_action == "Login"
            and request_body.get("Login", {}).get("Action") == "request"
            and request_body.get("Login", {}).get("LoginPassword", "") == ""
        )

        # Only include HNAP_AUTH for non-challenge requests
        if not is_challenge_request and auth_token:
            headers["HNAP_AUTH"] = auth_token

        # Add SOAP action header
        if soap_action == "Login":
            headers["SOAPAction"] = f'"http://purenetworks.com/HNAP1/{soap_action}"'
            headers["Referer"] = f"{self.base_url}/Login.html"
        else:
            headers["SOAPACTION"] = f'"http://purenetworks.com/HNAP1/{soap_action}"'
            headers["Referer"] = f"{self.base_url}/Cmconnectionstatus.html"

        # Add cookies for authenticated requests
        if authenticated and uid_cookie:
            cookies = [f"uid={uid_cookie}"]
            if private_key:
                cookies.append(f"PrivateKey={private_key}")
            headers["Cookie"] = "; ".join(cookies)

        # Merge additional headers
        if extra_headers:
            headers.update(extra_headers)

        logger.debug(f"📤 HNAP: {soap_action}")

        try:
            # Execute request with relaxed parsing (handled by our session)
            response = self.session.post(
                f"{self.base_url}/HNAP1/",
                json=request_body,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                response_text = str(response.text)
                logger.debug(f"📥 Response: {len(response_text)} chars")

                # Record successful timing
                if self.instrumentation:
                    self.instrumentation.record_timing(
                        f"hnap_request_{soap_action}",
                        start_time,
                        success=True,
                        http_status=response.status_code,
                        response_size=len(response_text),
                    )

                # Return None if response is empty, otherwise return the text
                return response_text if response_text.strip() else None

            # Record failed timing
            if self.instrumentation:
                self.instrumentation.record_timing(
                    f"hnap_request_{soap_action}",
                    start_time,
                    success=False,
                    error_type=f"HTTP_{response.status_code}",
                    http_status=response.status_code,
                )

            raise ArrisHTTPError(
                f"HTTP {response.status_code} response from modem",
                status_code=response.status_code,
                details={"operation": soap_action, "response_text": response.text[:500]},
            )

        except ArrisHTTPError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Record exception timing
            if self.instrumentation:
                self.instrumentation.record_timing(
                    f"hnap_request_{soap_action}",
                    start_time,
                    success=False,
                    error_type=str(type(e).__name__),
                )
            raise

    def _exponential_backoff(self, attempt: int, jitter: bool = True) -> float:
        """Calculate exponential backoff time with optional jitter."""
        backoff_time = self.base_backoff * (2**attempt)

        if jitter:
            backoff_time += random.uniform(0, backoff_time * 0.1)

        return float(min(backoff_time, 10.0))
