"""
ArrisStatusClient: A Python client to interact with and query Arris cable modem status.

This module provides a class for logging into an Arris modem's web interface and retrieving
status information such as modem uptime, channel data, and other diagnostic metrics.

VERSION: 2.2.0 - Production Ready with Elegant Fallback
- Complete HNAP authentication with dual cookie support
- Graceful handling of non-standard HTTP responses for channel data
- Automatic fallback to raw socket for problematic responses

Typical usage example:
    client = ArrisStatusClient(password="your_password")
    status = await client.get_status()
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
import socket
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

    This version implements complete HNAP authentication and gracefully handles
    non-standard HTTP responses that some Arris modems return for channel data.

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
        self.uid_cookie = None
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
            cookie_jar=aiohttp.CookieJar(),
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
        logger.info(f"Initialized session for {self.base_url}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup aiohttp session"""
        if self.session:
            await self.session.close()
            logger.debug("Session closed")

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

            logger.debug(f"Generated HNAP auth for {soap_action}: {auth_hash[:20]}...")
            return f"{auth_hash} {timestamp}"

        except Exception as e:
            logger.error(f"HNAP token generation failed: {e}")
            return f"{'0' * 64} {timestamp}"

    async def _make_hnap_request(self, soap_action: str, request_body: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Make authenticated HNAP request with proper cookie handling.

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
                    "Referer": f"{self.base_url}/Cmconnectionstatus.html",
                    "Origin": f"https://{self.host}",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "same-origin"
                }

            # Build complete cookie header with both cookies
            if soap_action != "Login" or extra_headers:
                cookies = []

                if self.uid_cookie:
                    cookies.append(f"uid={self.uid_cookie}")

                if self.private_key and self.authenticated:
                    cookies.append(f"PrivateKey={self.private_key}")

                for cookie in self.session.cookie_jar:
                    cookie_str = f"{cookie.key}={cookie.value}"
                    if cookie_str not in cookies:
                        cookies.append(cookie_str)

                if cookies:
                    headers["Cookie"] = "; ".join(cookies)
                    logger.debug(f"Sending cookies: {headers['Cookie'][:50]}...")

            if extra_headers:
                headers.update(extra_headers)

            # Convert request body to JSON string
            request_json = json.dumps(request_body)
            headers["Content-Length"] = str(len(request_json.encode('utf-8')))

            logger.info(f"Making HNAP request: {soap_action}")
            logger.debug(f"Request headers: {headers}")

            async with self.session.post(
                f"{self.base_url}/HNAP1/",
                data=request_json,
                headers=headers
            ) as response:
                content = await response.text()

                logger.info(f"HNAP response: HTTP {response.status}, {len(content)} chars")

                if response.status == 200:
                    return content
                else:
                    logger.error(f"HNAP request failed: HTTP {response.status}")
                    logger.debug(f"Response content: {content[:200]}...")
                    return None

        except aiohttp.ClientResponseError as e:
            logger.warning(f"HNAP request got malformed response: {e}")
            raise
        except Exception as e:
            logger.error(f"HNAP request error for {soap_action}: {e}")
            return None

    async def _make_channel_request_raw_socket(self, request_body: Dict[str, Any]) -> Optional[str]:
        """
        Make channel data request using raw socket to bypass strict HTTP parsing.

        Args:
            request_body (dict): JSON request body

        Returns:
            Optional[str]: Response content or None if failed
        """
        try:
            logger.info("Using raw socket method for channel data...")

            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)

            # Wrap with SSL
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            ssl_sock = context.wrap_socket(sock, server_hostname=self.host)
            ssl_sock.connect((self.host, self.port))

            # Build HTTP request
            auth_token = self._generate_hnap_auth_token("GetMultipleHNAPs")
            body = json.dumps(request_body)

            request = (
                f"POST /HNAP1/ HTTP/1.1\r\n"
                f"Host: {self.host}\r\n"
                f"Accept: application/json\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Cookie: uid={self.uid_cookie}; PrivateKey={self.private_key}\r\n"
                f"HNAP_AUTH: {auth_token}\r\n"
                f'SOAPACTION: "http://purenetworks.com/HNAP1/GetMultipleHNAPs"\r\n'
                f"Referer: {self.base_url}/Cmconnectionstatus.html\r\n"
                f"Connection: close\r\n"
                f"\r\n"
                f"{body}"
            )

            # Send request
            ssl_sock.send(request.encode('utf-8'))

            # Read response
            response_data = b""
            while True:
                chunk = ssl_sock.recv(8192)
                if not chunk:
                    break
                response_data += chunk
                # Check for end of JSON response
                if b'"GetMultipleHNAPsResult": "OK" } }' in response_data:
                    break

            ssl_sock.close()
            sock.close()

            # Extract JSON from response
            response_text = response_data.decode('utf-8', errors='ignore')
            json_start = response_text.find('{ "GetMultipleHNAPsResponse"')

            if json_start >= 0:
                json_data = response_text[json_start:]

                # Find proper JSON end
                brace_count = 0
                json_end = 0
                for i, char in enumerate(json_data):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > 0:
                    clean_json = json_data[:json_end]

                    # Validate it's proper JSON
                    json.loads(clean_json)

                    logger.info("✅ Successfully extracted channel data via raw socket!")
                    return clean_json

            logger.warning("Could not find valid JSON in raw response")
            return None

        except Exception as e:
            logger.error(f"Raw socket method failed: {e}")
            return None

    async def _authenticate(self) -> bool:
        """
        Perform HNAP login authentication with complete cookie setup.

        Returns:
            bool: True if authentication successful
        """
        try:
            logger.info("Starting authentication process...")

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
                logger.error("Failed to get challenge response")
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

                logger.info(f"Got challenge: {challenge[:20]}...")
                logger.info(f"Got public key: {public_key[:20]}...")
                logger.info(f"Got uid cookie: {uid_cookie}")

            except json.JSONDecodeError:
                logger.error("Failed to parse challenge response")
                return False

            if not challenge or not public_key:
                logger.error("Missing Challenge or PublicKey in response")
                return False

            # Store uid cookie
            self.uid_cookie = uid_cookie

            # Step 2: Compute authentication hashes using VERIFIED algorithm
            key1 = public_key + self.password
            message1 = challenge

            private_key = hmac.new(
                key1.encode('utf-8'),
                message1.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()

            login_password = hmac.new(
                private_key.encode('utf-8'),
                challenge.encode('utf-8'),
                hashlib.sha256
            ).hexdigest().upper()

            # Store private key for subsequent requests
            self.private_key = private_key
            logger.info(f"Computed private key: {private_key[:20]}...")

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
                logger.error("Login request failed")
                return False

            # Check for success
            if any(term in login_response.lower() for term in ["success", "ok", "true"]):
                self.authenticated = True

                # Set both cookies in the session cookie jar
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
                    logger.info("✅ Set uid cookie in jar")

                # Add PrivateKey cookie
                pk_simple = SimpleCookie()
                pk_simple['PrivateKey'] = private_key
                pk_simple['PrivateKey']['path'] = '/'
                pk_simple['PrivateKey']['secure'] = True
                self.session.cookie_jar.update_cookies(pk_simple, url)
                logger.info("✅ Set PrivateKey cookie in jar")

                logger.info("✅ Authentication successful with both cookies set!")
                return True
            else:
                logger.error(f"Login failed: {login_response}")
                return False

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _get_channel_data(self) -> Dict[str, Any]:
        """
        Get comprehensive channel data from modem.

        Returns:
            Dict containing parsed channel information and modem status
        """
        if not self.authenticated:
            logger.info("Not authenticated, performing login...")
            if not await self._authenticate():
                raise RuntimeError("Authentication failed")

        # Load the connection status page first (required by modem)
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

            # Wait for page to initialize
            await asyncio.sleep(2.0)

        except Exception as e:
            logger.warning(f"Failed to load connection status page: {e}")

        # Make the three key HNAP calls
        responses = {}

        # Call 1: Startup and Connection Info
        logger.info("📊 Requesting startup and connection info...")
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
        logger.info("📊 Requesting internet and register status...")
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

        # Call 3: Channel Information
        logger.info("📊 Requesting channel information...")
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
                logger.info("✅ Got channel information!")

                # Quick validation
                if "CustomerConnDownstreamChannel" in channel_response:
                    logger.info("🎉 SUCCESS! Got downstream channel data!")
                    channel_count = channel_response.count("|+|") + 1
                    logger.info(f"📊 Found approximately {channel_count} channels")

        except aiohttp.ClientResponseError as e:
            # Handle non-standard HTTP responses
            if "Invalid header" in str(e) or "malformed" in str(e).lower():
                logger.warning("Channel data response has non-standard headers, using fallback method...")

                # Try raw socket method
                channel_response = await self._make_channel_request_raw_socket(channel_request)
                if channel_response:
                    responses["channel_info"] = channel_response
                    logger.info("✅ Got channel data via raw socket method!")
            else:
                logger.error(f"Channel data request failed: {e}")

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
            "upstream_channels": [],
            "channel_data_available": True
        }

        for response_type, content in responses.items():
            try:
                json_data = json.loads(content)
                logger.debug(f"Parsing {response_type} response")

                if response_type == "channel_info":
                    channels = self._extract_channels_from_json(json_data)
                    parsed_data["downstream_channels"].extend(channels.get("downstream", []))
                    parsed_data["upstream_channels"].extend(channels.get("upstream", []))
                    logger.info(f"Parsed {len(parsed_data['downstream_channels'])} downstream, {len(parsed_data['upstream_channels'])} upstream channels")

                elif response_type == "startup_and_connection":
                    startup_info = self._extract_startup_info(json_data)
                    parsed_data.update(startup_info)

                elif response_type == "internet_and_register":
                    internet_info = self._extract_internet_info(json_data)
                    parsed_data.update(internet_info)

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse {response_type} as JSON")

        # Check if channel data was retrieved
        if not parsed_data["downstream_channels"] and not parsed_data["upstream_channels"]:
            parsed_data["channel_data_available"] = False

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

                if channel_type == "downstream" and len(fields) >= 6:
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

                elif channel_type == "upstream" and len(fields) >= 7:
                    # Upstream format is slightly different
                    channel = ChannelInfo(
                        channel_id=fields[0] if len(fields) > 0 else "Unknown",
                        lock_status=fields[1] if len(fields) > 1 else "Unknown",
                        modulation=fields[2] if len(fields) > 2 else "Unknown",
                        frequency=f"{fields[5]} Hz" if len(fields) > 5 else "Unknown",
                        power=f"{fields[6]} dBmV" if len(fields) > 6 else "Unknown",
                        snr="N/A",  # Upstream doesn't have SNR
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

            # Extract device info
            register_response = multiple_hnaps.get("GetArrisRegisterInfoResponse", {})
            if register_response:
                info["mac_address"] = register_response.get("MacAddress", "Unknown")
                info["serial_number"] = register_response.get("SerialNumber", "Unknown")

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
