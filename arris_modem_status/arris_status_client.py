"""
Arris Cable Modem Status Client
A Python client library for querying status information from Arris cable modems
(S33, S34, etc.) using the HNAP (Home Network Administration Protocol).
This implementation includes:
- Complete HNAP authentication with dual-cookie support
- Robust handling of Arris firmware HTTP response bugs
- Comprehensive channel data extraction and parsing
- Production-ready error handling and logging
Example Usage:
    from arris_modem_status import ArrisStatusClient
    client = ArrisStatusClient(password="your_modem_password")
    status = client.get_status()
    print(f"Internet: {status['internet_status']}")
    print(f"Channels: {len(status['downstream_channels'])}")
Author: Charles Marshall
License: MIT
Version: 1.0.0
"""
import hashlib
import hmac
import json
import logging
import time
import urllib3
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import requests


# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger("arris-modem-status")


@dataclass
class ChannelInfo:
    """
    Represents a single modem channel (downstream or upstream).
    Channel data is extracted from the modem's pipe-delimited format and
    parsed into structured fields for easy access and analysis.
    """
    channel_id: str
    frequency: str  # e.g., "549000000 Hz"
    power: str      # e.g., "2.5 dBmV"
    snr: str        # e.g., "39.0 dB" (downstream only)
    modulation: str  # e.g., "256QAM", "OFDM PLC"
    lock_status: str  # e.g., "Locked", "Unlocked"
    corrected_errors: Optional[str] = None    # Downstream only
    uncorrected_errors: Optional[str] = None  # Downstream only
    channel_type: str = "unknown"  # "downstream" or "upstream"


