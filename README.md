# arris-modem-status 🚀

[![Quality Check](https://github.com/csmarshall/arris-modem-status/actions/workflows/quality-check.yml/badge.svg)](https://github.com/csmarshall/arris-modem-status/actions/workflows/quality-check.yml)
[![PyPI version](https://badge.fury.io/py/arris-modem-status.svg)](https://badge.fury.io/py/arris-modem-status)
[![Python versions](https://img.shields.io/pypi/pyversions/arris-modem-status.svg)](https://pypi.org/project/arris-modem-status/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-support-yellow?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/cs_marshall)

I got tired of logging into my Arris cable modem's clunky web interface just to check signal levels. So, with the help of AI (Claude), I reverse-engineered the modem's API and built this Python library!

## What's This Thing Do? 🤔

It grabs ALL the juicy details from your Arris S33/S34/SB8200 cable modem:
- 📊 Signal levels, SNR, and all that good stuff
- 🌊 Downstream/upstream channel info  
- 🔧 Modem uptime, firmware version, the works
- ⚡ And it's FAST (< 1.5 seconds vs 7+ seconds scraping the web UI)

## Quick Start 🏃‍♂️

```bash
pip install arris-modem-status

# Check your modem
arris-modem-status --password YOUR_PASSWORD

# Get JSON for your monitoring setup
arris-modem-status --password YOUR_PASSWORD --quiet | jq
```

## Python Usage 🐍

```python
from arris_modem_status import ArrisModemStatusClient

with ArrisModemStatusClient(password="YOUR_PASSWORD") as client:
    status = client.get_status()
    
    print(f"Modem: {status['model_name']}")
    print(f"Uptime: {status['system_uptime']}")
    
    # Check signal levels
    for channel in status['downstream_channels']:
        print(f"Channel {channel.channel_id}: {channel.power} / SNR: {channel.snr}")
```

## The Cool Technical Bits 🤓

I spent way too much time figuring out:
- 🔐 The HNAP authentication (challenge-response with HMAC-SHA256)
- 🏎️ Concurrent requests (3x faster than serial!)
- 🛡️ HTTP compatibility quirks (urllib3 is... picky)
- 📦 How the modem encodes channel data (pipe-delimited chaos)

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

## Found a Bug? Want a Feature? 🐛

Open an issue! PRs welcome! The codebase is pretty clean thanks to the AI helping me follow best practices.

## The Story 📖

I started this because I'm obsessive about my internet connection quality (aren't we all?). After discovering the modem had an API, I went down a rabbit hole of reverse engineering with Claude as my copilot. Many debug sessions and HTTP captures later, here we are!

Fun fact: The trickiest part wasn't the authentication - it was figuring out why urllib3 kept choking on the modem's perfectly valid (but quirky) HTTP responses. Turns out, modems don't read RFC specs. 🤷‍♂️

## Requirements 📋

- Python 3.9+
- An Arris S33/S34/SB8200 modem
- The admin password (usually on the sticker)
- A healthy curiosity about your internet connection

## License 📄

MIT - Use it, modify it, monitoring-ify it!

---

Built with 🧠 + 🤖 by Charles Marshall | [GitHub](https://github.com/csmarshall)
