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
pip install -r requirements.txt
```

## Usage (CLI)

```bash
python -m arris_status.cli --password YOUR_MODEM_PASSWORD
```

The output will be a JSON-formatted string containing modem status data.

## Usage (Library)

```python
from arris_status.arris_status_client import ArrisStatusClient

client = ArrisStatusClient(password="YOUR_MODEM_PASSWORD")
status = client.get_status()
print(status)
```

## Requirements

* Python 3.8+
* `requests`
* `lxml`

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