class ArrisStatusClient:
    """
    Client for querying Arris cable modem status via HNAP protocol.
    This client implements the complete HNAP authentication flow discovered
    through reverse engineering of the modem's JavaScript interface. It handles
    the complex challenge-response authentication and dual-cookie session
    management required by Arris modems.
    The client gracefully handles a known firmware bug where channel data
    responses include malformed HTTP headers by using the requests library,
    which is more forgiving than strict HTTP parsers.
    Attributes:
        host (str): Modem IP address or hostname
        port (int): HTTPS port (typically 443)
        username (str): Login username (typically "admin")
        password (str): Login password
        base_url (str): Complete base URL for requests
        session (requests.Session): HTTP session with configured settings
        private_key (str): Computed HMAC key for authenticated requests
        uid_cookie (str): Session cookie from authentication
        authenticated (bool): Current authentication status
    """
    def __init__(
        self,
        password: str,
        username: str = "admin",
        host: str = "192.168.100.1",
        port: int = 443
    ):
        """
        Initialize the Arris modem client.
        Args:
            password (str): Modem admin password
            username (str, optional): Login username. Defaults to "admin".
            host (str, optional): Modem IP address. Defaults to "192.168.100.1".
            port (int, optional): HTTPS port. Defaults to 443.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"

        # Authentication state
        self.private_key: Optional[str] = None
        self.uid_cookie: Optional[str] = None
        self.authenticated: bool = False
        # Configure HTTP session for robust communication
        self.session = requests.Session()
        self.session.verify = False  # Modems use self-signed certificates
        self.session.timeout = 15    # Reasonable timeout for local network
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; ArrisModemStatus/1.0)",
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        })

    def _generate_hnap_auth_token(self, soap_action: str, timestamp: int = None) -> str:
        """
        Generate HNAP authentication token using the verified algorithm.
        The HNAP (Home Network Administration Protocol) authentication uses HMAC-SHA256
        with a specific format discovered through reverse engineering:
        1. For unauthenticated requests: use "withoutloginkey" as the HMAC key
        2. For authenticated requests: use the computed private_key as the HMAC key
        3. Message format: timestamp + '"http://purenetworks.com/HNAP1/' + action + '"'
        4. Output format: "HASH TIMESTAMP"
        This algorithm was extracted from the modem's SOAPAction.js file.
        Args:
            soap_action (str): SOAP action name (e.g., "Login", "GetMultipleHNAPs")
            timestamp (int, optional): Unix timestamp in milliseconds. Auto-generated if None.
        Returns:
            str: HNAP_AUTH token in format "HASH TIMESTAMP"
        """
        if timestamp is None:
            # Use same timestamp format as the modem's JavaScript
            timestamp = int(time.time() * 1000) % 2000000000000
        # Select HMAC key based on authentication state
        if not self.private_key:
            # Pre-authentication requests use this hardcoded key
            hmac_key = "withoutloginkey"
        else:
            # Post-authentication requests use the computed private key
            hmac_key = self.private_key
        # Build the message exactly as the modem's JavaScript does
        namespace = "http://purenetworks.com/HNAP1/"
        soap_action_uri = f'"{namespace}{soap_action}"'
        message = str(timestamp) + soap_action_uri
        try:
            # Compute HMAC-SHA256 hash
            auth_hash = hmac.new(
                hmac_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()
            logger.debug(f"Generated HNAP_AUTH for {soap_action}: {auth_hash[:20]}...")
            return f"{auth_hash} {timestamp}"
        except Exception as e:
            logger.error(f"HNAP token generation failed: {e}")
            # Return a fallback token to prevent crashes
            return f"{'0' * 64} {timestamp}"

    def _make_hnap_request(
        self,
        soap_action: str,
        request_body: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Make an HNAP request with proper authentication and headers.
        This method handles the complex header construction required by HNAP,
        including the SOAP action headers, authentication tokens, and cookie
        management for maintaining the session.
        Args:
            soap_action (str): SOAP action name
            request_body (dict): JSON request body
            extra_headers (dict, optional): Additional headers to include
        Returns:
            Optional[str]: Response content or None if request failed
        """
        try:
            # Generate authentication token for this request
            auth_token = self._generate_hnap_auth_token(soap_action)
            # Build headers based on request type
            if soap_action == "Login":
                # Login requests use slightly different headers (from captured traffic)
                headers = {
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/json; charset=UTF-8",
                    "HNAP_AUTH": auth_token,
                    "SOAPAction": f'"http://purenetworks.com/HNAP1/{soap_action}"',
                    "Referer": f"{self.base_url}/Login.html",
                    "X-Requested-With": "XMLHttpRequest"
                }
            else:
                # Post-authentication requests use this header format
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "HNAP_AUTH": auth_token,
                    "SOAPACTION": f'"http://purenetworks.com/HNAP1/{soap_action}"',
                    "Referer": f"{self.base_url}/Cmconnectionstatus.html"
                }
            # Add session cookies for authenticated requests
            if soap_action != "Login" or extra_headers:
                cookies = []
                if self.uid_cookie:
                    cookies.append(f"uid={self.uid_cookie}")
                if self.private_key and self.authenticated:
                    cookies.append(f"PrivateKey={self.private_key}")
                if cookies:
                    headers["Cookie"] = "; ".join(cookies)
                    logger.debug(f"Sending cookies: {headers['Cookie'][:50]}...")
            # Merge any additional headers
            if extra_headers:
                headers.update(extra_headers)
            logger.info(f"📤 Making HNAP request: {soap_action}")
            # Make the HTTP request
            response = self.session.post(
                f"{self.base_url}/HNAP1/",
                json=request_body,
                headers=headers
            )
            logger.info(f"📥 HNAP response: HTTP {response.status_code}, {len(response.text)} chars")
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"HNAP request failed: HTTP {response.status_code}")
                logger.debug(f"Response content: {response.text[:200]}...")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"HNAP request failed for {soap_action}: {e}")
            return None

    def authenticate(self) -> bool:
        """
        Perform HNAP authentication using the discovered challenge-response protocol.
        The Arris HNAP authentication process involves multiple steps:
        1. Request Challenge: Send username to get a challenge string and public key
        2. Compute Private Key: HMAC(PublicKey + Password, Challenge)
        3. Compute Login Password: HMAC(PrivateKey, Challenge)
        4. Send Login: Submit the computed login password
        5. Store Cookies: Save uid and PrivateKey cookies for subsequent requests
        This algorithm was reverse engineered from the modem's Login.js file.
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info("🔐 Starting HNAP authentication...")
            # Step 1: Request authentication challenge
            # This gets us a random challenge string and public key for HMAC computation
            challenge_request = {
                "Login": {
                    "Action": "request",
                    "Username": self.username,
                    "LoginPassword": "",  # Empty for challenge request
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }
            challenge_response = self._make_hnap_request("Login", challenge_request)
            if not challenge_response:
                logger.error("Failed to get authentication challenge")
                return False
            # Parse the challenge response
            try:
                challenge_data = json.loads(challenge_response)
                login_response = challenge_data.get("LoginResponse", {})
                challenge = login_response.get("Challenge")
                public_key = login_response.get("PublicKey")
                uid_cookie = login_response.get("Cookie")
                logger.info(f"📋 Received challenge: {challenge[:20]}...")
                logger.info(f"📋 Received public key: {public_key[:20]}...")
                logger.info(f"📋 Received uid cookie: {uid_cookie}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse challenge response: {e}")
                return False
            if not challenge or not public_key:
                logger.error("Missing Challenge or PublicKey in response")
                return False
            # Store the uid cookie for session management
            self.uid_cookie = uid_cookie
            # Step 2: Compute the private key using the verified algorithm
            # This is the core of the authentication: HMAC(PublicKey + Password, Challenge)
            key_material = public_key + self.password  # String concatenation, not binary
            private_key = hmac.new(
                key_material.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()
            # Step 3: Compute the login password
            # Second HMAC using the private key: HMAC(PrivateKey, Challenge)
            login_password = hmac.new(
                private_key.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()
            # Store private key for subsequent authenticated requests
            self.private_key = private_key
            logger.info(f"🔑 Computed private key: {private_key[:20]}...")
            # Step 4: Send login request with computed credentials
            login_request = {
                "Login": {
                    "Action": "login",
                    "Username": self.username,
                    "LoginPassword": login_password,  # The computed HMAC
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }
            # Include uid cookie in login request
            login_headers = {
                "Cookie": f"uid={uid_cookie}" if uid_cookie else ""
            }
            login_response = self._make_hnap_request("Login", login_request, extra_headers=login_headers)
            if not login_response:
                logger.error("Login request failed")
                return False
            # Step 5: Verify authentication success
            if any(term in login_response.lower() for term in ["success", "ok", "true"]):
                self.authenticated = True
                # Set cookies in session for automatic inclusion in future requests
                if uid_cookie:
                    self.session.cookies.set('uid', uid_cookie, domain=self.host)
                self.session.cookies.set('PrivateKey', private_key, domain=self.host)
                logger.info("🎉 HNAP authentication successful!")
                return True
            else:
                logger.error(f"Authentication failed. Response: {login_response}")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive modem status and channel information.
        This method performs multiple HNAP calls to gather complete modem data:
        1. Startup and connection information
        2. Internet status and device registration
        3. Downstream and upstream channel details
        The requests library handles a known Arris firmware bug where channel
        data responses include malformed HTTP headers that would cause strict
        HTTP parsers to fail.
        Returns:
            dict: Complete modem status with the following structure:
                {
                    "model_name": str,
                    "internet_status": str,
                    "connection_status": str,
                    "system_uptime": str,
                    "mac_address": str,
                    "serial_number": str,
                    "downstream_channels": List[ChannelInfo],
                    "upstream_channels": List[ChannelInfo],
                    "channel_data_available": bool
                }
        Raises:
            RuntimeError: If authentication fails
            requests.RequestException: If network communication fails
        """
        try:
            # Ensure we're authenticated before making data requests
            if not self.authenticated:
                logger.info("Not authenticated, performing login...")
                if not self.authenticate():
                    raise RuntimeError("HNAP authentication failed")
            # Load the connection status page (required by modem firmware)
            # The modem requires this page to be loaded before accepting data requests
            logger.info("📄 Loading connection status page...")
            page_response = self.session.get(
                f"{self.base_url}/Cmconnectionstatus.html",
                headers={"Referer": f"{self.base_url}/Login.html"}
            )
            if page_response.status_code == 200:
                logger.info("✅ Connection status page loaded successfully")
            else:
                logger.warning(f"Connection status page returned {page_response.status_code}")
            # Brief delay to allow page JavaScript initialization
            time.sleep(2)
            # Storage for all response data
            responses = {}
            # Request 1: Get startup sequence and connection info
            logger.info("📊 Requesting startup and connection information...")
            startup_request = {
                "GetMultipleHNAPs": {
                    "GetCustomerStatusStartupSequence": "",
                    "GetCustomerStatusConnectionInfo": ""
                }
            }
            startup_response = self._make_hnap_request("GetMultipleHNAPs", startup_request)
            if startup_response:
                responses["startup_and_connection"] = startup_response
                logger.info("✅ Retrieved startup and connection data")
            # Request 2: Get internet status and device registration
            logger.info("📊 Requesting internet and registration status...")
            internet_request = {
                "GetMultipleHNAPs": {
                    "GetInternetConnectionStatus": "",
                    "GetArrisRegisterInfo": "",
                    "GetArrisRegisterStatus": ""
                }
            }
            internet_response = self._make_hnap_request("GetMultipleHNAPs", internet_request)
            if internet_response:
                responses["internet_and_register"] = internet_response
                logger.info("✅ Retrieved internet and registration data")
            # Request 3: Get channel information (this is where the firmware bug occurs)
            logger.info("📊 Requesting channel information...")
            channel_request = {
                "GetMultipleHNAPs": {
                    "GetCustomerStatusDownstreamChannelInfo": "",
                    "GetCustomerStatusUpstreamChannelInfo": ""
                }
            }
            # The requests library gracefully handles the malformed HTTP headers
            # that Arris firmware includes in channel data responses
            channel_response = self._make_hnap_request("GetMultipleHNAPs", channel_request)
            if channel_response and "CustomerConnDownstreamChannel" in channel_response:
                responses["channel_info"] = channel_response
                # Quick channel count for logging
                channel_count = channel_response.count("|+|") + 1
                logger.info(f"✅ Retrieved channel data! Found ~{channel_count} channels")
            else:
                logger.warning("Failed to retrieve channel information")
            # Parse all responses into structured data
            return self._parse_responses(responses)
        except Exception as e:
            logger.error(f"Failed to retrieve modem status: {e}")
            raise

    def _parse_responses(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse HNAP responses into structured data.
        Takes the raw JSON responses from multiple HNAP calls and extracts
        the relevant information into a clean, structured format.
        Args:
            responses (dict): Dictionary of response_type -> JSON content
        Returns:
            dict: Parsed and structured modem data
        """
        # Initialize with default values
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
        # Process each response type
        for response_type, content in responses.items():
            try:
                json_data = json.loads(content)
                if response_type == "channel_info":
                    channels = self._extract_channels_from_json(json_data)
                    parsed_data["downstream_channels"].extend(channels.get("downstream", []))
                    parsed_data["upstream_channels"].extend(channels.get("upstream", []))
                    logger.info(f"📈 Parsed {len(parsed_data['downstream_channels'])} downstream, "
                              f"{len(parsed_data['upstream_channels'])} upstream channels")
                elif response_type == "startup_and_connection":
                    startup_info = self._extract_startup_info(json_data)
                    parsed_data.update(startup_info)
                elif response_type == "internet_and_register":
                    internet_info = self._extract_internet_info(json_data)
                    parsed_data.update(internet_info)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse {response_type} response as JSON: {e}")
        # Update channel availability status
        if not parsed_data["downstream_channels"] and not parsed_data["upstream_channels"]:
            parsed_data["channel_data_available"] = False
        return parsed_data

    def _extract_channels_from_json(self, json_data: Dict[str, Any]) -> Dict[str, List[ChannelInfo]]:
        """
        Extract channel information from HNAP JSON response.
        Channels are returned in a pipe-delimited format that needs to be
        parsed into structured ChannelInfo objects.
        Args:
            json_data (dict): Parsed JSON response
        Returns:
            dict: Dictionary with "downstream" and "upstream" channel lists
        """
        channels = {"downstream": [], "upstream": []}
        try:
            multiple_hnaps = json_data.get("GetMultipleHNAPsResponse", {})
            # Extract downstream channels
            downstream_response = multiple_hnaps.get("GetCustomerStatusDownstreamChannelInfoResponse", {})
            downstream_raw = downstream_response.get("CustomerConnDownstreamChannel", "")
            if downstream_raw:
                channels["downstream"] = self._parse_pipe_delimited_channels(downstream_raw, "downstream")
            # Extract upstream channels
            upstream_response = multiple_hnaps.get("GetCustomerStatusUpstreamChannelInfoResponse", {})
            upstream_raw = upstream_response.get("CustomerConnUpstreamChannel", "")
            if upstream_raw:
                channels["upstream"] = self._parse_pipe_delimited_channels(upstream_raw, "upstream")
        except Exception as e:
            logger.error(f"Error extracting channel data: {e}")
        return channels

    def _parse_pipe_delimited_channels(self, raw_data: str, channel_type: str) -> List[ChannelInfo]:
        """
        Parse the modem's pipe-delimited channel format into ChannelInfo objects.
        The modem returns channel data in this format:
        "1^Locked^256QAM^5^549000000^ 2.5^39.0^15^0^|+|2^Locked^256QAM^..."
        Fields vary between downstream and upstream channels:
        Downstream: ID^Status^Modulation^?^Frequency^Power^SNR^Corrected^Uncorrected
        Upstream: ID^Status^Modulation^?^?^Frequency^Power
        Args:
            raw_data (str): Pipe-delimited channel data string
            channel_type (str): "downstream" or "upstream"
        Returns:
            List[ChannelInfo]: Parsed channel objects
        """
        channels = []
        try:
            # Split on the channel separator
            channel_entries = raw_data.split("|+|")
            for entry in channel_entries:
                if not entry.strip():
                    continue
                # Split fields by ^ delimiter
                fields = entry.split("^")
                if channel_type == "downstream" and len(fields) >= 6:
                    # Downstream channels have SNR and error counts
                    channel = ChannelInfo(
                        channel_id=fields[0] if len(fields) > 0 else "Unknown",
                        lock_status=fields[1] if len(fields) > 1 else "Unknown",
                        modulation=fields[2] if len(fields) > 2 else "Unknown",
                        # Field 3 appears to be unused/unknown
                        frequency=f"{fields[4]} Hz" if len(fields) > 4 else "Unknown",
                        power=f"{fields[5]} dBmV" if len(fields) > 5 else "Unknown",
                        snr=f"{fields[6]} dB" if len(fields) > 6 else "Unknown",
                        corrected_errors=fields[7] if len(fields) > 7 else None,
                        uncorrected_errors=fields[8] if len(fields) > 8 else None,
                        channel_type=channel_type
                    )
                    channels.append(channel)
                elif channel_type == "upstream" and len(fields) >= 7:
                    # Upstream channels don't have SNR or error counts
                    channel = ChannelInfo(
                        channel_id=fields[0] if len(fields) > 0 else "Unknown",
                        lock_status=fields[1] if len(fields) > 1 else "Unknown",
                        modulation=fields[2] if len(fields) > 2 else "Unknown",
                        # Fields 3-4 appear to be unused/unknown for upstream
                        frequency=f"{fields[5]} Hz" if len(fields) > 5 else "Unknown",
                        power=f"{fields[6]} dBmV" if len(fields) > 6 else "Unknown",
                        snr="N/A",  # Upstream channels don't report SNR
                        channel_type=channel_type
                    )
                    channels.append(channel)
        except Exception as e:
            logger.error(f"Error parsing {channel_type} channels: {e}")
        return channels

    def _extract_startup_info(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract startup and connection information from HNAP response."""
        info = {}
        try:
            multiple_hnaps = json_data.get("GetMultipleHNAPsResponse", {})
            connection_response = multiple_hnaps.get("GetCustomerStatusConnectionInfoResponse", {})
            info["system_uptime"] = connection_response.get("CustomerCurSystemTime", "Unknown")
            info["connection_status"] = connection_response.get("CustomerConnNetworkAccess", "Unknown")
            info["model_name"] = connection_response.get("StatusSoftwareModelName", "Unknown")
        except Exception as e:
            logger.error(f"Error extracting startup info: {e}")
        return info

    def _extract_internet_info(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract internet connection and device information from HNAP response."""
        info = {}
        try:
            multiple_hnaps = json_data.get("GetMultipleHNAPsResponse", {})
            # Internet connection status
            internet_response = multiple_hnaps.get("GetInternetConnectionStatusResponse", {})
            info["internet_status"] = internet_response.get("InternetConnection", "Unknown")
            # Device registration information
            register_response = multiple_hnaps.get("GetArrisRegisterInfoResponse", {})
            if register_response:
                info["mac_address"] = register_response.get("MacAddress", "Unknown")
                info["serial_number"] = register_response.get("SerialNumber", "Unknown")
        except Exception as e:
            logger.error(f"Error extracting internet info: {e}")
        return info

    def close(self) -> None:
        """Close the HTTP session and clean up resources."""
        if self.session:
            self.session.close()
            logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()


# For backwards compatibility and ease of import
__all__ = ["ArrisStatusClient", "ChannelInfo"]
