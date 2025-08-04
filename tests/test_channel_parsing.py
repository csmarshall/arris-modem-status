"""Tests for channel data parsing functionality."""

import pytest

try:
    from arris_modem_status import ArrisModemStatusClient, ChannelInfo

    CLIENT_AVAILABLE = True
except ImportError:
    CLIENT_AVAILABLE = False
    pytest.skip("ArrisModemStatusClient not available", allow_module_level=True)


@pytest.mark.unit
@pytest.mark.parsing
class TestChannelInfoModel:
    """Test ChannelInfo data model."""

    def test_channel_info_basic_creation(self):
        """Test basic ChannelInfo creation."""
        channel = ChannelInfo(
            channel_id="1",
            frequency="549000000",
            power="0.6",
            snr="39.0",
            modulation="256QAM",
            lock_status="Locked",
        )

        assert channel.channel_id == "1"
        assert channel.frequency == "549000000 Hz"  # Auto-formatted
        assert channel.power == "0.6 dBmV"  # Auto-formatted
        assert channel.snr == "39.0 dB"  # Auto-formatted
        assert channel.modulation == "256QAM"
        assert channel.lock_status == "Locked"

    def test_channel_info_already_formatted(self):
        """Test ChannelInfo with already formatted values."""
        channel = ChannelInfo(
            channel_id="2",
            frequency="555000000 Hz",
            power="1.2 dBmV",
            snr="38.5 dB",
            modulation="256QAM",
            lock_status="Locked",
        )

        # Should not double-format
        assert channel.frequency == "555000000 Hz"
        assert channel.power == "1.2 dBmV"
        assert channel.snr == "38.5 dB"

    def test_channel_info_special_values(self):
        """Test ChannelInfo with special values."""
        channel = ChannelInfo(
            channel_id="3",
            frequency="561000000",
            power="-0.2",
            snr="N/A",  # Special case for upstream
            modulation="OFDMA",
            lock_status="Unlocked",
        )

        assert channel.frequency == "561000000 Hz"
        assert channel.power == "-0.2 dBmV"
        assert channel.snr == "N/A"  # Should not be formatted
        assert channel.lock_status == "Unlocked"

    def test_channel_info_invalid_power(self):
        """Test ChannelInfo with invalid power value."""
        channel = ChannelInfo(
            channel_id="4",
            frequency="567000000",
            power="invalid",
            snr="37.0",
            modulation="256QAM",
            lock_status="Locked",
        )

        # Should handle invalid power gracefully
        assert channel.power == "invalid"  # No formatting applied

    def test_channel_info_optional_fields(self):
        """Test ChannelInfo with optional fields."""
        channel = ChannelInfo(
            channel_id="5",
            frequency="573000000",
            power="2.1",
            snr="36.2",
            modulation="1024QAM",
            lock_status="Locked",
            corrected_errors="150",
            uncorrected_errors="5",
            channel_type="downstream",
        )

        assert channel.corrected_errors == "150"
        assert channel.uncorrected_errors == "5"
        assert channel.channel_type == "downstream"


