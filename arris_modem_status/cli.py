"""
CLI for Arris Modem Status Client

This module provides a command-line interface for querying status information
from an Arris modem using the ArrisStatusClient class.

Usage:
    python -m arris_modem_status.cli --password <password>

Options:
    --host      Hostname or IP address of the modem (default: 192.168.100.1)
    --port      HTTPS port to connect to (default: 443)
    --username  Username for login (default: admin)
    --password  Password for login (required)
    --debug     Enable debug logging

The output is printed in JSON format.
"""

import argparse
import json
import logging
from arris_modem_status import ArrisStatusClient

def main():
    """Entry point for the Arris Modem Status CLI."""
    parser = argparse.ArgumentParser(description="Query Arris modem status and output JSON.")
    parser.add_argument(
        "--host",
        default="192.168.100.1",
        help="Modem hostname or IP address (default: 192.168.100.1)"
    )
    parser.add_argument(
        "--port",
        default=443,
        type=int,
        help="Port for HTTPS connection to the modem (default: 443)"
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Modem username (default: admin)"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Modem password"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s"
    )

    client = ArrisStatusClient(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password
    )

    try:
        status = client.get_status()
        print(json.dumps(status, indent=2))
    except Exception as e:
        logging.error(f"Failed to get modem status: {e}")
        exit(1)

if __name__ == "__main__":
    main()
