# arris-modem-status

`arris-modem-status` is a Python library and CLI tool to fetch status and diagnostics data from Arris cable modems (such as the S33) over the local network. It interacts with the modem via its web interface and returns structured JSON data.

## Features

* Programmatic access to modem status such as:
  * Channel data (downstream/upstream)
  * Connection uptime
  * Hardware/software version
  * Signal-to-noise ratios and power levels
* Simple command-line interface
* Library interface for integration into other systems (e.g., Netdata plugins)

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .[dev]
```

### Setting up a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -e .[dev]
```

## Usage (CLI)

```bash
python -m arris_modem_status.cli --password YOUR_MODEM_PASSWORD
```

Optional arguments:
- `--host`: Modem IP address or hostname (default: `192.168.100.1`)
- `--port`: HTTPS port (default: `443`)
- `--username`: Modem username (default: `admin`)
- `--debug`: Enable debug logging

The output will be a JSON-formatted string containing modem status data.

## Usage (Library)

```python
from arris_modem_status import ArrisStatusClient

client = ArrisStatusClient(
    host="192.168.100.1",
    port=443,
    username="admin",
    password="YOUR_MODEM_PASSWORD"
)

status = client.get_status()
print(status)
```

## Scripts

For development and debugging, there's a script available to capture live modem traffic using Selenium:

```bash
python scripts/extract_selenium_token.py
```

This will open a browser, load the modem interface, and save observed API requests to `selenium_hnap_capture.json`.
You can manually log in if needed during the 30-second wait.

## Requirements

* Python 3.8+
* `requests`
* (For development/debugging: `selenium`, `selenium-wire`, `beautifulsoup4`)

## License

MIT License. See `LICENSE` file for details.

## Roadmap

* [ ] Publish as PyPI package
* [ ] Add support for more Arris models
* [ ] Improve error handling and reconnection
* [ ] Determine max safe polling rate
* [ ] Build Netdata plugin integration

---

Built with 🛠️ to help users gain better insights into their home network hardware.
