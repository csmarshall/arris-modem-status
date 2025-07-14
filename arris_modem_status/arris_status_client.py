"""
Enhanced Arris Status Client with Serial/Parallel Request Option
===============================================================

This version adds a critical debugging option to isolate whether the mysterious
numbers and header parsing errors are caused by:

1. Client-side threading issues (requests/urllib3)
2. Server-side race conditions (Arris firmware bug)
3. HTTP connection pooling problems
4. Session sharing issues

The concurrent parameter allows switching between parallel and serial request modes
to help identify the root cause and provide a reliable fallback option.

Author: Charles Marshall
Version: 1.3.0
"""

import hashlib
import hmac
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    concurrent_mode: bool  # NEW: Track if error occurred in concurrent mode


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
    Enhanced Arris modem client with serial/parallel request option.

    This version adds the ability to switch between concurrent and serial request modes
    to help isolate whether mysterious header parsing errors are caused by:
    - Client-side threading issues (requests/urllib3)
    - Server-side race conditions (Arris firmware)
    - HTTP connection pooling problems

    NEW in v1.3.0: concurrent parameter for debugging and reliability
    """

    def __init__(
        self,
        password: str,
        username: str = "admin",
        host: str = "192.168.100.1",
        port: int = 443,
        concurrent: bool = True,        # NEW: Enable/disable concurrent requests
        max_workers: int = 2,
        max_retries: int = 3,
        base_backoff: float = 0.5,
        capture_errors: bool = True,
        timeout: tuple = (3, 12)
    ):
        """
        Initialize the Arris modem client with serial/parallel option.

        Args:
            password: Modem admin password
            username: Login username (default: "admin")
            host: Modem IP address (default: "192.168.100.1")
            port: HTTPS port (default: 443)
            concurrent: Enable concurrent requests (default: True)
                       Set to False for serial requests to debug threading issues
            max_workers: Concurrent request workers (ignored if concurrent=False)
            max_retries: Max retry attempts for failed requests (default: 3)
            base_backoff: Base backoff time in seconds (default: 0.5)
            capture_errors: Whether to capture error details for analysis (default: True)
            timeout: (connect_timeout, read_timeout) in seconds (default: (3, 12))
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"
        self.concurrent = concurrent            # NEW: Concurrent vs serial mode
        self.max_workers = max_workers if concurrent else 1
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.capture_errors = capture_errors
        self.timeout = timeout

        # Authentication state
        self.private_key: Optional[str] = None
        self.uid_cookie: Optional[str] = None
        self.authenticated: bool = False

        # Error analysis storage
        self.error_captures: List[ErrorCapture] = []

        # Configure HTTP session for the selected mode
        self.session = self._create_session()

        mode_str = "concurrent" if concurrent else "serial"
        logger.info(f"🛡️ ArrisStatusClient v1.3 initialized for {host}:{port}")
        logger.info(f"🔧 Mode: {mode_str}, Workers: {self.max_workers}, Retries: {max_retries}")

    def _create_session(self) -> requests.Session:
        """Create HTTP session optimized for the selected mode."""
        session = requests.Session()

        # Conservative retry strategy
        retry_strategy = Retry(
            total=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=0.3,
            respect_retry_after_header=False
        )

        # HTTP adapter configuration based on mode
        if self.concurrent:
            # Concurrent mode: connection pooling enabled
            adapter = HTTPAdapter(
                pool_connections=1,
                pool_maxsize=5,
                max_retries=retry_strategy,
                pool_block=False
            )
        else:
            # Serial mode: minimal connection pooling to avoid threading issues
            adapter = HTTPAdapter(
                pool_connections=1,
                pool_maxsize=1,  # Single connection only
                max_retries=retry_strategy,
                pool_block=True
            )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Session settings
        session.verify = False
        session.timeout = self.timeout
        session.headers.update({
            "User-Agent": f"ArrisStatusClient/1.3.0-{'Concurrent' if self.concurrent else 'Serial'}",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive" if self.concurrent else "close"  # NEW: Connection strategy
        })

        return session

    def _analyze_malformed_response(
        self,
        response: requests.Response,
        error: Exception,
        request_type: str
    ) -> ErrorCapture:
        """Enhanced error analysis with concurrent mode tracking."""
        try:
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
                recovery_successful=False,
                concurrent_mode=self.concurrent  # NEW: Track the mode when error occurred
            )

            if self.capture_errors:
                self.error_captures.append(capture)

            # Enhanced logging with mode information
            mode_str = "concurrent" if self.concurrent else "serial"
            logger.warning(f"🔍 Malformed response analysis ({mode_str} mode):")
            logger.warning(f"   Request type: {request_type}")
            logger.warning(f"   HTTP status: {getattr(response, 'status_code', 'unknown')}")
            logger.warning(f"   Error type: {error_type}")
            logger.warning(f"   Raw error: {error_details[:200]}...")

            # Extract mysterious numbers with mode context
            if "HeaderParsingError" in error_details and "|" in error_details:
                try:
                    import re
                    match = re.search(r'(\d+\.?\d*)\s*\|', error_details)
                    if match:
                        mysterious_number = match.group(1)
                        logger.warning(f"   🔢 Mysterious number in {mode_str} mode: {mysterious_number}")

                        if not self.concurrent:
                            logger.warning(f"   ⚠️  CRITICAL: Firmware bug occurs even in SERIAL mode!")
                        else:
                            logger.warning(f"   🔍 Firmware bug in concurrent mode (expected)")

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
                recovery_successful=False,
                concurrent_mode=self.concurrent
            )

    def _is_firmware_bug_error(self, error: Exception) -> bool:
        """Detect known Arris firmware bug patterns."""
        error_str = str(error).lower()

        firmware_bug_patterns = [
            "firstheaderlineiscontinuationdefect",
            "headerparsingerror",
            "3.400002",  # Example mysterious number
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
        """Make HNAP request with retry logic (unchanged from previous version)."""
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
            for attempt in range(self.max_retries + 1):
                try:
                    if attempt > 0:
                        backoff_time = self._exponential_backoff(attempt - 1)
                        logger.info(f"🔄 Retry {attempt}/{self.max_retries} for {soap_action} after {backoff_time:.2f}s")
                        time.sleep(backoff_time)

                    captured_warnings.clear()
                    response = self._make_hnap_request_raw(soap_action, request_body, extra_headers)

                    # Check for captured header parsing warnings
                    if captured_warnings and self.capture_errors:
                        for warning_msg in captured_warnings:
                            mode_str = "concurrent" if self.concurrent else "serial"
                            logger.warning(f"🔍 Header parsing warning ({mode_str} mode): {warning_msg}")

                            # Create error capture for header parsing warning
                            header_capture = ErrorCapture(
                                timestamp=time.time(),
                                request_type=soap_action,
                                http_status=200,
                                error_type="header_parsing_warning",
                                raw_error=warning_msg,
                                response_headers={},
                                partial_content=response[:200] if response else "",
                                recovery_successful=True,
                                concurrent_mode=self.concurrent
                            )

                            self.error_captures.append(header_capture)

                            # Extract mysterious number with mode context
                            try:
                                import re
                                match = re.search(r'(\d+\.?\d*)\s*\|', warning_msg)
                                if match:
                                    mysterious_number = match.group(1)
                                    if self.concurrent:
                                        logger.warning(f"   🔢 Channel data in header (concurrent): {mysterious_number}")
                                    else:
                                        logger.warning(f"   🚨 CRITICAL - Channel data in header (SERIAL): {mysterious_number}")
                                        logger.warning(f"   🔍 This confirms it's an Arris firmware bug, not threading!")
                            except Exception as e:
                                logger.debug(f"Failed to extract mysterious number: {e}")

                    if response is not None:
                        if last_capture:
                            last_capture.recovery_successful = True
                            logger.info(f"✅ Recovery successful for {soap_action} on attempt {attempt + 1}")
                        return response

                except (HeaderParsingError, requests.exceptions.RequestException) as e:
                    last_error = e
                    try:
                        response_obj = getattr(e, 'response', None)
                        last_capture = self._analyze_malformed_response(response_obj, e, soap_action)
                    except Exception as analysis_error:
                        logger.debug(f"Error analysis failed: {analysis_error}")

                    if self._is_firmware_bug_error(e):
                        mode_str = "concurrent" if self.concurrent else "serial"
                        logger.warning(f"🐛 Firmware bug detected in {mode_str} mode, attempt {attempt + 1}")

                        if attempt < self.max_retries:
                            continue
                    else:
                        logger.error(f"❌ Unknown error type for {soap_action}: {e}")
                        break

                except Exception as e:
                    logger.error(f"❌ Unexpected error in {soap_action}: {e}")
                    last_error = e
                    break

            logger.error(f"💥 All retry attempts exhausted for {soap_action}")
            return None

        finally:
            urllib3_logger.removeHandler(warning_handler)

    def _exponential_backoff(self, attempt: int, jitter: bool = True) -> float:
        """Calculate exponential backoff time with optional jitter."""
        backoff_time = self.base_backoff * (2 ** attempt)

        if jitter:
            backoff_time += random.uniform(0, backoff_time * 0.1)

        return min(backoff_time, 10.0)

    def _make_hnap_request_raw(
        self,
        soap_action: str,
        request_body: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """Make raw HNAP request (unchanged from previous version)."""
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
            error = requests.exceptions.RequestException(f"HTTP {response.status_code}")
            error.response = response
            raise error

    def _generate_hnap_auth_token(self, soap_action: str, timestamp: int = None) -> str:
        """Generate HNAP auth token (unchanged from previous version)."""
        if timestamp is None:
            timestamp = int(time.time() * 1000) % 2000000000000

        hmac_key = self.private_key or "withoutloginkey"
        message = f'{timestamp}"http://purenetworks.com/HNAP1/{soap_action}"'

        auth_hash = hmac.new(
            hmac_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()

        return f"{auth_hash} {timestamp}"

    def authenticate(self) -> bool:
        """Perform HNAP authentication (unchanged from previous version)."""
        try:
            logger.info("🔐 Starting authentication...")
            start_time = time.time()

            # Step 1: Request challenge
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

            # Step 3: Send login request
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
                mode_str = "concurrent" if self.concurrent else "serial"
                logger.info(f"🎉 Authentication successful ({mode_str} mode)! ({auth_time:.2f}s)")
                return True
            else:
                logger.error("Authentication failed after retries")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive modem status with serial or parallel requests.

        NEW in v1.3.0: Respects the concurrent setting to use either:
        - Concurrent requests (concurrent=True): Faster but may trigger firmware bugs
        - Serial requests (concurrent=False): Slower but avoids threading issues
        """
        try:
            if not self.authenticated:
                if not self.authenticate():
                    raise RuntimeError("Authentication failed")

            mode_str = "concurrent" if self.concurrent else "serial"
            logger.info(f"📊 Retrieving modem status with {mode_str} processing...")
            start_time = time.time()

            # Define the same requests regardless of mode
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

            responses = {}
            successful_requests = 0

            if self.concurrent:
                # Concurrent mode: Use ThreadPoolExecutor
                logger.debug("🚀 Using concurrent request processing")
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_name = {
                        executor.submit(
                            self._make_hnap_request_with_retry,
                            "GetMultipleHNAPs",
                            req_body
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

            else:
                # Serial mode: Process requests one by one
                logger.debug("🔄 Using serial request processing")
                for req_name, req_body in request_definitions:
                    try:
                        logger.debug(f"📤 Processing {req_name} serially...")
                        response = self._make_hnap_request_with_retry("GetMultipleHNAPs", req_body)
                        if response:
                            responses[req_name] = response
                            successful_requests += 1
                            logger.debug(f"✅ {req_name} completed successfully")
                        else:
                            logger.warning(f"⚠️ {req_name} failed after retries")

                        # Small delay between serial requests to be gentle on the modem
                        time.sleep(0.1)

                    except Exception as e:
                        logger.error(f"❌ {req_name} failed with exception: {e}")

            # Parse responses (same regardless of mode)
            parsed_data = self._parse_responses(responses)

            total_time = time.time() - start_time
            downstream_count = len(parsed_data.get('downstream_channels', []))
            upstream_count = len(parsed_data.get('upstream_channels', []))
            channel_count = downstream_count + upstream_count

            logger.info(f"✅ Status retrieved! {channel_count} channels in {total_time:.2f}s ({mode_str} mode)")
            logger.info(f"📊 Success rate: {successful_requests}/{len(request_definitions)} requests")

            # Enhanced error analysis with mode information
            if self.capture_errors and self.error_captures:
                error_count = len(self.error_captures)
                recovery_count = len([e for e in self.error_captures if e.recovery_successful])
                concurrent_errors = len([e for e in self.error_captures if e.concurrent_mode])
                serial_errors = len([e for e in self.error_captures if not e.concurrent_mode])

                parsed_data['_error_analysis'] = {
                    'total_errors': error_count,
                    'firmware_bugs': len([e for e in self.error_captures if e.error_type == "header_parsing"]),
                    'http_errors': len([e for e in self.error_captures if e.error_type.startswith("http_")]),
                    'recovery_rate': recovery_count / error_count if error_count > 0 else 0,
                    'concurrent_mode_errors': concurrent_errors,
                    'serial_mode_errors': serial_errors,
                    'current_mode': 'concurrent' if self.concurrent else 'serial'
                }

                logger.info(f"🔍 Error analysis: {error_count} errors, {recovery_count} recovered")
                if serial_errors > 0:
                    logger.warning(f"⚠️ {serial_errors} errors occurred in SERIAL mode - confirms Arris firmware bug!")

            # Add mode information to response
            parsed_data['_request_mode'] = 'concurrent' if self.concurrent else 'serial'
            parsed_data['_performance'] = {
                'total_time': total_time,
                'requests_successful': successful_requests,
                'requests_total': len(request_definitions),
                'mode': 'concurrent' if self.concurrent else 'serial'
            }

            return parsed_data

        except Exception as e:
            logger.error(f"Status retrieval failed: {e}")
            raise

    def get_error_analysis(self) -> Dict[str, Any]:
        """Enhanced error analysis with concurrent/serial mode breakdown."""
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
            "mode_breakdown": {
                "concurrent_mode_errors": 0,
                "serial_mode_errors": 0,
                "current_mode": 'concurrent' if self.concurrent else 'serial'
            },
            "timeline": [],
            "patterns": []
        }

        # Analyze errors by mode
        for capture in self.error_captures:
            error_type = capture.error_type
            if error_type not in analysis["error_types"]:
                analysis["error_types"][error_type] = 0
            analysis["error_types"][error_type] += 1

            # Track recoveries
            if capture.recovery_successful:
                analysis["recovery_stats"]["total_recoveries"] += 1

            # Track by mode
            if capture.concurrent_mode:
                analysis["mode_breakdown"]["concurrent_mode_errors"] += 1
            else:
                analysis["mode_breakdown"]["serial_mode_errors"] += 1

            # Extract mysterious numbers
            try:
                import re
                pipe_matches = re.findall(r'(\d+\.?\d*)\s*\|', capture.raw_error)
                for match in pipe_matches:
                    if match not in analysis["mysterious_numbers"]:
                        analysis["mysterious_numbers"].append(match)
                        mode_str = "concurrent" if capture.concurrent_mode else "serial"
                        logger.info(f"🔢 Found mysterious number in {mode_str} mode: {match}")

            except Exception as e:
                logger.debug(f"Error extracting numbers from {capture.error_type}: {e}")

            # Add to timeline with mode information
            analysis["timeline"].append({
                "timestamp": capture.timestamp,
                "request_type": capture.request_type,
                "error_type": capture.error_type,
                "recovered": capture.recovery_successful,
                "http_status": capture.http_status,
                "concurrent_mode": capture.concurrent_mode
            })

        # Calculate recovery rate
        if analysis["total_errors"] > 0:
            analysis["recovery_stats"]["recovery_rate"] = analysis["recovery_stats"]["total_recoveries"] / analysis["total_errors"]

        # Enhanced pattern analysis
        concurrent_errors = analysis["mode_breakdown"]["concurrent_mode_errors"]
        serial_errors = analysis["mode_breakdown"]["serial_mode_errors"]

        if concurrent_errors > 0 and serial_errors == 0:
            analysis["patterns"].append("Errors only occur in concurrent mode - likely threading/race condition issue")
        elif concurrent_errors > 0 and serial_errors > 0:
            analysis["patterns"].append("Errors occur in BOTH concurrent and serial modes - confirmed Arris firmware bug")
        elif serial_errors > 0 and concurrent_errors == 0:
            analysis["patterns"].append("Errors only in serial mode - unusual, needs investigation")

        if analysis["mysterious_numbers"]:
            analysis["patterns"].append(f"Found {len(analysis['mysterious_numbers'])} mysterious numbers: {analysis['mysterious_numbers']}")

        return analysis

    # Include all other methods from the previous version unchanged
    def validate_parsing(self) -> Dict[str, Any]:
        """Validate data parsing and return comprehensive quality metrics."""
        try:
            status = self.get_status()

            downstream_count = len(status.get('downstream_channels', []))
            upstream_count = len(status.get('upstream_channels', []))
            total_channels = downstream_count + upstream_count

            completeness_factors = [
                status.get('model_name', 'Unknown') != 'Unknown',
                status.get('internet_status', 'Unknown') != 'Unknown',
                status.get('mac_address', 'Unknown') != 'Unknown',
                downstream_count > 0,
                upstream_count > 0
            ]
            completeness_score = (sum(completeness_factors) / len(completeness_factors)) * 100

            # Enhanced validation with mode information
            channel_quality = {}
            if downstream_count > 0:
                downstream_locked = sum(1 for ch in status['downstream_channels'] if 'Locked' in ch.lock_status)
                downstream_modulations = set(ch.modulation for ch in status['downstream_channels'] if ch.modulation != 'Unknown')

                channel_quality['downstream_validation'] = {
                    'total_channels': downstream_count,
                    'locked_channels': downstream_locked,
                    'all_locked': downstream_locked == downstream_count,
                    'modulation_types': list(downstream_modulations)
                }

            if upstream_count > 0:
                upstream_locked = sum(1 for ch in status['upstream_channels'] if 'Locked' in ch.lock_status)
                upstream_modulations = set(ch.modulation for ch in status['upstream_channels'] if ch.modulation != 'Unknown')

                channel_quality['upstream_validation'] = {
                    'total_channels': upstream_count,
                    'locked_channels': upstream_locked,
                    'all_locked': upstream_locked == upstream_count,
                    'modulation_types': list(upstream_modulations)
                }

            # MAC address validation
            mac_valid = False
            if status.get('mac_address') and status['mac_address'] != 'Unknown':
                import re
                mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
                mac_valid = bool(re.match(mac_pattern, status['mac_address']))

            # Frequency format validation
            freq_formats = {}
            if downstream_count > 0:
                sample_channel = status['downstream_channels'][0]
                freq_formats['downstream_frequency'] = 'Hz' in sample_channel.frequency
                freq_formats['downstream_power'] = 'dBmV' in sample_channel.power
                freq_formats['downstream_snr'] = 'dB' in sample_channel.snr

            return {
                "parsing_validation": {
                    "basic_info_parsed": status.get('model_name', 'Unknown') != 'Unknown',
                    "internet_status_parsed": status.get('internet_status', 'Unknown') != 'Unknown',
                    "downstream_channels_found": downstream_count,
                    "upstream_channels_found": upstream_count,
                    "mac_address_format": mac_valid,
                    "frequency_formats": freq_formats,
                    "channel_data_quality": channel_quality
                },
                "performance_metrics": {
                    "data_completeness_score": completeness_score,
                    "total_channels": total_channels,
                    "parsing_errors": len([e for e in self.error_captures if 'parsing' in e.error_type.lower()]),
                    "firmware_bugs_detected": len([e for e in self.error_captures if e.error_type == "header_parsing_warning"]),
                    "request_mode": 'concurrent' if self.concurrent else 'serial'
                }
            }

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e)}

    def _parse_responses(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """Parse HNAP responses into structured data (unchanged)."""
        # ... (same implementation as before)
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

        for response_type, content in responses.items():
            try:
                data = json.loads(content)
                hnaps_response = data.get("GetMultipleHNAPsResponse", {})

                if response_type == "channel_info":
                    channels = self._parse_channels(hnaps_response)
                    parsed_data["downstream_channels"] = channels["downstream"]
                    parsed_data["upstream_channels"] = channels["upstream"]
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

        if not parsed_data["downstream_channels"] and not parsed_data["upstream_channels"]:
            parsed_data["channel_data_available"] = False

        return parsed_data

    def _parse_channels(self, hnaps_response: Dict[str, Any]) -> Dict[str, List[ChannelInfo]]:
        """Parse channel information from HNAP response (unchanged)."""
        channels = {"downstream": [], "upstream": []}

        try:
            downstream_resp = hnaps_response.get("GetCustomerStatusDownstreamChannelInfoResponse", {})
            downstream_raw = downstream_resp.get("CustomerConnDownstreamChannel", "")

            if downstream_raw:
                channels["downstream"] = self._parse_channel_string(downstream_raw, "downstream")

            upstream_resp = hnaps_response.get("GetCustomerStatusUpstreamChannelInfoResponse", {})
            upstream_raw = upstream_resp.get("CustomerConnUpstreamChannel", "")

            if upstream_raw:
                channels["upstream"] = self._parse_channel_string(upstream_raw, "upstream")

        except Exception as e:
            logger.error(f"Channel parsing error: {e}")

        return channels

    def _parse_channel_string(self, raw_data: str, channel_type: str) -> List[ChannelInfo]:
        """Parse pipe-delimited channel data into ChannelInfo objects (unchanged)."""
        channels = []

        try:
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
        """Clean up resources."""
        if self.capture_errors and self.error_captures:
            mode_str = "concurrent" if self.concurrent else "serial"
            logger.info(f"📊 Session captured {len(self.error_captures)} errors for analysis ({mode_str} mode)")

        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Public API
__all__ = ["ArrisStatusClient", "ChannelInfo", "ErrorCapture"]
