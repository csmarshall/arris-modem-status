"""
Arris Modem Status Library
=========================

High-performance Python library for querying Arris cable modem status via HNAP.

Example Usage:
    from arris_modem_status import ArrisStatusClient

    client = ArrisStatusClient(password="your_password")
    status = client.get_status()

    print(f"Internet: {status['internet_status']}")
    print(f"Channels: {len(status['downstream_channels'])} down, {len(status['upstream_channels'])} up")

Author: Charles Marshall
License: MIT
Version: 1.1.0
"""

from .arris_status_client import ArrisStatusClient, ChannelInfo

# Version information
__version__ = "1.1.0"
__author__ = "Charles Marshall"
__license__ = "MIT"

# Public API
__all__ = [
    "ArrisStatusClient",
    "ChannelInfo",
    "__version__",
    "__author__",
    "__license__"
]
