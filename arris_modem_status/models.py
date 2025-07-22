"""
Data Models for Arris Modem Status Client
=========================================

This module contains all dataclasses and data models used by the
Arris Modem Status Client.

Author: Charles Marshall
Version: 1.3.0
"""

from dataclasses import dataclass
from typing import Dict, Optional


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
    response_headers: Dict[str, str]
    partial_content: str
    recovery_successful: bool
    compatibility_issue: bool  # True if this was an HTTP compatibility issue


@dataclass
class ChannelInfo:
    """Represents a single modem channel with optimized field access."""

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
__all__ = ["TimingMetrics", "ErrorCapture", "ChannelInfo"]
