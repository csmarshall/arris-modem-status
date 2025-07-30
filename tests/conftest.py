import json
import time
from unittest.mock import MagicMock, Mock, patch

import pytest


@pytest.fixture
def mock_modem_responses():
    """Fixture providing comprehensive mock modem responses."""
    return {
        "challenge_response": json.dumps(
            {
                "LoginResponse": {
                    "Challenge": "a1b2c3d4e5f6789012345678901234567890abcd",
                    "PublicKey": "fedcba9876543210abcdef1234567890fedcba98",
                    "Cookie": "12345678-abcd-4321-9876-fedcba987654",
                    "LoginResult": "SUCCESS",
                }
            }
        ),
        "login_success": json.dumps({"LoginResponse": {"LoginResult": "SUCCESS"}}),
        "login_failure": json.dumps({"LoginResponse": {"LoginResult": "FAILED"}}),
        "complete_status": json.dumps(
            {
                "GetMultipleHNAPsResponse": {
                    "GetCustomerStatusSoftwareResponse": {
                        "StatusSoftwareCustomerVer": "DOCSIS 3.1",
                        "StatusSoftwareModelName": "S34",
                        "StatusSoftwareSfVer": "AT01.01.010.042324_S3.04.735",
                        "StatusSoftwareMac": "F8:20:D2:1D:21:27",
                        "StatusSoftwareHdVer": "1.0",
                        "StatusSoftwareSerialNum": "4CD54D222102727",
                        "CustomerConnSystemUpTime": "26 day(s) 09h:30m:06s",
                        "GetCustomerStatusSoftwareResult": "OK",
                    },
                    "GetCustomerStatusConnectionInfoResponse": {
                        "CustomerConnNetworkAccess": "Allowed",
                    },
                    "GetInternetConnectionStatusResponse": {
                        "InternetConnection": "Connected",
                    },
                    "GetCustomerStatusDownstreamChannelInfoResponse": {
                        "CustomerConnDownstreamChannel": (
                            "1^Locked^256QAM^^549000000^0.6^39.0^15^0|+|"
                            "2^Locked^256QAM^^555000000^1.2^38.5^20^1|+|"
                            "3^Locked^256QAM^^561000000^-0.2^37.8^25^2"
                        )
                    },
                    "GetCustomerStatusUpstreamChannelInfoResponse": {
                        "CustomerConnUpstreamChannel": (
                            "1^Locked^SC-QAM^^^30600000^46.5|+|"
                            "2^Locked^SC-QAM^^^23700000^45.2|+|"
                            "3^Locked^OFDMA^^^25000000^44.8"
                        )
                    },
                }
            }
        ),
        # Legacy response format for backwards compatibility tests
        "legacy_status": json.dumps(
            {
                "GetMultipleHNAPsResponse": {
                    "GetCustomerStatusConnectionInfoResponse": {
                        "StatusSoftwareModelName": "S34",
                        "CustomerCurSystemTime": "7 days 14:23:56",
                        "CustomerConnNetworkAccess": "Allowed",
                    },
                    "GetInternetConnectionStatusResponse": {"InternetConnection": "Connected"},
                    "GetArrisRegisterInfoResponse": {
                        "MacAddress": "AA:BB:CC:DD:EE:FF",
                        "SerialNumber": "ABCD12345678",
                    },
                    "GetCustomerStatusDownstreamChannelInfoResponse": {
                        "CustomerConnDownstreamChannel": (
                            "1^Locked^256QAM^^549000000^0.6^39.0^15^0|+|"
                            "2^Locked^256QAM^^555000000^1.2^38.5^20^1|+|"
                            "3^Locked^256QAM^^561000000^-0.2^37.8^25^2"
                        )
                    },
                    "GetCustomerStatusUpstreamChannelInfoResponse": {
                        "CustomerConnUpstreamChannel": (
                            "1^Locked^SC-QAM^^^30600000^46.5|+|"
                            "2^Locked^SC-QAM^^^23700000^45.2|+|"
                            "3^Locked^OFDMA^^^25000000^44.8"
                        )
                    },
                }
            }
        ),
        "empty_channels": json.dumps(
            {
                "GetMultipleHNAPsResponse": {
                    "GetCustomerStatusDownstreamChannelInfoResponse": {"CustomerConnDownstreamChannel": ""},
                    "GetCustomerStatusUpstreamChannelInfoResponse": {"CustomerConnUpstreamChannel": ""},
                }
            }
        ),
        # Individual endpoint responses for testing
        "software_info_only": json.dumps(
            {
                "GetMultipleHNAPsResponse": {
                    "GetCustomerStatusSoftwareResponse": {
                        "StatusSoftwareCustomerVer": "DOCSIS 3.1",
                        "StatusSoftwareModelName": "S34",
                        "StatusSoftwareSfVer": "AT01.01.010.042324_S3.04.735",
                        "StatusSoftwareMac": "F8:20:D2:1D:21:27",
                        "StatusSoftwareHdVer": "1.0",
                        "StatusSoftwareSerialNum": "4CD54D222102727",
                        "CustomerConnSystemUpTime": "26 day(s) 09h:30m:06s",
                        "GetCustomerStatusSoftwareResult": "OK",
                    }
                }
            }
        ),
    }


