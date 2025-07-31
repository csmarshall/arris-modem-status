# arris-modem-status 🚀

[![Quality Check](https://github.com/csmarshall/arris-modem-status/actions/workflows/quality-check.yml/badge.svg)](https://github.com/csmarshall/arris-modem-status/actions/workflows/quality-check.yml)
[![codecov](https://codecov.io/gh/csmarshall/arris-modem-status/branch/main/graph/badge.svg)](https://codecov.io/gh/csmarshall/arris-modem-status)
[![PyPI version](https://badge.fury.io/py/arris-modem-status.svg)](https://badge.fury.io/py/arris-modem-status)
[![Python versions](https://img.shields.io/pypi/pyversions/arris-modem-status.svg)](https://pypi.org/project/arris-modem-status/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/cs_marshall)

I got tired of logging into my Arris cable modem's clunky web interface just to check signal levels. So, with the help of AI (Claude), I reverse-engineered the modem's API and built this Python library!

## What's This Thing Do? 🤔

It grabs **ALL** the juicy details from your Arris S33/S34/SB8200 cable modem:
- 📊 Signal levels, SNR, error counts
- 🌊 Downstream/upstream channel info
- 🔧 Model name, firmware version, hardware version
- ⏰ System uptime (e.g., "27 day(s) 10h:12m:37s")
- 🔒 Boot status, security status, connectivity state
- ⚡ And it's FAST (< 2 seconds in serial mode)

## Quick Start 🏃‍♂️

```bash
pip install arris-modem-status

# Check your modem (serial mode by default for reliability)
arris-modem-status --password YOUR_PASSWORD

# Get JSON for your monitoring setup
arris-modem-status --password YOUR_PASSWORD --quiet | jq

# Use parallel mode if your modem supports it (30% faster but may fail)
arris-modem-status --password YOUR_PASSWORD --parallel
```

## Python Usage 🐍

```python
from arris_modem_status import ArrisModemStatusClient

# Serial mode by default (recommended)
with ArrisModemStatusClient(password="YOUR_PASSWORD") as client:
    status = client.get_status()

    print(f"Modem: {status['model_name']}")
    print(f"Firmware: {status['firmware_version']}")
    print(f"Uptime: {status['system_uptime']}")

    # Check signal levels
    for channel in status['downstream_channels']:
        print(f"Channel {channel.channel_id}: {channel.power} / SNR: {channel.snr}")

# Use concurrent mode if your modem handles it well
with ArrisModemStatusClient(password="YOUR_PASSWORD", concurrent=True) as client:
    status = client.get_status()  # ~30% faster but may get HTTP 403 errors
```

## Serial vs Parallel Mode ⚠️

**DEFAULT: Serial mode** - Requests are made one at a time. Slower but much more reliable.

Many Arris modems have buggy HNAP implementations that return HTTP 403 errors when handling concurrent requests. This causes inconsistent data like:
- Sometimes getting model name, sometimes not
- Missing internet status randomly
- Partial channel information

If you want to try parallel mode for speed (at your own risk):
```bash
arris-modem-status --password YOUR_PASSWORD --parallel
```

## Complete Data Retrieved 📦

The library now retrieves **ALL** available modem information:

```json
{
  "model_name": "S34",
  "hardware_version": "1.0",
  "firmware_version": "AT01.01.010.042324_S3.04.735",
  "system_uptime": "27 day(s) 10h:12m:37s",
  "current_system_time": "07/30/2025 23:31:23",
  "mac_address": "F8:20:D2:1D:21:27",
  "serial_number": "4CD54D222102727",
  "internet_status": "Connected",
  "network_access": "Allowed",
  "boot_status": "OK",
  "boot_comment": "Operational",
  "configuration_file_status": "OK",
  "security_status": "Enabled",
  "security_comment": "BPI+",
  "downstream_frequency": "549000000 Hz",
  "downstream_comment": "Locked",
  "downstream_channels": [...],
  "upstream_channels": [...]
}
```

## The Cool Technical Bits 🤓

I spent way too much time figuring out:
- 🔐 The HNAP authentication (challenge-response with HMAC-SHA256)
- 🏎️ Why concurrent requests fail (modem firmware bugs causing HTTP 403)
- 🛡️ HTTP compatibility quirks (urllib3 is... picky)
- 📦 Complete HNAP request mapping (including the missing GetCustomerStatusSoftware!)
- 🐛 Why data was inconsistent (partial request failures in concurrent mode)

## Monitoring Integration 📈

Perfect for Grafana, Prometheus, or any monitoring stack:

```python
# Quick Prometheus exporter example
from prometheus_client import Gauge
downstream_power = Gauge('arris_downstream_power_dbmv', 'Power', ['channel'])

# Update metrics
for ch in status['downstream_channels']:
    downstream_power.labels(channel=ch.channel_id).set(float(ch.power.split()[0]))
```

## Disclaimer

This is an unofficial library not affiliated with ARRIS® or CommScope, Inc. ARRIS® is a registered trademark of CommScope, Inc.

This is a personal project provided as-is under the MIT license.

## Found a Bug? Want a Feature? 🐛

Open an issue! PRs welcome! The codebase is pretty clean thanks to the AI helping me follow best practices.

## The Story 📖

I started this because I'm obsessive about my internet connection quality (aren't we all?). After discovering the modem had an API, I went down a rabbit hole of reverse engineering with Claude as my copilot.

Fun discoveries:
- The modem returns the same data in multiple HNAP responses (redundancy FTW)
- Many modems can't handle concurrent requests (firmware bugs)
- The missing firmware version was in GetCustomerStatusSoftware all along
- Serial mode is more reliable than parallel for most modems

## Requirements 📋

- Python 3.9+
- An Arris S33/S34/SB8200 modem
- The admin password (usually on the sticker)
- Patience if your modem hates concurrent requests

## License 📄

MIT - Use it, modify it, monitoring-ify it!

---

Built with 🧠 + 🤖 by Charles Marshall | [GitHub](https://github.com/csmarshall)
