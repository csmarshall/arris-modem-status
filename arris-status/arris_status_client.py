"""
ArrisStatusClient: A Python client to interact with and query Arris cable modem status.

This module provides a class for logging into an Arris modem's web interface and retrieving
status information such as modem uptime, channel data, and other diagnostic metrics.

Typical usage example:
    client = ArrisStatusClient(password="your_password")
    status = client.get_status()
    print(status)
"""

import hashlib
import hmac
import logging
import time
import xml.etree.ElementTree as ET
from base64 import encodebytes
from datetime import datetime
from typing import Dict, Optional

import requests

logger = logging.getLogger("arris-client")


class ArrisStatusClient:
    """
    A client to query status information from an Arris modem.

    Attributes:
        host (str): Hostname or IP of the modem.
        username (str): Username for modem login.
        password (str): Password for modem login.
    """

    def __init__(self, password: str, username: str = "admin", host: str = "192.168.100.1"):
        """
        Initialize the client with modem access credentials.

        Args:
            password (str): Password for the modem.
            username (str, optional): Username for login. Defaults to "admin".
            host (str, optional): Modem hostname or IP address. Defaults to "192.168.100.1".
        """
        self.host = host
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.hnap_auth = ""
        self.private_key = ""

    def _hnap_request(self, action: str, body: str, auth: bool = False) -> str:
        """
        Send an HNAP SOAP request to the modem.

        Args:
            action (str): SOAPAction to perform.
            body (str): XML body content.
            auth (bool): Whether authentication headers are required.

        Returns:
            str: Response text from the modem.
        """
        url = f"https://{self.host}/HNAP1/"
        headers = {
            "SOAPAction": f'"http://purenetworks.com/HNAP1/{action}"',
            "Content-Type": "text/xml; charset=utf-8",
        }
        if auth:
            timestamp = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
            auth_code = hmac.new(
                self.private_key.encode(),
                f'{timestamp}"http://purenetworks.com/HNAP1/{action}"'.encode(),
                hashlib.sha256,
            ).hexdigest().upper()
            self.hnap_auth = f"{auth_code} {self.private_key}"
            headers.update({
                "HNAP_AUTH": self.hnap_auth,
                "Cookie": "uid=admin",
                "Date": timestamp,
            })
        response = self.session.post(url, headers=headers, data=body, verify=False)
        response.raise_for_status()
        return response.text

    def login(self) -> bool:
        """
        Perform login handshake and authentication.

        Returns:
            bool: True if login is successful.

        Raises:
            ValueError: If response format is unexpected.
        """
        body1 = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <Login xmlns="http://purenetworks.com/HNAP1/">
                  <Action>request</Action>
                  <Username>{self.username}</Username>
                  <LoginPassword></LoginPassword>
                  <Captcha></Captcha>
                </Login>
              </soap:Body>
            </soap:Envelope>"""

        response1 = self._hnap_request("Login", body1)

        try:
            challenge = self._parse_xml_value(response1, "Challenge")
            public_key = self._parse_xml_value(response1, "PublicKey")
            cookie = self._parse_xml_value(response1, "Cookie")
        except Exception as e:
            logger.error(f"Failed to parse tag Challenge: {e}")
            raise

        self.private_key = hmac.new(
            public_key.encode(),
            challenge.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

        login_password = hmac.new(
            self.private_key.encode(),
            self.password.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

        body2 = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <Login xmlns="http://purenetworks.com/HNAP1/">
                  <Action>login</Action>
                  <Username>{self.username}</Username>
                  <LoginPassword>{login_password}</LoginPassword>
                  <Captcha></Captcha>
                </Login>
              </soap:Body>
            </soap:Envelope>"""

        response2 = self._hnap_request("Login", body2, auth=True)
        result = self._parse_xml_value(response2, "LoginResult")
        return result == "success"

    def get_status(self) -> Dict:
        """
        Retrieve modem status data.

        Returns:
            dict: Dictionary of modem status fields.

        Raises:
            RuntimeError: If login fails.
        """
        if not self.login():
            raise RuntimeError("Login failed")

        body = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <GetMultipleHNAPs xmlns="http://purenetworks.com/HNAP1/">
                  <GetHNAPs>
                    <string>GetSystemStatus</string>
                    <string>GetStatus</string>
                  </GetHNAPs>
                </GetMultipleHNAPs>
              </soap:Body>
            </soap:Envelope>"""

        response = self._hnap_request("GetMultipleHNAPs", body, auth=True)
        return self._parse_status_xml(response)

    def _parse_xml_value(self, xml: str, tag: str) -> str:
        """
        Extract a value from a given XML string.

        Args:
            xml (str): XML content.
            tag (str): Tag name to search.

        Returns:
            str: Value of the tag.
        """
        root = ET.fromstring(xml)
        return root.find(".//" + tag).text

    def _parse_status_xml(self, xml: str) -> Dict:
        """
        Parse the modem status XML into a Python dictionary.

        Args:
            xml (str): XML status response.

        Returns:
            dict: Parsed status values.
        """
        root = ET.fromstring(xml)
        status = {}
        for elem in root.iter():
            if elem.tag.endswith("Status") or elem.tag.endswith("Uptime") or elem.tag.endswith("Temperature"):
                status[elem.tag] = elem.text
        return status
