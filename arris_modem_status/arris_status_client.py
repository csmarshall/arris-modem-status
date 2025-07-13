"""
ArrisStatusClient: A Python client to interact with and query Arris cable modem status.

This module provides a class for logging into an Arris modem's web interface and retrieving
status information such as modem uptime, channel data, and other diagnostic metrics.

VERSION: 2.0.0 - Complete HNAP Authentication Implementation
- Implements verified JavaScript authentication algorithm
- Supports full channel data extraction
- Ready for PyPI publication and Netdata integration

Typical usage example:
    client = ArrisStatusClient(password="your_password")
    status = client.get_status()
    print(status)

The client can also be used from the command line with the CLI script.

Usage (command line):
    python -m arris_modem_status.cli --password YOUR_PASSWORD [--host 192.168.100.1] [--port 443]
"""

import hashlib
import hmac
import logging
import time
import urllib3
import json
import asyncio
import aiohttp
import ssl
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("arris-client")


@dataclass
class ChannelInfo:
    """Channel information extracted from HNAP response"""
    channel_id: str
    frequency: str
    power: str
    snr: str
    modulation: str
    lock_status: str
    corrected_errors: Optional[str] = None
    uncorrected_errors: Optional[str] = None
    channel_type: str = "unknown"


class ArrisStatusClient:
    """
    A client to query status information from an Arris modem.

    This version implements the complete HNAP authentication algorithm discovered
    through JavaScript reverse engineering, providing full access to modem channel
    data and diagnostics.

    Attributes:
        host (str): Hostname or IP of the modem.
        port (int): Port to connect to.
        username (str): Username for modem login.
        password (str): Password for modem login.
    """

    def __init__(self, password: str, username: str = "admin", host: str = "192.168.100.1", port: int = 443):
        """
        Initialize the client with modem access credentials.

        Args:
            password (str): Password for the modem.
            username (str, optional): Username for login. Defaults to "admin".
            host (str, optional): Modem hostname or IP address. Defaults to "192.168.100.1".
            port (int, optional): Port number to use for HTTPS connection. Defaults to 443.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_url = f"https://{host}:{port}"

        # Authentication state
        self.private_key = None
        self.authenticated = False
        self.session = None

    async def __aenter__(self):
        """Initialize aiohttp session for async operations"""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        connector = aiohttp.TCPConnector(
            limit=10,
            ssl=ssl_context,
            keepalive_timeout=30
        )

        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20),
            connector=connector,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup aiohttp session"""
        if self.session:
            await self.session.close()

    def _generate_hnap_auth_token(self, soap_action: str, timestamp: int = None) -> str:
        """
        Generate HNAP authentication token using verified algorithm.

        Args:
            soap_action (str): SOAP action name (e.g., "Login")
            timestamp (int, optional): Unix timestamp in milliseconds

        Returns:
            str: HNAP_AUTH token in format "HASH TIMESTAMP"
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000) % 2000000000000

        # Use "withoutloginkey" for unauthenticated requests, private_key for authenticated
        if not self.private_key:
            private_key = "withoutloginkey"
        else:
            private_key = self.private_key

        # Exact format from SOAPAction.js
        namespace = "http://purenetworks.com/HNAP1/"
        soap_action_uri = f'"{namespace}{soap_action}"'
        message = str(timestamp) + soap_action_uri

        try:
            auth_hash = hmac.new(
                private_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()

            return f"{auth_hash} {timestamp}"

        except Exception as e:
            logger.error(f"HNAP token generation failed: {e}")
            return f"{'0' * 64} {timestamp}"

    async def _make_hnap_request(self, soap_action: str, request_body: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Make authenticated HNAP request.

        Args:
            soap_action (str): SOAP action name
            request_body (dict): JSON request body
            extra_headers (dict, optional): Additional headers to include

        Returns:
            Optional[str]: Response content or None if failed
        """
        try:
            auth_token = self._generate_hnap_auth_token(soap_action)

            # Headers based on captured browser requests
            if soap_action == "Login":
                headers = {
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "Content-Type": "application/json; charset=UTF-8",
                    "HNAP_AUTH": auth_token,
                    "SOAPAction": f'"http://purenetworks.com/HNAP1/{soap_action}"',
                    "Referer": f"{self.base_url}/Login.html",
                    "X-Requested-With": "XMLHttpRequest"
                }
            else:
                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "HNAP_AUTH": auth_token,
                    "SOAPACTION": f'"http://purenetworks.com/HNAP1/{soap_action}"',
                    "Referer": f"{self.base_url}/Cmconnectionstatus.html"
                }
            
            # CRITICAL: Manually build cookie header from jar
            if soap_action != "Login" or extra_headers:  # Don't add cookies for initial login challenge
                cookies = []
                for cookie in self.session.cookie_jar:
                    cookies.append(f"{cookie.key}={cookie.value}")
                
                if cookies:
                    headers["Cookie"] = "; ".join(cookies)
                    logger.debug(f"Sending cookies: {headers['Cookie']}")
            
            # Add any extra headers
            if extra_headers:
                headers.update(extra_headers)

            # Convert request body to JSON string
            request_json = json.dumps(request_body)
            
            async with self.session.post(
                f"{self.base_url}/HNAP1/",
                data=request_json,  # Use data instead of json parameter
                headers=headers
            ) as response:

                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"HNAP request failed: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"HNAP request error for {soap_action}: {e}")
            return None

    async def _authenticate(self) -> bool:
        """
        Perform HNAP login authentication using verified algorithm.

        Returns:
            bool: True if authentication successful
        """
        try:
            # Step 1: Request login challenge
            challenge_request = {
                "Login": {
                    "Action": "request",
                    "Username": self.username,
                    "LoginPassword": "",
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }

            challenge_response = await self._make_hnap_request("Login", challenge_request)
            if not challenge_response:
                return False

            # Parse challenge response
            challenge = None
            public_key = None
            uid_cookie = None
            
            try:
                challenge_data = json.loads(challenge_response)
                login_response = challenge_data.get("LoginResponse", {})
                challenge = login_response.get("Challenge")
                public_key = login_response.get("PublicKey")
                uid_cookie = login_response.get("Cookie")
                
            except json.JSONDecodeError:
                logger.error("Failed to parse challenge response")
                return False
            
            if not challenge or not public_key:
                logger.error("Missing Challenge or PublicKey in response")
                return False
            
            # Step 2: Compute authentication hashes using VERIFIED algorithm
            # From Login.js: PrivateKey = hex_hmac_sha256(obj.PublicKey + ifLogin_Password, obj.Challenge);
            key1 = public_key + self.password
            message1 = challenge
            
            private_key = hmac.new(
                key1.encode('utf-8'),
                message1.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()
            
            # From Login.js: Login_Passwd = hex_hmac_sha256(PrivateKey, obj.Challenge);
            login_password = hmac.new(
                private_key.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()
            
            # Store private key for subsequent requests
            self.private_key = private_key
            
            # Step 3: Send login with computed hash
            login_request = {
                "Login": {
                    "Action": "login",
                    "Username": self.username,
                    "LoginPassword": login_password,
                    "Captcha": "",
                    "PrivateLogin": "LoginPassword"
                }
            }
            
            # Add uid cookie for login request
            login_headers = {
                "Cookie": f"uid={uid_cookie}" if uid_cookie else ""
            }
            
            login_response = await self._make_hnap_request("Login", login_request, extra_headers=login_headers)
            if not login_response:
                return False
            
            # Check for success (various possible response formats)
            if any(term in login_response.lower() for term in ["success", "ok", "true"]):
                self.authenticated = True
                
                # CRITICAL: Set both cookies in the session
                from http.cookies import SimpleCookie
                from yarl import URL
                url = URL(self.base_url)
                
                # Add uid cookie
                if uid_cookie:
                    uid_simple = SimpleCookie()
                    uid_simple['uid'] = uid_cookie
                    uid_simple['uid']['path'] = '/'
                    uid_simple['uid']['secure'] = True
                    self.session.cookie_jar.update_cookies(uid_simple, url)
                
                # Add PrivateKey cookie (same as computed private_key!)
                pk_simple = SimpleCookie()
                pk_simple['PrivateKey'] = private_key
                pk_simple['PrivateKey']['path'] = '/'
                pk_simple['PrivateKey']['secure'] = True
                self.session.cookie_jar.update_cookies(pk_simple, url)
                
                logger.info("Authentication successful with both cookies set")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    async def _get_channel_data(self) -> Dict[str, Any]:
        """
        Get comprehensive channel data from modem.
        
        Returns:
            Dict containing parsed channel information and modem status
        """
        if not self.authenticated:
            if not await self._authenticate():
                raise RuntimeError("Authentication failed")
        
        # CRITICAL: Load the connection status page first (required by modem!)
        logger.info("Loading connection status page...")
        try:
            page_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Referer": f"{self.base_url}/Login.html",
                "Upgrade-Insecure-Requests": "1"
            }
            
            async with self.session.get(f"{self.base_url}/Cmconnectionstatus.html", headers=page_headers) as response:
                if response.status != 200:
                    logger.warning(f"Connection status page returned {response.status}")
                else:
                    logger.info("✅ Connection status page loaded successfully")
            
            # Wait for page to initialize (as observed in browser)
            await asyncio.sleep(2.0)
            
        except Exception as e:
            logger.warning(f"Failed to load connection status page: {e}")
        
        # Make the three key HNAP calls discovered from browser capture
        responses = {}
        
        # Call 1: Startup and Connection Info
        startup_request = {
            "GetMultipleHNAPs": {
                "GetCustomerStatusStartupSequence": "",
                "GetCustomerStatusConnectionInfo": ""
            }
        }
        startup_response = await self._make_hnap_request("GetMultipleHNAPs", startup_request)
        if startup_response:
            responses["startup_and_connection"] = startup_response
            logger.info("✅ Got startup and connection info")
        
        # Call 2: Internet and Register Status
        internet_request = {
            "GetMultipleHNAPs": {
                "GetInternetConnectionStatus": "",
                "GetArrisRegisterInfo": "",
                "GetArrisRegisterStatus": ""
            }
        }
        internet_response = await self._make_hnap_request("GetMultipleHNAPs", internet_request)
        if internet_response:
            responses["internet_and_register"] = internet_response
            logger.info("✅ Got internet and register status")
        
        # Call 3: Channel Information (most important)
        channel_request = {
            "GetMultipleHNAPs": {
                "GetCustomerStatusDownstreamChannelInfo": "",
                "GetCustomerStatusUpstreamChannelInfo": ""
            }
        }
        
        try:
            channel_response = await self._make_hnap_request("GetMultipleHNAPs", channel_request)
            if channel_response:
                responses["channel_info"] = channel_response
                logger.info("✅ Got channel information")
        except aiohttp.ClientResponseError as e:
            logger.warning(f"Channel data request got malformed response: {e}")
            logger.info("Note: Some modems return invalid HTTP headers for channel data")
        except Exception as e:
            logger.warning(f"Channel data request failed: {e}")
        
        return self._parse_responses(responses)

    def _parse_responses(self, responses: Dict[str, str]) -> Dict[str, Any]:
        """Parse HNAP responses into structured data"""
        parsed_data = {
            "model_name": "S34",
            "firmware_version": "Unknown",
            "system_uptime": "Unknown",
            "internet_status": "Unknown",
            "connection_status": "Unknown",
            "downstream_channels": [],
            "upstream_channels": []
        }
        
        for response_type, content in responses.items():
            try:
                json_data = json.loads(content)
                
                if response_type == "channel_info":
                    channels = self._extract_channels_from_json(json_data)
                    parsed_data["downstream_channels"].extend(channels.get("downstream", []))
                    parsed_data["upstream_channels"].extend(channels.get("upstream", []))
                    
                elif response_type == "startup_and_connection":
                    startup_info = self._extract_startup_info(json_data)
                    parsed_data.update(startup_info)
                    
                elif response_type == "internet_and_register":
                    internet_info = self._extract_internet_info(json_data)
                    parsed_data.update(internet_info)
                    
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse {response_type} as JSON")
        
        return parsed_data

    def _extract_channels_from_json(self, json_data: Dict[str, Any]) -> Dict[str, List[ChannelInfo]]:
        """Extract channel information from pipe-delimited format"""
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
        """Parse the modem's pipe-delimited channel format"""
        channels = []
        
        try:
            # Format: field1^field2^field3^...^fieldN|+|field1^field2^...
            channel_entries = raw_data.split("|+|")
            
            for entry in channel_entries:
                if not entry.strip():
                    continue
                
                fields = entry.split("^")
                
                if len(fields) >= 6:
                    channel = ChannelInfo(
                        channel_id=fields[0] if len(fields) > 0 else "Unknown",
                        lock_status=fields[1] if len(fields) > 1 else "Unknown",
                        modulation=fields[2] if len(fields) > 2 else "Unknown",
                        frequency=f"{fields[4]} Hz" if len(fields) > 4 else "Unknown",
                        power=f"{fields[5]} dBmV" if len(fields) > 5 else "Unknown",
                        snr=f"{fields[6]} dB" if len(fields) > 6 else "Unknown",
                        corrected_errors=fields[7] if len(fields) > 7 else None,
                        uncorrected_errors=fields[8] if len(fields) > 8 else None,
                        channel_type=channel_type
                    )
                    channels.append(channel)
                    
        except Exception as e:
            logger.error(f"Error parsing {channel_type} channels: {e}")
        
        return channels

    def _extract_startup_info(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract startup and connection info"""
        info = {}
        
        try:
            multiple_hnaps = json_data.get("GetMultipleHNAPsResponse", {})
            
            # Extract connection info
            connection_response = multiple_hnaps.get("GetCustomerStatusConnectionInfoResponse", {})
            info["system_uptime"] = connection_response.get("CustomerCurSystemTime", "Unknown")
            info["connection_status"] = connection_response.get("CustomerConnNetworkAccess", "Unknown")
            info["model_name"] = connection_response.get("StatusSoftwareModelName", "S34")
            
        except Exception as e:
            logger.error(f"Error extracting startup info: {e}")
        
        return info

    def _extract_internet_info(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract internet status"""
        info = {}
        
        try:
            multiple_hnaps = json_data.get("GetMultipleHNAPsResponse", {})
            
            # Extract internet connection status
            internet_response = multiple_hnaps.get("GetInternetConnectionStatusResponse", {})
            info["internet_status"] = internet_response.get("InternetConnection", "Unknown")
            
        except Exception as e:
            logger.error(f"Error extracting internet info: {e}")
        
        return info

    async def get_status(self) -> Dict:
        """
        Retrieve comprehensive modem status data.

        Returns:
            dict: Dictionary containing modem status, channel data, and diagnostics.
            
        Raises:
            RuntimeError: If authentication fails.
        """
        async with self:
            return await self._get_channel_data()

    def get_status_sync(self) -> Dict:
        """
        Synchronous version of get_status() for backwards compatibility.
        
        Returns:
            dict: Dictionary containing modem status and channel data.
        """
        return asyncio.run(self.get_status())

    # Legacy methods for backwards compatibility
    def login(self) -> bool:
        """Legacy login method - now handled automatically in get_status()"""
        async def _login():
            async with self:
                return await self._authenticate()
        return asyncio.run(_login())

    def _parse_xml_value(self, xml: str, tag: str) -> str:
        """Legacy method - kept for compatibility but not used in new implementation"""
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml)
            return root.find(".//" + tag).text
        except:
            return "Unknown"

    def _parse_status_xml(self, xml: str) -> Dict:
        """Legacy method - kept for compatibility but not used in new implementation"""
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml)
            status = {}
            for elem in root.iter():
                if elem.tag.endswith("Status") or elem.tag.endswith("Uptime") or elem.tag.endswith("Temperature"):
                    status[elem.tag] = elem.text
            return status
        except:
            return {}