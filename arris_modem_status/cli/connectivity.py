"""
Network Connectivity Check Module

This module provides functions for checking network connectivity to the
Arris modem before attempting HTTPS connections. It helps fail fast for
unreachable devices.

Author: Charles Marshall
License: MIT
"""

import logging
import socket
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def quick_connectivity_check(host: str, port: int = 443, timeout: float = 2.0) -> tuple[bool, Optional[str]]:
    """
    Quick TCP connectivity check before attempting HTTPS connection.

    This helps fail fast for unreachable devices instead of waiting for long timeouts.
    Since Arris modems are typically on local networks, if they don't respond quickly,
    they're likely offline or unreachable.

    Args:
        host: Target hostname or IP address
        port: Target port (default: 443 for HTTPS)
        timeout: Connection timeout in seconds (default: 2.0)

    Returns:
        (is_reachable, error_message) - error_message is None if reachable
    """
    try:
        logger.info(f"Performing quick connectivity check: {host}:{port}")
        print(f"🔍 Quick connectivity check: {host}:{port}...", file=sys.stderr)

        with socket.create_connection((host, port), timeout=timeout):
            logger.info("TCP connection successful")
            print("✅ TCP connection successful", file=sys.stderr)
            return True, None

    except socket.timeout:
        error_msg = f"Connection timeout - {host}:{port} not responding within {timeout}s"
        logger.warning(error_msg)
        return False, error_msg

    except socket.gaierror as e:
        error_msg = f"DNS resolution failed for {host}: {e}"
        logger.error(error_msg)
        return False, error_msg

    except ConnectionRefusedError:
        error_msg = f"Connection refused - {host}:{port} not accepting connections"
        logger.error(error_msg)
        return False, error_msg

    except OSError as e:
        error_msg = f"Network error connecting to {host}:{port}: {e}"
        logger.error(error_msg)
        return False, error_msg


def get_optimal_timeouts(host: str) -> tuple[float, float]:
    """
    Get optimal connection timeouts based on whether the host appears to be local.

    Args:
        host: Target hostname or IP address

    Returns:
        (connect_timeout, read_timeout) in seconds
    """
    # Check if this appears to be a local network address
    is_local = host.startswith(("192.168.", "10.", "172.")) or host in ["localhost", "127.0.0.1"]

    if is_local:
        logger.debug(f"Host {host} appears to be local, using shorter timeouts")
        return (2, 8)  # Shorter timeouts for local devices
    logger.debug(f"Host {host} appears to be remote, using longer timeouts")
    return (5, 15)  # Longer timeouts for remote access


def print_connectivity_troubleshooting(host: str, port: int, error_msg: str) -> None:
    """
    Print specific troubleshooting suggestions based on the connection error.

    Args:
        host: Target hostname or IP address
        port: Target port
        error_msg: Error message from connection attempt
    """
    print(f"\n💡 TROUBLESHOOTING for {host}:{port}:", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    if "timeout" in error_msg.lower():
        print("Connection timeout suggests:", file=sys.stderr)
        print(
            f"  1. Device may be offline - verify {host} is powered on",
            file=sys.stderr,
        )
        print(
            "  2. Wrong IP address - check your modem's current IP",
            file=sys.stderr,
        )
        print(f"  3. Network issue - try: ping {host}", file=sys.stderr)
        print("  4. Firewall blocking connection", file=sys.stderr)

    elif "refused" in error_msg.lower():
        print("Connection refused suggests:", file=sys.stderr)
        print("  1. Device is on but HTTPS service disabled", file=sys.stderr)
        print("  2. Try HTTP instead: --port 80", file=sys.stderr)
        print("  3. Web interface may be disabled", file=sys.stderr)

    elif "dns" in error_msg.lower() or "resolution" in error_msg.lower():
        print("DNS resolution failed suggests:", file=sys.stderr)
        print("  1. Use IP address instead of hostname", file=sys.stderr)
        print("  2. Check DNS settings", file=sys.stderr)
        print("  3. Verify hostname spelling", file=sys.stderr)

    else:
        print("Network connectivity issue:", file=sys.stderr)
        print(f"  1. Verify device IP: {host}", file=sys.stderr)
        print(f"  2. Check network connectivity: ping {host}", file=sys.stderr)
        print(f"  3. Try web interface: https://{host}/", file=sys.stderr)
        print("  4. Check if device is on the same network", file=sys.stderr)

    print("\n🔧 Quick tests:", file=sys.stderr)
    print(f"  ping {host}", file=sys.stderr)
    print(f"  curl -k https://{host}/ --connect-timeout 5", file=sys.stderr)

    logger.info(f"Displayed troubleshooting suggestions for: {error_msg}")
