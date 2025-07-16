"""PyTest configuration and shared fixtures."""

import pytest
import json
from unittest.mock import Mock


@pytest.fixture
def mock_modem_responses():
    """Fixture providing comprehensive mock modem responses."""
    return {
        "challenge_response": {
            "LoginResponse": {
                "Challenge": "a1b2c3d4e5f6789012345678901234567890abcd",
                "PublicKey": "fedcba9876543210abcdef1234567890fedcba98",
                "Cookie": "12345678-abcd-4321-9876-fedcba987654",
                "LoginResult": "SUCCESS"
            }
        },
        "complete_status": {
            "GetMultipleHNAPsResponse": {
                "GetCustomerStatusDownstreamChannelInfoResponse": {
                    "CustomerConnDownstreamChannel": (
                        "1^Locked^256QAM^^549000000^0.6^39.0^15^0|+|"
                        "2^Locked^256QAM^^555000000^1.2^38.5^20^1"
                    )
                },
                "GetCustomerStatusUpstreamChannelInfoResponse": {
                    "CustomerConnUpstreamChannel": (
                        "1^Locked^SC-QAM^^^30600000^46.5|+|"
                        "2^Locked^SC-QAM^^^23700000^45.2"
                    )
                },
                "GetCustomerStatusConnectionInfoResponse": {
                    "StatusSoftwareModelName": "S34"
                }
            }
        }
    }
