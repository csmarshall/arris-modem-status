import argparse
import json
import logging

from arris_status import ArrisStatusClient

def main():
    parser = argparse.ArgumentParser(description="Query Arris modem status and output JSON.")
    parser.add_argument("--host", default="192.168.100.1", help="Modem hostname or IP address (default: 192.168.100.1)")
    parser.add_argument("--username", default="admin", help="Modem username (default: admin)")
    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s"
    )

    client = ArrisStatusClient(
        host=args.host,
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