@pytest.fixture
def mock_http_session():
    """Mock HTTP session for testing."""
    session = MagicMock()
    session.post = MagicMock()
    session.close = MagicMock()
    session.verify = False
    session.headers = {}
    return session


@pytest.fixture
def mock_successful_auth_flow(mock_modem_responses):
    """Mock successful authentication flow."""
    with patch("requests.Session.post") as mock_post:
        mock_post.side_effect = [
            Mock(
                status_code=200,
                text=mock_modem_responses["challenge_response"],
            ),
            Mock(status_code=200, text=mock_modem_responses["login_success"]),
        ]
        yield mock_post


@pytest.fixture
def mock_successful_status_flow(mock_modem_responses):
    """Mock successful complete status flow with GetCustomerStatusSoftware."""
    with patch("requests.Session.post") as mock_post:
        # Auth flow + 3 status requests (software_info, connection_internet, channel_info)
        mock_post.side_effect = [
            Mock(
                status_code=200,
                text=mock_modem_responses["challenge_response"],
            ),
            Mock(status_code=200, text=mock_modem_responses["login_success"]),
            Mock(status_code=200, text=mock_modem_responses["complete_status"]),
            Mock(status_code=200, text=mock_modem_responses["complete_status"]),
            Mock(status_code=200, text=mock_modem_responses["complete_status"]),
        ]
        yield mock_post


@pytest.fixture
def mock_legacy_status_flow(mock_modem_responses):
    """Mock status flow with legacy response format (no GetCustomerStatusSoftware)."""
    with patch("requests.Session.post") as mock_post:
        # Auth flow + 3 status requests
        mock_post.side_effect = [
            Mock(
                status_code=200,
                text=mock_modem_responses["challenge_response"],
            ),
            Mock(status_code=200, text=mock_modem_responses["login_success"]),
            Mock(status_code=200, text=mock_modem_responses["legacy_status"]),
            Mock(status_code=200, text=mock_modem_responses["legacy_status"]),
            Mock(status_code=200, text=mock_modem_responses["legacy_status"]),
        ]
        yield mock_post


@pytest.fixture
def sample_channel_data():
    """Sample channel data for testing."""
    return {
        "downstream": "1^Locked^256QAM^^549000000^0.6^39.0^15^0",
        "upstream": "1^Locked^SC-QAM^^^30600000^46.5",
        "malformed": "1^Locked",  # Not enough fields
        "empty": "",
    }


@pytest.fixture
def client_kwargs():
    """Default client kwargs for testing."""
    return {
        "password": "test_password",
        "host": "192.168.100.1",
        "port": 443,
        "username": "admin",
        "concurrent": True,
        "max_workers": 2,
        "max_retries": 2,
        "base_backoff": 0.1,
        "capture_errors": True,
        "timeout": (3, 12),
        "enable_instrumentation": True,
    }


@pytest.fixture
def mock_performance_instrumentation():
    """Mock performance instrumentation."""
    from arris_modem_status.instrumentation import PerformanceInstrumentation

    with (
        patch.object(PerformanceInstrumentation, "start_timer") as mock_start,
        patch.object(PerformanceInstrumentation, "record_timing") as mock_record,
    ):
        mock_start.return_value = time.time()
        mock_record.return_value = Mock(operation="test", duration=0.1, success=True, duration_ms=100)
        yield mock_start, mock_record
