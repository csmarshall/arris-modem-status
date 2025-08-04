"""Tests for models module coverage."""

import pytest

from arris_modem_status.models import ChannelInfo


@pytest.mark.unit
class TestModelsCoverage:
    """Test model edge cases for coverage."""

    def test_channel_info_snr_invalid_not_na(self):
        """Test ChannelInfo with invalid SNR that's not 'N/A'."""
        channel = ChannelInfo(
            channel_id="1",
            frequency="549000000",
            power="0.6",
            snr="invalid_value",  # Not a number and not "N/A"
            modulation="256QAM",
            lock_status="Locked",
        )

        # Should not format invalid SNR
        assert channel.snr == "invalid_value"
        assert " dB" not in channel.snr

    def test_channel_info_empty_snr(self):
        """Test ChannelInfo with empty SNR."""
        channel = ChannelInfo(
            channel_id="1",
            frequency="549000000",
            power="0.6",
            snr="",  # Empty string
            modulation="256QAM",
            lock_status="Locked",
        )

        # Should not format empty SNR
        assert channel.snr == ""
