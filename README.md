# arris-modem-status

`arris-modem-status` is a Python library and CLI tool to fetch status and diagnostics data from Arris cable modems (such as the S33/S34) over the local network. It interacts with the modem via its web interface and returns structured JSON data including comprehensive channel information.

## Features

* Programmatic access to complete modem status including:
  * **Channel data** (downstream/upstream with power, SNR, frequency, lock status)
  * **Connection diagnostics** (uptime, connectivity status, boot sequence)
  * **Hardware/software information** (model, firmware version, MAC address)
  * **Internet connectivity status** and registration details
* Simple command-line interface for immediate use
* Library interface for integration into monitoring systems (e.g., Netdata plugins)
* **Full HNAP authentication** - Complete reverse-engineered implementation

## Authentication Process

This library implements the complete Arris HNAP (Home Network Administration Protocol) authentication discovered through JavaScript reverse engineering:

### High-Level Authentication Flow

1. **Session Establishment**
   ```
   GET https://192.168.100.1/ → Establish HTTPS session with modem
   ```

2. **Challenge Request** 
   ```
   POST /HNAP1/ → Request authentication challenge
   Body: {"Login":{"Action":"request","Username":"admin","LoginPassword":"","Captcha":"","PrivateLogin":"LoginPassword"}}
   Headers: HNAP_AUTH: HMAC("withoutloginkey", timestamp + soap_action)
   ```

3. **Challenge Response Processing**
   ```
   Response contains: {"Challenge": "base64_value", "PublicKey": "base64_value", "Cookie": "value"}
   Extract Challenge and PublicKey for HMAC computation
   ```

4. **Private Key Generation**
   ```python
   # Step 1: Concatenate PublicKey + Password, use Challenge as message
   private_key = HMAC_SHA256(PublicKey + Password, Challenge)
   ```

5. **Login Password Computation** 
   ```python
   # Step 2: Use private_key as key, Challenge as message (again!)
   login_password = HMAC_SHA256(private_key, Challenge)  
   ```

6. **Authentication Request**
   ```
   POST /HNAP1/ → Send login with computed hash
   Body: {"Login":{"Action":"login","Username":"admin","LoginPassword":"computed_hash","Captcha":"","PrivateLogin":"LoginPassword"}}
   Headers: HNAP_AUTH: HMAC(private_key, timestamp + soap_action)
   ```

7. **Authenticated Data Requests**
   ```
   POST /HNAP1/ → Multiple GetMultipleHNAPs calls for channel data
   Headers: HNAP_AUTH: HMAC(private_key, timestamp + soap_action) + " " + timestamp
   ```

### Key Technical Details

- **HMAC Algorithm**: SHA-256 throughout the process
- **String Concatenation**: PublicKey + Password as UTF-8 strings (not binary)
- **Dynamic Values**: Challenge and PublicKey change with every session
- **HNAP_AUTH Format**: `"HASH TIMESTAMP"` where HASH = HMAC(key, timestamp + soap_action_uri)
- **Soap Action URI**: `"http://purenetworks.com/HNAP1/ActionName"`

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

Example output:
```json
{
  "model_name": "S34",
  "internet_status": "Connected", 
  "downstream_channels": [
    {
      "channel_id": "1",
      "frequency": "549000000 Hz",
      "power": "0.6 dBmV", 
      "snr": "39.0 dB",
      "modulation": "256QAM",
      "lock_status": "Locked"
    }
  ],
  "upstream_channels": [...],
  ...
}
```

## Usage (Library)

### Asynchronous Interface (Recommended)
```python
from arris_modem_status import ArrisStatusClient

async def get_modem_data():
    client = ArrisStatusClient(password="YOUR_MODEM_PASSWORD")
    status = await client.get_status()
    
    print(f"Model: {status['model_name']}")
    print(f"Internet: {status['internet_status']}")
    print(f"Downstream Channels: {len(status['downstream_channels'])}")
    
    # Access individual channel data
    for channel in status['downstream_channels']:
        print(f"Channel {channel.channel_id}: {channel.frequency}, {channel.power}")

import asyncio
asyncio.run(get_modem_data())
```

