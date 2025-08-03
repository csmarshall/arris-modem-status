"""
Data Models for Arris Modem Status Client
=========================================

This module contains all dataclasses and data models used by the
Arris Modem Status Client.

"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TimingMetrics:
    """Detailed timing metrics for performance analysis."""

    operation: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    error_type: Optional[str] = None
    retry_count: int = 0
    http_status: Optional[int] = None
    response_size: int = 0

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000


@dataclass
class ErrorCapture:
    """Captures details about HTTP compatibility issues for analysis."""

    timestamp: float
    request_type: str
    http_status: int
    error_type: str
    raw_error: str
    response_headers: dict[str, str]
    partial_content: str
    recovery_successful: bool
    compatibility_issue: bool  # True if this was an HTTP compatibility issue


@dataclass
class ChannelInfo:
    """
    Represents a single modem channel with optimized field access.

    This dataclass contains all the diagnostic information for a single
    downstream or upstream channel, with automatic formatting applied
    to common fields for consistent display.

    Attributes:
        channel_id: Channel identifier (e.g., "1", "2")
        frequency: Channel frequency, auto-formatted with "Hz" suffix
        power: Signal power level, auto-formatted with "dBmV" suffix
        snr: Signal-to-noise ratio, auto-formatted with "dB" suffix (downstream only)
        modulation: Modulation type (e.g., "256QAM", "SC-QAM", "OFDMA")
        lock_status: Channel lock status ("Locked", "Unlocked", etc.)
        corrected_errors: Number of corrected errors (downstream only, optional)
        uncorrected_errors: Number of uncorrected errors (downstream only, optional)
        channel_type: Channel type ("downstream", "upstream", "unknown")

    Examples:
        Downstream channel with full diagnostics:

        >>> channel = ChannelInfo(
        ...     channel_id="1",
        ...     frequency="549000000",  # Auto-formatted to "549000000 Hz"
        ...     power="0.6",           # Auto-formatted to "0.6 dBmV"
        ...     snr="39.0",            # Auto-formatted to "39.0 dB"
        ...     modulation="256QAM",
        ...     lock_status="Locked",
        ...     corrected_errors="15",
        ...     uncorrected_errors="0",
        ...     channel_type="downstream"
        ... )

        Upstream channel (no SNR or error counts):

        >>> channel = ChannelInfo(
        ...     channel_id="1",
        ...     frequency="30600000",
        ...     power="46.5",
        ...     snr="N/A",
        ...     modulation="SC-QAM",
        ...     lock_status="Locked",
        ...     channel_type="upstream"
        ... )

    Note:
        Frequency, power, and SNR values are automatically formatted with
        appropriate units if they are numeric strings without units.
    """

    channel_id: str
    frequency: str
    power: str
    snr: str
    modulation: str
    lock_status: str
    corrected_errors: Optional[str] = None
    uncorrected_errors: Optional[str] = None
    channel_type: str = "unknown"

    def __post_init__(self) -> None:
        """Post-init processing for data validation and cleanup."""
        # Clean up frequency format
        if self.frequency.isdigit():
            self.frequency = f"{self.frequency} Hz"

        # Clean up power format
        if self.power and not self.power.endswith("dBmV"):
            try:
                float(self.power)
                self.power = f"{self.power} dBmV"
            except ValueError:
                pass

        # Clean up SNR format
        if self.snr and self.snr != "N/A" and not self.snr.endswith("dB"):
            try:
                float(self.snr)
                self.snr = f"{self.snr} dB"
            except ValueError:
                pass


# Export all models
__all__ = ["ChannelInfo", "ErrorCapture", "TimingMetrics"]
