import requests
import logging
import hashlib
import hmac
import base64
import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any

logger = logging.getLogger("arris-client")

class ArrisStatusClient:
    def __init__(self, password: str, host: str = "192.168.100.1"):
        self.password = password
        self.host = host
        self.base_url = f"https://{host}/HNAP1/"
        self.cookies = {}
        self.headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"http://purenetworks.com/HNAP1/Login"'
        }
        self.private_key = None
        self.login_token = None

    def _parse_xml_value(self, xml: str, tag: str) -> str:
        try:
            root = ET.fromstring(xml)
            return root.find(".//" + tag).text
        except Exception as e:
            logger.error(f"Failed to parse tag {tag}: {e}")
            raise

    def _hnap_auth(self, action: str, timestamp: str) -> str:
        data = f"{timestamp}" + action
        digest = hmac.new(
            key=self.private_key.encode("utf-8"),
            msg=data.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest().upper()
        return f"{digest} {timestamp}"

    def login(self) -> bool:
        logger.info("Attempting to login...")
        # Step 1: Get Challenge, Cookie, PublicKey
        login_payload = (
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
            "<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
            "xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" "
            "xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">"
            "<soap:Body>"
            "<Login xmlns=\"http://purenetworks.com/HNAP1/\">"
            "<Action>request</Action>"
            "<Username>admin</Username>"
            "<LoginPassword></LoginPassword>"
            "<Captcha></Captcha>"
            "</Login>"
            "</soap:Body>"
            "</soap:Envelope>"
        )

        try:
            res1 = requests.post(self.base_url, headers=self.headers, data=login_payload, verify=False)
            if res1.headers.get("Content-Type") != "text/xml; charset=utf-8":
                logger.error("Unexpected content-type, got: %s", res1.headers.get("Content-Type"))
                logger.debug("Body: %s", res1.text)
                return False

            challenge = self._parse_xml_value(res1.text, "Challenge")
            public_key = self._parse_xml_value(res1.text, "PublicKey")
            cookie = res1.cookies.get("uid")
            self.cookies["uid"] = cookie

            self.private_key = hmac.new(
                key=public_key.encode("utf-8"),
                msg=challenge.encode("utf-8"),
                digestmod=hashlib.sha256
            ).hexdigest().upper()

            login_password = hmac.new(
                key=self.private_key.encode("utf-8"),
                msg=self.password.encode("utf-8"),
                digestmod=hashlib.sha256
            ).hexdigest().upper()
        except Exception as e:
            logger.error("Login phase 1 failed: %s", e)
            return False

        # Step 2: Send login
        timestamp = str(int(time.time()))
        self.headers.update({
            "Cookie": f"uid={cookie}",
            "SOAPAction": '"http://purenetworks.com/HNAP1/Login"',
            "HNAP_AUTH": self._hnap_auth("http://purenetworks.com/HNAP1/Login", timestamp)
        })

        login_payload2 = (
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
            "<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
            "xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" "
            "xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">"
            "<soap:Body>"
            "<Login xmlns=\"http://purenetworks.com/HNAP1/\">"
            "<Action>login</Action>"
            "<Username>admin</Username>"
            f"<LoginPassword>{login_password}</LoginPassword>"
            f"<Captcha></Captcha>"
            f"</Login>"
            "</soap:Body>"
            "</soap:Envelope>"
        )

        try:
            res2 = requests.post(self.base_url, headers=self.headers, data=login_payload2, cookies=self.cookies, verify=False)
            self.login_token = self._parse_xml_value(res2.text, "LoginResult")
            return self.login_token == "success"
        except Exception as e:
            logger.error("Login phase 2 failed: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        timestamp = str(int(time.time()))
        action = "http://purenetworks.com/HNAP1/GetMultipleHNAPs"
        self.headers["SOAPAction"] = f'"{action}"'
        self.headers["HNAP_AUTH"] = self._hnap_auth(action, timestamp)

        status_payload = (
            "<?xml version=\"1.0\" encoding=\"utf-8\"?>"
            "<soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" "
            "xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" "
            "xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">"
            "<soap:Body>"
            "<GetMultipleHNAPs xmlns=\"http://purenetworks.com/HNAP1/\">"
            "<GetHNAPs>"
            "<string>GetStatus</string>"
            "<string>GetConnectionStatus</string>"
            "<string>GetSystemStatus</string>"
            "<string>GetConfigInfo</string>"
            "<string>GetCMStatus</string>"
            "</GetHNAPs>"
            "</GetMultipleHNAPs>"
            "</soap:Body>"
            "</soap:Envelope>"
        )

        try:
            response = requests.post(self.base_url, headers=self.headers, data=status_payload, cookies=self.cookies, verify=False)
            return self._parse_status_response(response.text)
        except Exception as e:
            logger.error("Failed to retrieve status: %s", e)
            return {}

    def _parse_status_response(self, xml: str) -> Dict[str, Any]:
        root = ET.fromstring(xml)
        status_data = {}
        for elem in root.iter():
            if elem.text and elem.tag.endswith("Result"):
                continue  # Skip Result tags
            if elem.text and elem.text.strip():
                tag = re.sub(r"^.*\}", "", elem.tag)  # strip namespace
                status_data[tag] = elem.text.strip()
        return status_data
