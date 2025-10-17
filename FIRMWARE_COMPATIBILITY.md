# Firmware Compatibility Tracking

This document tracks which Arris modem firmware versions have been tested with this library and any known compatibility issues or protocol changes.

## Purpose

Firmware updates can change HNAP protocol behavior, authentication requirements, or response formats. This tracking helps:
- Identify when protocol changes break compatibility
- Document workarounds for specific firmware versions
- Provide version-specific guidance to users
- Track protocol evolution over time

## Tested Firmware Versions

### Arris S34

| Firmware Version | Test Date | Status | Protocol Changes | Notes |
|------------------|-----------|--------|------------------|-------|
| `AT01.01.010.042324_S3.04.735` | 2025-10-17 | ✅ Working | HNAP_AUTH required on challenge requests | Fixed in commit fixing RELOAD error |

**AT01.01.010.042324_S3.04.735 Details:**
- **Model**: S34
- **Hardware Version**: 1.0
- **ISP**: Comcast (USA)
- **Test Location**: Development testing
- **Known Issues**:
  - Requires `HNAP_AUTH` header on initial challenge request (uses "withoutloginkey" fallback)
  - Returns `"LoginResult": "RELOAD"` if HNAP_AUTH is missing
- **Protocol Behavior**:
  - Challenge request must include HMAC-SHA256 auth token
  - Token computed as: `hex_hmac_sha256("withoutloginkey", timestamp + URI)`
  - JavaScript fallback: `if(PrivateKey == null) PrivateKey = "withoutloginkey"`

### Arris S33

| Firmware Version | Test Date | Status | Protocol Changes | Notes |
|------------------|-----------|--------|------------------|-------|
| *Not yet tested* | - | ⚠️ Untested | - | Likely compatible based on S34 testing |

### Arris SB8200

| Firmware Version | Test Date | Status | Protocol Changes | Notes |
|------------------|-----------|--------|------------------|-------|
| *Not yet tested* | - | ⚠️ Untested | - | Likely compatible based on S34 testing |

## Reporting Compatibility

If you test this library with a different firmware version, please report your findings by opening an issue with:

1. **Firmware version** (from modem status page or `arris-modem-status` output)
2. **Model name** (S34, S33, SB8200, etc.)
3. **Hardware version**
4. **ISP** (if comfortable sharing)
5. **Success status**: ✅ Working, ⚠️ Partial, ❌ Broken
6. **Any error messages** or unexpected behavior
7. **Optional**: HAR capture from browser (see [Debugging Protocol Issues](README.md#debugging-protocol-issues))

## Known Protocol Changes by Firmware

### HNAP_AUTH Authentication Token

**Change introduced**: Unknown (present in AT01.01.010.042324_S3.04.735)

**Behavior**:
- All HNAP requests (including initial challenge) require `HNAP_AUTH` header
- Before authentication: uses `"withoutloginkey"` as HMAC key
- After authentication: uses computed PrivateKey as HMAC key
- Missing HNAP_AUTH results in `"LoginResult": "RELOAD"` response

**Implementation**:
```python
# Before challenge request
auth_token = authenticator.generate_auth_token("Login")  # Uses "withoutloginkey"
response = request_handler.make_request_with_retry("Login", request, auth_token=auth_token)
```

**Browser JavaScript reference** (from modem's `hnap.js`):
```javascript
var PrivateKey=$.cookie('PrivateKey');
if(PrivateKey == null) PrivateKey = "withoutloginkey";
var current_time = new Date().getTime();
current_time = Math.floor(current_time) % 2000000000000;
var URI = '"http://purenetworks.com/HNAP1/'+hnap+'"';
var auth = hex_hmac_sha256(PrivateKey, current_time.toString()+URI);
ajaxObj.setHeader("HNAP_AUTH", auth + " " + current_time);
```

## Debugging Firmware Changes

When encountering issues with new firmware:

1. **Capture browser behavior**:
   ```bash
   python debug_tools/enhanced_deep_capture.py --password YOUR_PASSWORD
   ```

2. **Compare headers**: Check `deep_capture.har` in Chrome DevTools Network tab
   - Look for new/changed headers
   - Note authentication flow differences
   - Check cookie requirements

3. **Extract JavaScript**: HAR files contain modem's JavaScript
   - Search for authentication logic changes
   - Look for new HMAC computations
   - Check for modified request formats

4. **Test incrementally**:
   ```bash
   arris-modem-status --debug --password YOUR_PASSWORD
   ```

5. **Document findings**: Open issue with firmware version + HAR capture

## Version Detection

The library automatically detects firmware version during connection:

```python
from arris_modem_status import ArrisModemStatusClient

with ArrisModemStatusClient(password="YOUR_PASSWORD") as client:
    status = client.get_status()
    print(f"Firmware: {status['firmware_version']}")
```

## Contributing Firmware Data

To help track firmware compatibility:

1. Run with `--debug` flag to capture detailed logs
2. Export HAR file from successful browser session
3. Note any warnings or errors encountered
4. Open issue with firmware version and findings

## Historical Protocol Changes

*This section will be updated as protocol changes are discovered across firmware versions.*

### Future Tracking

As new firmware versions are released, we'll document:
- Authentication changes
- New HNAP endpoints
- Response format modifications
- Deprecated fields or methods
- Performance characteristics
- Known bugs or quirks

---

**Last Updated**: 2025-10-17
**Maintainer**: Charles Marshall
**Contributing**: PRs welcome for new firmware testing results
