"""
Authentication module for Arris Modem Status Client
===================================================

This module handles HNAP authentication with the Arris modem.

"""

import hashlib
import hmac
import json
import logging
import time
from typing import Optional, Tuple

from arris_modem_status.exceptions import ArrisParsingError

logger = logging.getLogger("arris-modem-status")


class HNAPAuthenticator:
    """Handles HNAP authentication for Arris modems."""

    def __init__(self, username: str, password: str):
        """
        Initialize HNAP authenticator.

        Args:
            username: Login username
            password: Login password
        """
        self.username = username
        self.password = password
        self.private_key: Optional[str] = None
        self.uid_cookie: Optional[str] = None
        self.authenticated: bool = False

    def generate_auth_token(self, soap_action: str, timestamp: Optional[int] = None) -> str:
        """
        Generate HNAP auth token.

        Args:
            soap_action: SOAP action name
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            HNAP auth token string
        """
        if timestamp is None:
            timestamp = int(time.time() * 1000) % 2000000000000

        hmac_key = self.private_key or "withoutloginkey"
        message = f'{timestamp}"http://purenetworks.com/HNAP1/{soap_action}"'

        auth_hash = (
            hmac.new(
                hmac_key.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

        return f"{auth_hash} {timestamp}"

    def parse_challenge_response(self, response_text: str) -> Tuple[str, str, Optional[str]]:
        """
        Parse authentication challenge response.

        Args:
            response_text: Raw response text from challenge request

        Returns:
            Tuple of (challenge, public_key, uid_cookie)

        Raises:
            ArrisParsingError: If response cannot be parsed
        """
        try:
            data = json.loads(response_text)
            login_resp = data["LoginResponse"]
            challenge = login_resp["Challenge"]
            public_key = login_resp["PublicKey"]
            uid_cookie = login_resp.get("Cookie")

            return challenge, public_key, uid_cookie

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Challenge parsing failed: {e}")
            raise ArrisParsingError(
                "Failed to parse authentication challenge response",
                details={"phase": "challenge", "parse_error": str(e), "response": response_text[:200]},
            ) from e

    def compute_credentials(self, challenge: str, public_key: str) -> str:
        """
        Compute login credentials from challenge.

        Args:
            challenge: Challenge string from modem
            public_key: Public key from modem

        Returns:
            Login password for authentication
        """
        # Compute private key
        key_material = public_key + self.password
        self.private_key = (
            hmac.new(
                key_material.encode("utf-8"),
                challenge.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

        # Compute login password
        return (
            hmac.new(
                self.private_key.encode("utf-8"),
                challenge.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

    def build_challenge_request(self) -> dict:
        """Build initial challenge request."""
        return {
            "Login": {
                "Action": "request",
                "Username": self.username,
                "LoginPassword": "",
                "Captcha": "",
                "PrivateLogin": "LoginPassword",
            }
        }

    def build_login_request(self, login_password: str) -> dict:
        """Build login request with computed password."""
        return {
            "Login": {
                "Action": "login",
                "Username": self.username,
                "LoginPassword": login_password,
                "Captcha": "",
                "PrivateLogin": "LoginPassword",
            }
        }

    def validate_login_response(self, response_text: str) -> bool:
        """
        Validate login response.

        Args:
            response_text: Raw response text from login request

        Returns:
            True if login successful, False otherwise
        """
        if response_text and any(term in response_text.lower() for term in ["success", "ok", "true"]):
            self.authenticated = True
            return True
        return False
