"""
Arris Status Client with Error Analysis and Robust Retry Logic
=============================================================

This version captures and analyzes the actual malformed responses from Arris firmware
to understand what's really happening, plus implements intelligent retry logic.

Author: Charles Marshall
Version: 1.2.0
"""
import hashlib
import hmac
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.exceptions import HeaderParsingError
from urllib3.util.retry import Retry

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("arris-modem-status")


@dataclass
class ErrorCapture:
    """Captures details about malformed responses for analysis."""
    timestamp: float
    request_type: str
    http_status: int
    error_type: str
    raw_error: str
    response_headers: Dict[str, str]
    partial_content: str
    recovery_successful: bool


@dataclass
class ChannelInfo:
    """Represents a single modem channel with optimized field access."""
    channel_id: str
    frequency: str
    power: str
    snr: str
    modulation: str
    lock_status: str
    corrected_errors: Optional[str] = None
    uncorrected_errors: Optional[str] = None
    channel_type: str = "unknown"

    def __post_init__(self):
        """Post-init processing for data validation and cleanup."""
        # Clean up frequency format
        if self.frequency.isdigit():
            self.frequency = f"{self.frequency} Hz"

        # Clean up power format
        if self.power and not self.power.endswith("dBmV"):
            try:
                float(self.power)
                self.power = f"{self.power} dBmV"
            except ValueError:
                pass

        # Clean up SNR format
        if self.snr and self.snr != "N/A" and not self.snr.endswith("dB"):
            try:
                float(self.snr)
                self.snr = f"{self.snr} dB"
            except ValueError:
                pass