@pytest.mark.unit
@pytest.mark.parsing
class TestChannelDataParsing:
    """Test channel data parsing methods."""

    def test_parse_downstream_channel_string(self, sample_channel_data):
        """Test parsing downstream channel string."""
        client = ArrisModemStatusClient(password="test")

        channels = client._parse_channel_string(sample_channel_data["downstream"], "downstream")

        assert len(channels) == 1
        channel = channels[0]
        assert channel.channel_id == "1"
        assert channel.lock_status == "Locked"
        assert channel.modulation == "256QAM"
        assert "549000000" in channel.frequency
        assert channel.power == "0.6 dBmV"
        assert channel.snr == "39.0 dB"
        assert channel.corrected_errors == "15"
        assert channel.uncorrected_errors == "0"
        assert channel.channel_type == "downstream"

    def test_parse_upstream_channel_string(self, sample_channel_data):
        """Test parsing upstream channel string."""
        client = ArrisModemStatusClient(password="test")

        channels = client._parse_channel_string(sample_channel_data["upstream"], "upstream")

        assert len(channels) == 1
        channel = channels[0]
        assert channel.channel_id == "1"
        assert channel.lock_status == "Locked"
        assert channel.modulation == "SC-QAM"
        assert "30600000" in channel.frequency
        assert channel.power == "46.5 dBmV"
        assert channel.snr == "N/A"  # Upstream channels typically don't have SNR
        assert channel.channel_type == "upstream"

    def test_parse_multiple_channels(self):
        """Test parsing multiple channels in one string."""
        client = ArrisModemStatusClient(password="test")
        multi_channel_data = (
            "1^Locked^256QAM^^549000000^0.6^39.0^15^0|+|"
            "2^Locked^256QAM^^555000000^1.2^38.5^20^1|+|"
            "3^Unlocked^256QAM^^561000000^-0.2^37.8^25^2"
        )

        channels = client._parse_channel_string(multi_channel_data, "downstream")

        assert len(channels) == 3

        # First channel
        assert channels[0].channel_id == "1"
        assert channels[0].lock_status == "Locked"
        assert channels[0].uncorrected_errors == "0"

        # Second channel
        assert channels[1].channel_id == "2"
        assert channels[1].power == "1.2 dBmV"
        assert channels[1].uncorrected_errors == "1"

        # Third channel
        assert channels[2].channel_id == "3"
        assert channels[2].lock_status == "Unlocked"
        assert channels[2].power == "-0.2 dBmV"

    def test_parse_malformed_channel_string(self, sample_channel_data):
        """Test parsing malformed channel string."""
        client = ArrisModemStatusClient(password="test")

        channels = client._parse_channel_string(sample_channel_data["malformed"], "downstream")

        # Should handle gracefully and return empty list
        assert len(channels) == 0

    def test_parse_empty_channel_string(self, sample_channel_data):
        """Test parsing empty channel string."""
        client = ArrisModemStatusClient(password="test")

        channels = client._parse_channel_string(sample_channel_data["empty"], "downstream")

        assert len(channels) == 0

    def test_parse_channels_from_hnap_response(self):
        """Test channel parsing from complete HNAP response."""
        client = ArrisModemStatusClient(password="test")

        hnap_response = {
            "GetCustomerStatusDownstreamChannelInfoResponse": {
                "CustomerConnDownstreamChannel": "1^Locked^256QAM^^549000000^0.6^39.0^15^0"
            },
            "GetCustomerStatusUpstreamChannelInfoResponse": {
                "CustomerConnUpstreamChannel": "1^Locked^SC-QAM^^^30600000^46.5"
            },
        }

        channels = client._parse_channels(hnap_response)

        assert "downstream" in channels
        assert "upstream" in channels
        assert len(channels["downstream"]) == 1
        assert len(channels["upstream"]) == 1

        downstream = channels["downstream"][0]
        upstream = channels["upstream"][0]

        assert downstream.channel_type == "downstream"
        assert upstream.channel_type == "upstream"

    def test_parse_channels_missing_data(self):
        """Test channel parsing with missing data."""
        client = ArrisModemStatusClient(password="test")

        # Empty response
        empty_response = {}
        channels = client._parse_channels(empty_response)

        assert channels["downstream"] == []
        assert channels["upstream"] == []

    def test_parse_channels_exception_handling(self):
        """Test channel parsing with exception."""
        client = ArrisModemStatusClient(password="test")

        # Malformed response that would cause exceptions
        bad_response = {"GetCustomerStatusDownstreamChannelInfoResponse": None}

        # Should handle gracefully without raising
        channels = client._parse_channels(bad_response)

        assert channels["downstream"] == []
        assert channels["upstream"] == []