### Synchronous Interface (Backwards Compatible)
```python
from arris_modem_status import ArrisStatusClient

client = ArrisStatusClient(password="YOUR_MODEM_PASSWORD")
status = client.get_status_sync()  # Synchronous version
print(status)
```

## Testing & Verification

Test the authentication algorithm:
```bash
python test_authentication.py --password "YOUR_PASSWORD" --debug
```

This will verify:
- HMAC algorithm implementation
- Live authentication with your modem
- Channel data extraction and parsing
- Interface compatibility

## Scripts

For development and debugging, there's a script available to capture live modem traffic using Selenium:

```bash
python scripts/extract_selenium_token.py
```

This will open a browser, load the modem interface, and save observed API requests to `selenium_hnap_capture.json`.
You can manually log in if needed during the 30-second wait.

## Channel Data Structure

The library extracts comprehensive channel information:

### Downstream Channels
- **Channel ID**: Physical channel identifier
- **Frequency**: Operating frequency in Hz  
- **Power Level**: Signal strength in dBmV
- **SNR**: Signal-to-noise ratio in dB
- **Modulation**: Modulation type (e.g., 256QAM, OFDM)
- **Lock Status**: Channel lock state (Locked/Unlocked)
- **Error Counts**: Corrected and uncorrected error statistics

### Upstream Channels
- **Channel ID**: Physical channel identifier
- **Frequency**: Operating frequency in Hz
- **Power Level**: Transmit power in dBmV
- **Modulation**: Modulation type (e.g., SC-QAM, OFDM)
- **Lock Status**: Channel lock state

## Requirements

* Python 3.8+
* `aiohttp` - Async HTTP client
* `asyncio` - Async/await support
* (For development/debugging: `selenium`, `selenium-wire`, `beautifulsoup4`)

## Architecture Notes

### HNAP Protocol Implementation
This library implements a complete HNAP (Home Network Administration Protocol) client discovered through reverse engineering of the modem's JavaScript. The authentication process uses:

- **Two-stage HMAC computation** for login password generation
- **Dynamic challenge-response** authentication  
- **Authenticated session management** with proper HNAP_AUTH headers
- **Multi-call data extraction** using GetMultipleHNAPs requests

### Channel Data Parsing
The modem returns channel data in a pipe-delimited format:
```
"1^Locked^256QAM^5^549000000^ 0.6^39.0^1^0^|+|2^Locked^256QAM^..."
```

The library parses this into structured `ChannelInfo` objects with proper field mapping and error handling.

## License

MIT License. See `LICENSE` file for details.

## Roadmap

* [x] Complete HNAP authentication implementation
* [x] Full channel data extraction
* [x] Async and sync interfaces  
* [x] Comprehensive error handling
* [ ] Publish as PyPI package
* [ ] Add support for more Arris models (S33, etc.)
* [ ] Build Netdata plugin integration
* [ ] Determine max safe polling rate
* [ ] Add configuration file support

## Contributing

Contributions welcome! This library was built through careful reverse engineering of the Arris web interface. If you have additional Arris models or encounter issues, please open an issue with:

- Model number and firmware version
- Debug output from test_authentication.py
- Any error messages or unexpected responses

## Technical Background

This library was developed through comprehensive reverse engineering of the Arris S34 web interface, including:

- **Browser session capture** (40+ HTTP requests analyzed)
- **JavaScript source extraction** and algorithm analysis  
- **HMAC computation verification** with multiple test vectors
- **Protocol documentation** and Python implementation

The authentication algorithm was discovered by analyzing `Login.js`, `SOAPAction.js`, and `hmac_sha256.js` from the modem's web interface.

---

Built with 🛠️ to help users gain better insights into their home network hardware.