class ArrisStatusClient:
    """
    Production-ready Arris modem client with comprehensive error analysis and retry logic.

    This client captures and analyzes malformed responses to understand what's really
    happening with the Arris firmware bugs, while implementing intelligent retry and
    backoff strategies for maximum reliability.
    """

    def __init__(
        self,
        password: str,
        username: str = "admin",
        host: str = "192.168.100.1",
        port: int = 443,
        max_workers: int = 2,  # Reduced for reliability
        max_retries: int = 3,
        base_backoff: float = 0.5,
        capture_errors: bool = True
    ):
        """
        Initialize the Arris modem client with robust error handling.

        Args:
            password: Modem admin password
            username: Login username (default: "admin")
            host: Modem IP address (default: "192.168.100.1")
            port: HTTPS port (default: 443)
            max_workers: Concurrent request workers (default: 2, conservative)
            max_retries: Max retry attempts for failed requests (default: 3)
            base_backoff: Base backoff time in seconds (default: 0.5)
            capture_errors: Whether to capture error details for analysis (default: True)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.capture_errors = capture_errors

        # Authentication state
        self.private_key: Optional[str] = None
        self.uid_cookie: Optional[str] = None
        self.authenticated: bool = False

        # Error analysis storage
        self.error_captures: List[ErrorCapture] = []

        # Configure HTTP session for reliability
        self.session = self._create_robust_session()

        logger.info(f"🛡️ ArrisStatusClient v1.2 initialized for {host}:{port}")
        logger.info(f"🔧 Config: {max_workers} workers, {max_retries} retries, {base_backoff}s backoff")

    def _create_robust_session(self) -> requests.Session:
        """Create HTTP session optimized for reliability over speed."""
        session = requests.Session()

        # Conservative retry strategy
        retry_strategy = Retry(
            total=2,  # Lower for faster fallback to custom retry logic
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=0.3,
            respect_retry_after_header=False
        )

        # HTTP adapter with conservative settings
        adapter = HTTPAdapter(
            pool_connections=1,
            pool_maxsize=5,  # Reduced pool size
            max_retries=retry_strategy,
            pool_block=False
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Conservative session settings
        session.verify = False
        session.timeout = (3, 12)  # Longer read timeout for reliability
        session.headers.update({
            "User-Agent": "ArrisStatusClient/1.2.0-Robust",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        })

        return session

    def _exponential_backoff(self, attempt: int, jitter: bool = True) -> float:
        """Calculate exponential backoff time with optional jitter."""
        backoff_time = self.base_backoff * (2 ** attempt)

        if jitter:
            # Add random jitter to avoid thundering herd
            backoff_time += random.uniform(0, backoff_time * 0.1)

        return min(backoff_time, 10.0)  # Cap at 10 seconds

    def _analyze_malformed_response(
        self,
        response: requests.Response,
        error: Exception,
        request_type: str
    ) -> ErrorCapture:
        """
        Analyze and capture details about malformed responses.

        This helps us understand what's really in those malformed headers/responses.
        """
        try:
            # Extract as much information as possible
            error_details = str(error)

            # Try to get partial content even from failed responses
            partial_content = ""
            try:
                partial_content = response.text[:500] if hasattr(response, 'text') else ""
            except Exception:
                try:
                    partial_content = str(response.content[:500])
                except Exception:
                    partial_content = "Unable to extract content"

            # Extract headers that we can read
            headers = {}
            try:
                headers = dict(response.headers) if hasattr(response, 'headers') else {}
            except Exception:
                headers = {"error": "Unable to extract headers"}

            # Look for patterns in the error
            error_type = "unknown"
            if "HeaderParsingError" in error_details:
                error_type = "header_parsing"
            elif "HTTP 403" in error_details:
                error_type = "http_403"
            elif "HTTP 500" in error_details:
                error_type = "http_500"
            elif "timeout" in error_details.lower():
                error_type = "timeout"

            capture = ErrorCapture(
                timestamp=time.time(),
                request_type=request_type,
                http_status=getattr(response, 'status_code', 0),
                error_type=error_type,
                raw_error=error_details,
                response_headers=headers,
                partial_content=partial_content,
                recovery_successful=False  # Will be updated if retry succeeds
            )

            if self.capture_errors:
                self.error_captures.append(capture)

            # Log detailed analysis
            logger.warning(f"🔍 Malformed response analysis:")
            logger.warning(f"   Request type: {request_type}")
            logger.warning(f"   HTTP status: {getattr(response, 'status_code', 'unknown')}")
            logger.warning(f"   Error type: {error_type}")
            logger.warning(f"   Raw error: {error_details[:200]}...")

            if partial_content:
                logger.warning(f"   Partial content: {partial_content[:100]}...")

            # Extract the mysterious number from header parsing errors
            if "HeaderParsingError" in error_details and "|" in error_details:
                try:
                    # Extract the number before the pipe
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*\|', error_details)
                    if match:
                        mysterious_number = match.group(1)
                        logger.warning(f"   🔍 Mysterious number in header: {mysterious_number}")

                        # Try to correlate with channel data
                        if hasattr(self, '_last_channel_data'):
                            logger.warning(f"   🔗 Checking correlation with channel data...")
                except Exception as e:
                    logger.debug(f"Failed to extract mysterious number: {e}")

            return capture

        except Exception as e:
            logger.error(f"Failed to analyze malformed response: {e}")
            return ErrorCapture(
                timestamp=time.time(),
                request_type=request_type,
                http_status=0,
                error_type="analysis_failed",
                raw_error=str(error),
                response_headers={},
                partial_content="",
                recovery_successful=False
            )

    def _is_firmware_bug_error(self, error: Exception) -> bool:
        """
        Detect known Arris firmware bug patterns.

        Returns True if this looks like a known firmware bug that we can retry.
        """
        error_str = str(error).lower()

        # Known firmware bug patterns
        firmware_bug_patterns = [
            "firstheaderlineiscontinuationdefect",
            "headerparsingerror",
            "3.400002",  # The mysterious number
            "content-type: text/html",
            "http 403",
            "unparsed data:",
        ]

        return any(pattern in error_str for pattern in firmware_bug_patterns)

    def _make_hnap_request_with_retry(
        self,
        soap_action: str,
        request_body: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Make HNAP request with intelligent retry logic and error analysis.

        This method implements exponential backoff and captures detailed error
        information to help understand what's really happening with firmware bugs.
        """
        last_error = None
        last_capture = None

        # Install a custom log handler to capture urllib3 warnings
        captured_warnings = []

        class WarningCapture(logging.Handler):
            def emit(self, record):
                if "Failed to parse headers" in record.getMessage() and "|" in record.getMessage():
                    captured_warnings.append(record.getMessage())

        warning_handler = WarningCapture()
        urllib3_logger = logging.getLogger("urllib3.connection")
        urllib3_logger.addHandler(warning_handler)

        try:
            for attempt in range(self.max_retries + 1):  # +1 for initial attempt
                try:
                    if attempt > 0:
                        # Calculate backoff time
                        backoff_time = self._exponential_backoff(attempt - 1)
                        logger.info(f"🔄 Retry {attempt}/{self.max_retries} for {soap_action} after {backoff_time:.2f}s")
                        time.sleep(backoff_time)

                    # Clear previous warnings
                    captured_warnings.clear()

                    # Make the actual request
                    response = self._make_hnap_request_raw(soap_action, request_body, extra_headers)

                    # Check for captured header parsing warnings
                    if captured_warnings and self.capture_errors:
                        for warning_msg in captured_warnings:
                            logger.warning(f"🔍 Captured header parsing warning: {warning_msg}")

                            # Create error capture for header parsing warning
                            header_capture = ErrorCapture(
                                timestamp=time.time(),
                                request_type=soap_action,
                                http_status=200,  # Response succeeded despite malformed headers
                                error_type="header_parsing_warning",
                                raw_error=warning_msg,
                                response_headers={},
                                partial_content=response[:200] if response else "",
                                recovery_successful=True  # Request succeeded despite warning
                            )

                            self.error_captures.append(header_capture)

                            # Extract mysterious number
                            try:
                                import re
                                match = re.search(r'(\d+\.?\d*)\s*\|', warning_msg)
                                if match:
                                    mysterious_number = match.group(1)
                                    logger.warning(f"   🔢 Mysterious number extracted: {mysterious_number}")
                            except Exception as e:
                                logger.debug(f"Failed to extract mysterious number: {e}")

                    if response is not None:
                        # Success! Update any previous error captures
                        if last_capture:
                            last_capture.recovery_successful = True
                            logger.info(f"✅ Recovery successful for {soap_action} on attempt {attempt + 1}")

                        return response

                except (HeaderParsingError, requests.exceptions.RequestException) as e:
                    last_error = e

                    # Analyze the error in detail
                    try:
                        # Get response object if available
                        response_obj = getattr(e, 'response', None)
                        last_capture = self._analyze_malformed_response(response_obj, e, soap_action)
                    except Exception as analysis_error:
                        logger.debug(f"Error analysis failed: {analysis_error}")

                    # Check if this is a known firmware bug we should retry
                    if self._is_firmware_bug_error(e):
                        logger.warning(f"🐛 Firmware bug detected in {soap_action}, attempt {attempt + 1}")

                        if attempt < self.max_retries:
                            continue  # Retry with backoff
                    else:
                        # Unknown error type, don't retry
                        logger.error(f"❌ Unknown error type for {soap_action}: {e}")
                        break

                except Exception as e:
                    # Unexpected error
                    logger.error(f"❌ Unexpected error in {soap_action}: {e}")
                    last_error = e
                    break

            # All retries exhausted
            logger.error(f"💥 All retry attempts exhausted for {soap_action}")
            return None

        finally:
            # Remove the warning handler
            urllib3_logger.removeHandler(warning_handler)

    def _make_hnap_request_raw(
        self,
        soap_action: str,
        request_body: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Make raw HNAP request without retry logic.

        This is the actual HTTP request implementation that gets called by the retry wrapper.
        """
        # Generate authentication token
        auth_token = self._generate_hnap_auth_token(soap_action)

        # Build headers
        headers = {
            "HNAP_AUTH": auth_token,
            "Content-Type": "application/json"
        }

        # Add SOAP action header
        if soap_action == "Login":
            headers["SOAPAction"] = f'"http://purenetworks.com/HNAP1/{soap_action}"'
            headers["Referer"] = f"{self.base_url}/Login.html"
        else:
            headers["SOAPACTION"] = f'"http://purenetworks.com/HNAP1/{soap_action}"'
            headers["Referer"] = f"{self.base_url}/Cmconnectionstatus.html"

        # Add cookies for authenticated requests
        if self.authenticated and self.uid_cookie:
            cookies = [f"uid={self.uid_cookie}"]
            if self.private_key:
                cookies.append(f"PrivateKey={self.private_key}")
            headers["Cookie"] = "; ".join(cookies)

        # Merge additional headers
        if extra_headers:
            headers.update(extra_headers)

        logger.debug(f"📤 HNAP: {soap_action}")

        # Execute request
        response = self.session.post(
            f"{self.base_url}/HNAP1/",
            json=request_body,
            headers=headers
        )

        if response.status_code == 200:
            logger.debug(f"📥 Response: {len(response.text)} chars")
            return response.text
        else:
            # Create a custom exception that includes the response
            error = requests.exceptions.RequestException(f"HTTP {response.status_code}")
            error.response = response
            raise error

    def _generate_hnap_auth_token(self, soap_action: str, timestamp: int = None) -> str:
        """Generate HNAP auth token."""
        if timestamp is None:
            timestamp = int(time.time() * 1000) % 2000000000000

        # Use cached private key or default
        hmac_key = self.private_key or "withoutloginkey"

        # Build the message exactly as the modem's JavaScript does
        message = f'{timestamp}"http://purenetworks.com/HNAP1/{soap_action}"'

        # Compute HMAC-SHA256 hash
        auth_hash = hmac.new(
            hmac_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

        return f"{auth_hash} {timestamp}"

    def authenticate(self) -> bool:
        """Perform HNAP authentication with retry logic."""
        try:
            logger.info("🔐 Starting robust authentication...")
            start_time = time.time()

            # Step 1: Request challenge with retry
            challenge_request = {
                "Login": {
                    "Action": "request",
                    "Username": self.username,
                    "LoginPassword": "",
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }

            challenge_response = self._make_hnap_request_with_retry("Login", challenge_request)
            if not challenge_response:
                logger.error("Failed to get authentication challenge after retries")
                return False

            # Parse challenge response
            try:
                data = json.loads(challenge_response)
                login_resp = data["LoginResponse"]
                challenge = login_resp["Challenge"]
                public_key = login_resp["PublicKey"]
                self.uid_cookie = login_resp.get("Cookie")
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Challenge parsing failed: {e}")
                return False

            # Step 2: Compute private key and login password
            key_material = public_key + self.password
            self.private_key = hmac.new(
                key_material.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()

            login_password = hmac.new(
                self.private_key.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()

            # Step 3: Send login request with retry
            login_request = {
                "Login": {
                    "Action": "login",
                    "Username": self.username,
                    "LoginPassword": login_password,
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }

            login_headers = {"Cookie": f"uid={self.uid_cookie}"} if self.uid_cookie else {}
            login_response = self._make_hnap_request_with_retry("Login", login_request, login_headers)

            if login_response and any(term in login_response.lower() for term in ["success", "ok", "true"]):
                self.authenticated = True
                auth_time = time.time() - start_time
                logger.info(f"🎉 Robust authentication successful! ({auth_time:.2f}s)")
                return True
            else:
                logger.error("Authentication failed after retries")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive modem status with robust error handling.

        Uses conservative concurrent processing and comprehensive retry logic
        to handle Arris firmware bugs gracefully.
        """
        try:
            # Ensure authentication
            if not self.authenticated:
                if not self.authenticate():
                    raise RuntimeError("Authentication failed")

            logger.info("📊 Retrieving modem status with robust error handling...")
            start_time = time.time()

            # Define requests with conservative approach
            request_definitions = [
                ("startup_connection", {
                    "GetMultipleHNAPs": {
                        "GetCustomerStatusStartupSequence": "",
                        "GetCustomerStatusConnectionInfo": ""
                    }
                }),
                ("internet_register", {
                    "GetMultipleHNAPs": {
                        "GetInternetConnectionStatus": "",
                        "GetArrisRegisterInfo": "",
                        "GetArrisRegisterStatus": ""
                    }
                }),
                ("channel_info", {
                    "GetMultipleHNAPs": {
                        "GetCustomerStatusDownstreamChannelInfo": "",
                        "GetCustomerStatusUpstreamChannelInfo": ""
                    }
                })
            ]

            # Execute requests with conservative concurrency
            responses = {}
            successful_requests = 0

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all requests
                future_to_name = {
                    executor.submit(
                        self._make_hnap_request_with_retry,
                        "GetMultipleHNAPs",
                        req_body
                    ): req_name
                    for req_name, req_body in request_definitions
                }

                # Collect results with timeout
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

            # Parse responses
            parsed_data = self._parse_responses(responses)

            total_time = time.time() - start_time
            channel_count = len(parsed_data.get('downstream_channels', [])) + len(parsed_data.get('upstream_channels', []))

            logger.info(f"✅ Status retrieved! {channel_count} channels in {total_time:.2f}s")
            logger.info(f"📊 Success rate: {successful_requests}/{len(request_definitions)} requests")

            # Add error analysis to response
            if self.capture_errors and self.error_captures:
                parsed_data['_error_analysis'] = {
                    'total_errors': len(self.error_captures),
                    'firmware_bugs': len([e for e in self.error_captures if e.error_type == "header_parsing"]),
                    'http_errors': len([e for e in self.error_captures if e.error_type.startswith("http_")]),
                    'recovery_rate': len([e for e in self.error_captures if e.recovery_successful]) / len(self.error_captures) if self.error_captures else 0
                }

            return parsed_data

        except Exception as e:
            logger.error(f"Status retrieval failed: {e}")
            raise

    def get_error_analysis(self) -> Dict[str, Any]:
        """
        Get detailed analysis of captured errors to understand firmware behavior.

        Returns comprehensive information about what's really happening with
        those malformed responses.
        """
        if not self.error_captures:
            return {"message": "No errors captured yet"}

        analysis = {
            "total_errors": len(self.error_captures),
            "error_types": {},
            "mysterious_numbers": [],
            "recovery_stats": {
                "total_recoveries": 0,
                "recovery_rate": 0.0
            },
            "timeline": [],
            "patterns": []
        }

        # Analyze error types
        for capture in self.error_captures:
            error_type = capture.error_type
            if error_type not in analysis["error_types"]:
                analysis["error_types"][error_type] = 0
            analysis["error_types"][error_type] += 1

            # Track recoveries
            if capture.recovery_successful:
                analysis["recovery_stats"]["total_recoveries"] += 1

            # Extract mysterious numbers from both error messages and header warnings
            try:
                import re
                # Look for numbers followed by pipe (header parsing pattern)
                pipe_matches = re.findall(r'(\d+\.?\d*)\s*\|', capture.raw_error)
                for match in pipe_matches:
                    if match not in analysis["mysterious_numbers"]:
                        analysis["mysterious_numbers"].append(match)
                        logger.info(f"🔢 Found mysterious number in {capture.error_type}: {match}")

                # Also look for other patterns
                if "FirstHeaderLineIsContinuationDefect" in capture.raw_error:
                    # This is definitely a header parsing issue
                    analysis["patterns"].append("Header parsing error with injected data")

                # Look for numbers in parentheses or quotes
                other_matches = re.findall(r"'([^']*\d+\.?\d*[^']*)'", capture.raw_error)
                for match in other_matches:
                    number_in_match = re.findall(r'(\d+\.?\d*)', match)
                    for num in number_in_match:
                        if num not in analysis["mysterious_numbers"] and len(num) > 1:
                            analysis["mysterious_numbers"].append(num)

            except Exception as e:
                logger.debug(f"Error extracting numbers from {capture.error_type}: {e}")

            # Add to timeline
            analysis["timeline"].append({
                "timestamp": capture.timestamp,
                "request_type": capture.request_type,
                "error_type": capture.error_type,
                "recovered": capture.recovery_successful,
                "http_status": capture.http_status
            })

        # Calculate recovery rate
        if analysis["total_errors"] > 0:
            analysis["recovery_stats"]["recovery_rate"] = analysis["recovery_stats"]["total_recoveries"] / analysis["total_errors"]

        # Analyze patterns
        header_parsing_errors = len([e for e in self.error_captures if e.error_type == "header_parsing_warning"])
        if header_parsing_errors > 0:
            analysis["patterns"].append(f"Found {header_parsing_errors} header parsing warnings with injected data")

        http_403_errors = len([e for e in self.error_captures if e.error_type == "http_403"])
        if http_403_errors > 0:
            analysis["patterns"].append(f"Found {http_403_errors} HTTP 403 errors (likely authentication issues)")

        if analysis["mysterious_numbers"]:
            analysis["patterns"].append(f"Found {len(analysis['mysterious_numbers'])} unique mysterious numbers: {analysis['mysterious_numbers']}")

        return analysis

    def _parse_responses(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """Parse HNAP responses into structured data."""
        # Initialize with defaults
        parsed_data = {
            "model_name": "Unknown",
            "firmware_version": "Unknown",
            "system_uptime": "Unknown",
            "internet_status": "Unknown",
            "connection_status": "Unknown",
            "mac_address": "Unknown",
            "serial_number": "Unknown",
            "downstream_channels": [],
            "upstream_channels": [],
            "channel_data_available": True
        }

        # Parse each response type
        for response_type, content in responses.items():
            try:
                data = json.loads(content)
                hnaps_response = data.get("GetMultipleHNAPsResponse", {})

                if response_type == "channel_info":
                    channels = self._parse_channels(hnaps_response)
                    parsed_data["downstream_channels"] = channels["downstream"]
                    parsed_data["upstream_channels"] = channels["upstream"]

                    # Store for correlation analysis
                    self._last_channel_data = channels

                elif response_type == "startup_connection":
                    conn_info = hnaps_response.get("GetCustomerStatusConnectionInfoResponse", {})
                    parsed_data.update({
                        "system_uptime": conn_info.get("CustomerCurSystemTime", "Unknown"),
                        "connection_status": conn_info.get("CustomerConnNetworkAccess", "Unknown"),
                        "model_name": conn_info.get("StatusSoftwareModelName", "Unknown")
                    })

                elif response_type == "internet_register":
                    internet_info = hnaps_response.get("GetInternetConnectionStatusResponse", {})
                    register_info = hnaps_response.get("GetArrisRegisterInfoResponse", {})

                    parsed_data.update({
                        "internet_status": internet_info.get("InternetConnection", "Unknown"),
                        "mac_address": register_info.get("MacAddress", "Unknown"),
                        "serial_number": register_info.get("SerialNumber", "Unknown")
                    })

            except json.JSONDecodeError as e:
                logger.warning(f"Parse failed for {response_type}: {e}")

        # Update availability status
        if not parsed_data["downstream_channels"] and not parsed_data["upstream_channels"]:
            parsed_data["channel_data_available"] = False

        return parsed_data

    def _parse_channels(self, hnaps_response: Dict[str, Any]) -> Dict[str, List[ChannelInfo]]:
        """Parse channel information from HNAP response."""
        channels = {"downstream": [], "upstream": []}

        try:
            # Parse downstream channels
            downstream_resp = hnaps_response.get("GetCustomerStatusDownstreamChannelInfoResponse", {})
            downstream_raw = downstream_resp.get("CustomerConnDownstreamChannel", "")

            if downstream_raw:
                channels["downstream"] = self._parse_channel_string(downstream_raw, "downstream")

            # Parse upstream channels
            upstream_resp = hnaps_response.get("GetCustomerStatusUpstreamChannelInfoResponse", {})
            upstream_raw = upstream_resp.get("CustomerConnUpstreamChannel", "")

            if upstream_raw:
                channels["upstream"] = self._parse_channel_string(upstream_raw, "upstream")

        except Exception as e:
            logger.error(f"Channel parsing error: {e}")

        return channels

    def _parse_channel_string(self, raw_data: str, channel_type: str) -> List[ChannelInfo]:
        """Parse pipe-delimited channel data into ChannelInfo objects."""
        channels = []

        try:
            # Split on channel separator
            entries = raw_data.split("|+|")

            for entry in entries:
                if not entry.strip():
                    continue

                fields = entry.split("^")

                if channel_type == "downstream" and len(fields) >= 6:
                    channel = ChannelInfo(
                        channel_id=fields[0] or "Unknown",
                        lock_status=fields[1] or "Unknown",
                        modulation=fields[2] or "Unknown",
                        frequency=fields[4] if len(fields) > 4 else "Unknown",
                        power=fields[5] if len(fields) > 5 else "Unknown",
                        snr=fields[6] if len(fields) > 6 else "Unknown",
                        corrected_errors=fields[7] if len(fields) > 7 else None,
                        uncorrected_errors=fields[8] if len(fields) > 8 else None,
                        channel_type=channel_type
                    )
                    channels.append(channel)

                elif channel_type == "upstream" and len(fields) >= 7:
                    channel = ChannelInfo(
                        channel_id=fields[0] or "Unknown",
                        lock_status=fields[1] or "Unknown",
                        modulation=fields[2] or "Unknown",
                        frequency=fields[5] if len(fields) > 5 else "Unknown",
                        power=fields[6] if len(fields) > 6 else "Unknown",
                        snr="N/A",
                        channel_type=channel_type
                    )
                    channels.append(channel)

        except Exception as e:
            logger.error(f"Error parsing {channel_type} channel string: {e}")

        return channels

    def close(self) -> None:
        """Clean up resources and optionally save error analysis."""
        if self.capture_errors and self.error_captures:
            logger.info(f"📊 Session captured {len(self.error_captures)} errors for analysis")

        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Public API
__all__ = ["ArrisStatusClient", "ChannelInfo", "ErrorCapture"]