@pytest.mark.unit
@pytest.mark.parsing
class TestResponseParsing:
    """Test complete response parsing."""

    def test_parse_responses_complete(self, mock_modem_responses):
        """Test parsing complete response data."""
        client = ArrisModemStatusClient(password="test")

        responses = {
            "software_info": mock_modem_responses["software_info"],  # Added software_info
            "startup_connection": mock_modem_responses["complete_status"],
            "internet_register": mock_modem_responses["complete_status"],
            "channel_info": mock_modem_responses["complete_status"],
        }

        parsed_data = client._parse_responses(responses)

        assert parsed_data["model_name"] == "S34"
        assert parsed_data["firmware_version"] == "AT01.01.010.042324_S3.04.735"  # From software_info
        assert parsed_data["hardware_version"] == "1.0"  # From software_info
        assert parsed_data["system_uptime"] == "7 days 14:23:56"  # From software_info
        assert parsed_data["connection_status"] == "Allowed"
        assert parsed_data["internet_status"] == "Connected"
        assert parsed_data["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert parsed_data["serial_number"] == "ABCD12345678"
        assert len(parsed_data["downstream_channels"]) == 3
        assert len(parsed_data["upstream_channels"]) == 3
        assert parsed_data["channel_data_available"] is True

    def test_parse_responses_partial(self):
        """Test parsing with partial response data."""
        client = ArrisModemStatusClient(password="test")

        responses = {
            "startup_connection": '{"GetMultipleHNAPsResponse": {"GetCustomerStatusConnectionInfoResponse": {"StatusSoftwareModelName": "S34"}}}'
        }

        parsed_data = client._parse_responses(responses)

        assert parsed_data["model_name"] == "S34"
        assert parsed_data["internet_status"] == "Unknown"  # Default value
        assert parsed_data["firmware_version"] == "Unknown"  # Default value
        assert parsed_data["system_uptime"] == "Unknown"  # Default value
        assert parsed_data["downstream_channels"] == []
        assert parsed_data["channel_data_available"] is False

    def test_parse_responses_invalid_json(self):
        """Test parsing with invalid JSON."""
        client = ArrisModemStatusClient(password="test")

        responses = {"invalid": "not json", "empty": ""}

        parsed_data = client._parse_responses(responses)

        # Should return defaults
        assert parsed_data["model_name"] == "Unknown"
        assert parsed_data["internet_status"] == "Unknown"
        assert parsed_data["firmware_version"] == "Unknown"
        assert parsed_data["system_uptime"] == "Unknown"
        assert parsed_data["downstream_channels"] == []

    def test_parse_responses_no_channels(self, mock_modem_responses):
        """Test parsing response with no channel data."""
        client = ArrisModemStatusClient(password="test")

        responses = {"channel_info": mock_modem_responses["empty_channels"]}

        parsed_data = client._parse_responses(responses)

        assert parsed_data["downstream_channels"] == []
        assert parsed_data["upstream_channels"] == []
        assert parsed_data["channel_data_available"] is False

    def test_parse_responses_software_info_only(self, mock_modem_responses):
        """Test parsing with only software info response."""
        client = ArrisModemStatusClient(password="test")

        responses = {"software_info": mock_modem_responses["software_info"]}

        parsed_data = client._parse_responses(responses)

        # Should have parsed software info correctly
        assert parsed_data["model_name"] == "S34"
        assert parsed_data["firmware_version"] == "AT01.01.010.042324_S3.04.735"
        assert parsed_data["hardware_version"] == "1.0"
        assert parsed_data["system_uptime"] == "7 days 14:23:56"

        # Other fields should be default
        assert parsed_data["internet_status"] == "Unknown"
        assert parsed_data["downstream_channels"] == []
        assert parsed_data["upstream_channels"] == []

    def test_parse_responses_missing_nested_keys(self):
        """Test parsing responses with missing nested keys."""
        client = ArrisModemStatusClient(password="test")

        responses = {
            "software_info": '{"GetMultipleHNAPsResponse": {}}',  # Missing inner response
            "channel_info": '{"GetMultipleHNAPsResponse": {"GetCustomerStatusDownstreamChannelInfoResponse": {}}}',  # Missing channel data
        }

        parsed = client._parse_responses(responses)

        # Should handle gracefully with defaults
        assert parsed["model_name"] == "Unknown"
        assert parsed["downstream_channels"] == []
