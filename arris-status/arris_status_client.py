import requests
import logging
import hashlib
import hmac
import base64
import xml.etree.ElementTree as ET
from datetime import datetime

logger = logging.getLogger("arris-client")

class ArrisStatusClient:
    def __init__(self, host="192.168.100.1", username="admin", password=""):
        self.host = host
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.url = f"https://{host}/HNAP1/"
        self.soap_action_base = "http://purenetworks.com/HNAP1/"
        self.headers = {
            "Content-Type": "text/xml; charset=utf-8"
        }
        self.private_key = None
        self.cookie = None

    def _parse_xml_value(self, xml, tag):
        try:
            root = ET.fromstring(xml)
            return root.find(f".//{{*}}{tag}").text
        except Exception as e:
            logger.error(f"Failed to parse tag {tag}: {e}")
            raise

    def _get_hnap_auth(self, action, timestamp):
        if not self.private_key:
            return ""
        hmac_digest = hmac.new(
            self.private_key.encode(),
            f"{timestamp}".encode() + action.encode(),
            hashlib.sha256
        ).hexdigest().upper()
        return f"{hmac_digest} {timestamp}"

    def login(self):
        action = f"{self.soap_action_base}Login"
        login_payload = f"""
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <Login xmlns="{self.soap_action_base}">
              <Action>request</Action>
              <Username>{self.username}</Username>
              <LoginPassword></LoginPassword>
              <Captcha></Captcha>
            </Login>
          </soap:Body>
        </soap:Envelope>
        """
        res1 = self.session.post(self.url, headers={**self.headers, "SOAPAction": f'"{action}"'}, data=login_payload, verify=False)
        if "text/html" in res1.headers.get("Content-Type", ""):
            raise RuntimeError("Modem returned unexpected HTML response to XML request.")

        challenge = self._parse_xml_value(res1.text, "Challenge")
        public_key = self._parse_xml_value(res1.text, "PublicKey")
        cookie = res1.cookies.get("UID")

        private_key = hmac.new(
            public_key.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        login_pwd = hmac.new(
            private_key.encode(),
            self.password.encode(),
            hashlib.sha256
        ).hexdigest().upper()

        self.private_key = private_key
        self.cookie = cookie

        login_payload2 = f"""
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <Login xmlns="{self.soap_action_base}">
              <Action>login</Action>
              <Username>{self.username}</Username>
              <LoginPassword>{login_pwd}</LoginPassword>
              <Captcha></Captcha>
            </Login>
          </soap:Body>
        </soap:Envelope>
        """
        timestamp = str(int(datetime.utcnow().timestamp()))
        headers = {
            **self.headers,
            "SOAPAction": f'"{action}"',
            "HNAP_AUTH": self._get_hnap_auth(action, timestamp),
            "Cookie": f"UID={cookie}"
        }
        res2 = self.session.post(self.url, headers=headers, data=login_payload2, verify=False)
        result = self._parse_xml_value(res2.text, "LoginResult")
        if result != "success":
            raise RuntimeError(f"Login failed: {result}")
        return True

    def get_status(self):
        if not self.login():
            raise RuntimeError("Login failed")

        action = f"{self.soap_action_base}GetMultipleHNAPs"
        timestamp = str(int(datetime.utcnow().timestamp()))
        headers = {
            **self.headers,
            "SOAPAction": f'"{action}"',
            "HNAP_AUTH": self._get_hnap_auth(action, timestamp),
            "Cookie": f"UID={self.cookie}"
        }

        payload = f"""
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                       xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <GetMultipleHNAPs xmlns="{self.soap_action_base}">
              <GetHNAPs>
                <string>GetStatus</string>
                <string>GetCommonLinkProperties</string>
                <string>GetCMStatus</string>
              </GetHNAPs>
            </GetMultipleHNAPs>
          </soap:Body>
        </soap:Envelope>
        """

        res = self.session.post(self.url, headers=headers, data=payload, verify=False)
        root = ET.fromstring(res.text)

        data = {}
        for tag in ["GetStatusResponse", "GetCommonLinkPropertiesResponse", "GetCMStatusResponse"]:
            node = root.find(f".//{{*}}{tag}")
            if node is not None:
                for child in node:
                    data[child.tag.split("}")[-1]] = child.text

        return data
