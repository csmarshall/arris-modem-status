"""
Response Parser for Arris Modem Status Client
============================================

This module handles parsing of HNAP responses and channel data.

"""

import json
import logging
from typing import Any

from arris_modem_status.models import ChannelInfo

logger = logging.getLogger("arris-modem-status")


class HNAPResponseParser:
    """Parses HNAP responses into structured data."""

    def parse_responses(self, responses: dict[str, str]) -> dict[str, Any]:
        """Parse HNAP responses into structured data."""
        parsed_data = {
            "model_name": "Unknown",
            "firmware_version": "Unknown",
            "hardware_version": "Unknown",
            "system_uptime": "Unknown",
            "internet_status": "Unknown",
            "connection_status": "Unknown",
            "boot_status": "Unknown",
            "boot_comment": "Unknown",
            "connectivity_status": "Unknown",
            "connectivity_comment": "Unknown",
            "configuration_file_status": "Unknown",
            "security_status": "Unknown",
            "security_comment": "Unknown",
            "mac_address": "Unknown",
            "serial_number": "Unknown",
            "current_system_time": "Unknown",
            "network_access": "Unknown",
            "downstream_frequency": "Unknown",
            "downstream_comment": "Unknown",
            "downstream_channels": [],
            "upstream_channels": [],
            "channel_data_available": True,
        }

        for response_type, content in responses.items():
            try:
                data = json.loads(content)

                # Handle software_info response - check both with and without wrapper
                if response_type == "software_info":
                    software_info = None

                    # First try direct access (without wrapper)
                    if "GetCustomerStatusSoftwareResponse" in data:
                        software_info = data.get("GetCustomerStatusSoftwareResponse", {})
                    # Then try with wrapper
                    elif "GetMultipleHNAPsResponse" in data:
                        hnaps_response = data.get("GetMultipleHNAPsResponse", {})
                        software_info = hnaps_response.get("GetCustomerStatusSoftwareResponse", {})

                    if software_info:
                        parsed_data.update(
                            {
                                "model_name": software_info.get("StatusSoftwareModelName", "Unknown"),
                                "firmware_version": software_info.get("StatusSoftwareSfVer", "Unknown"),
                                "system_uptime": software_info.get("CustomerConnSystemUpTime", "Unknown"),
                                "hardware_version": software_info.get("StatusSoftwareHdVer", "Unknown"),
                            }
                        )
                        logger.debug(
                            f"Parsed software info: Model={parsed_data['model_name']}, "
                            f"Firmware={parsed_data['firmware_version']}, "
                            f"Uptime={parsed_data['system_uptime']}"
                        )
                    continue

                # Normal handling for other responses with wrapper
                hnaps_response = data.get("GetMultipleHNAPsResponse", {})

                if response_type == "channel_info":
                    channels = self._parse_channels(hnaps_response)
                    parsed_data["downstream_channels"] = channels["downstream"]
                    parsed_data["upstream_channels"] = channels["upstream"]

                elif response_type == "startup_connection":
                    # Parse startup sequence info
                    startup_info = hnaps_response.get("GetCustomerStatusStartupSequenceResponse", {})
                    if startup_info:
                        parsed_data.update(
                            {
                                "downstream_frequency": startup_info.get("CustomerConnDSFreq", "Unknown"),
                                "downstream_comment": startup_info.get("CustomerConnDSComment", "Unknown"),
                                "connectivity_status": startup_info.get("CustomerConnConnectivityStatus", "Unknown"),
                                "connectivity_comment": startup_info.get("CustomerConnConnectivityComment", "Unknown"),
                                "boot_status": startup_info.get("CustomerConnBootStatus", "Unknown"),
                                "boot_comment": startup_info.get("CustomerConnBootComment", "Unknown"),
                                "configuration_file_status": startup_info.get(
                                    "CustomerConnConfigurationFileStatus", "Unknown"
                                ),
                                "security_status": startup_info.get("CustomerConnSecurityStatus", "Unknown"),
                                "security_comment": startup_info.get("CustomerConnSecurityComment", "Unknown"),
                            }
                        )

                    # Parse connection info
                    conn_info = hnaps_response.get("GetCustomerStatusConnectionInfoResponse", {})
                    if conn_info:
                        parsed_data.update(
                            {
                                "current_system_time": conn_info.get("CustomerCurSystemTime", "Unknown"),
                                "connection_status": conn_info.get("CustomerConnNetworkAccess", "Unknown"),
                                "network_access": conn_info.get("CustomerConnNetworkAccess", "Unknown"),
                            }
                        )
                        # Only use model name from here if we didn't get it from software_info
                        if parsed_data["model_name"] == "Unknown":
                            parsed_data["model_name"] = conn_info.get("StatusSoftwareModelName", "Unknown")

                elif response_type == "internet_register":
                    internet_info = hnaps_response.get("GetInternetConnectionStatusResponse", {})
                    register_info = hnaps_response.get("GetArrisRegisterInfoResponse", {})

                    parsed_data.update(
                        {
                            "internet_status": internet_info.get("InternetConnection", "Unknown"),
                            "mac_address": register_info.get("MacAddress", "Unknown"),
                            "serial_number": register_info.get("SerialNumber", "Unknown"),
                        }
                    )

            except json.JSONDecodeError as e:
                logger.warning(f"Parse failed for {response_type}: {e}")
                # Don't raise, continue with other responses

        if not parsed_data["downstream_channels"] and not parsed_data["upstream_channels"]:
            parsed_data["channel_data_available"] = False

        return parsed_data

    def _parse_channels(self, hnaps_response: dict[str, Any]) -> dict[str, list[ChannelInfo]]:
        """Parse channel information from HNAP response."""
        channels: dict[str, list[ChannelInfo]] = {"downstream": [], "upstream": []}

        try:
            downstream_resp = hnaps_response.get("GetCustomerStatusDownstreamChannelInfoResponse", {})
            downstream_raw = downstream_resp.get("CustomerConnDownstreamChannel", "")

            if downstream_raw:
                channels["downstream"] = self._parse_channel_string(downstream_raw, "downstream")

            upstream_resp = hnaps_response.get("GetCustomerStatusUpstreamChannelInfoResponse", {})
            upstream_raw = upstream_resp.get("CustomerConnUpstreamChannel", "")

            if upstream_raw:
                channels["upstream"] = self._parse_channel_string(upstream_raw, "upstream")

        except Exception as e:
            logger.error(f"Channel parsing error: {e}")
            # Return empty channels rather than raising

        return channels

    def _parse_channel_string(self, raw_data: str, channel_type: str) -> list[ChannelInfo]:
        """Parse pipe-delimited channel data into ChannelInfo objects."""
        channels = []

        try:
            entries = raw_data.split("|+|")

            for entry in entries:
                if not entry.strip():
                    continue

                fields = entry.split("^")

                if channel_type == "downstream" and len(fields) >= 6:
                    channel = ChannelInfo(
                        channel_id=fields[0] or "Unknown",
                        lock_status=fields[1] or "Unknown",
                        modulation=fields[2] or "Unknown",
                        frequency=fields[4] if len(fields) > 4 else "Unknown",
                        power=fields[5] if len(fields) > 5 else "Unknown",
                        snr=fields[6] if len(fields) > 6 else "Unknown",
                        corrected_errors=(fields[7] if len(fields) > 7 else None),
                        uncorrected_errors=(fields[8] if len(fields) > 8 else None),
                        channel_type=channel_type,
                    )
                    channels.append(channel)

                elif channel_type == "upstream" and len(fields) >= 7:
                    channel = ChannelInfo(
                        channel_id=fields[0] or "Unknown",
                        lock_status=fields[1] or "Unknown",
                        modulation=fields[2] or "Unknown",
                        frequency=fields[5] if len(fields) > 5 else "Unknown",
                        power=fields[6] if len(fields) > 6 else "Unknown",
                        snr="N/A",
                        channel_type=channel_type,
                    )
                    channels.append(channel)

        except Exception as e:
            logger.error(f"Error parsing {channel_type} channel string: {e}")
            # Return what we have so far

        return channels
