# Debugging Scripts

This directory contains helper scripts used during development of `arris-modem-status`.

## `extract_selenium_token.py`

This script launches a browser and passively listens for requests made to the Arris modem’s API interface. It’s useful for inspecting how the web interface communicates, especially when debugging headers, tokens, or unusual behavior.

### Setup

1. Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. Install development requirements:
    ```bash
    pip install -e .[dev]
    ```

3. Run the script:
    ```bash
    python scripts/extract_selenium_token.py
    ```

### Output

After 30 seconds, it will write any captured `HNAP1` API traffic to `selenium_hnap_capture.json`.

---

**Note:** This requires Google Chrome and `chromedriver` installed and available in your `PATH`.

# Arris Modem Status Scripts – Testing Summary

This README provides a detailed summary of each script used to attempt capturing request and response traffic from an Arris cable modem’s web interface.

## ⚙️ Overview

The primary goal of this project is to extract upstream/downstream channel statistics from a JavaScript-rendered status page on an Arris modem. Due to the nature of the page (heavy JavaScript + potentially obfuscated API calls), various tools and techniques have been tested including:

- Selenium with stealth or undetected drivers
- Chrome DevTools Protocol (CDP)
- JavaScript injection
- Proxy (mitmproxy)
- Capturing XHR/fetch requests

---

## 📜 Script Summaries

### `capture_modem_cdp.py`
**Goal:** Use Selenium CDP to capture all network requests/responses during page load.

**Approach:**
- Launch undetected Chrome with CDP enabled
- Attempt modem login
- Use CDP events (`Network.requestWillBeSent`, `Network.responseReceived`, `Network.getResponseBody`) to log traffic

**Status:**  
🟥 `modem_cdp_capture.json` output was empty — modem responses not captured or logged correctly. May have failed due to incorrect login or early termination.

---

### `capture_with_proxy.py`
**Goal:** Intercept all browser traffic using `selenium-wire` + embedded mitmproxy.

**Approach:**
- Use Selenium Wire’s internal proxy to sniff all traffic
- Let JavaScript execute normally
- Dump all requests/responses to `.flow` file

**Status:**  
🟨 Captured data (`mitm_capture_all.flow`) was large (~20MB) but the specific upstream/downstream info was not found on inspection.

---

### `debug_cdp_capture.py`
**Goal:** Fine-tune and debug CDP capture and login issues.

**Approach:**
- Wait for form using known IDs (`loginUsername`, `loginWAP`, `login`)
- Attach listeners to all CDP network events
- Try to download response bodies as they arrive

**Status:**  
🟥 Multiple runs showed:
- Occasional failures to locate login form
- Final JSON capture file always 2 bytes (empty array)
- Response bodies could not be fetched (possibly blocked or due to HTTPS issues)

---

### `extract_selenium_stealth.py`
**Goal:** Use Selenium with stealth JS injection to bypass anti-bot checks.

**Approach:**
- Inject `navigator.webdriver = false`
- Load modem page, login, wait for tables
- Scrape DOM once tables are present

**Status:**  
🟥 Tables never appeared. JavaScript may not have loaded correctly due to browser stealth hacks.

---

### `extract_selenium_token.py`
**Goal:** Log in and manually fetch XHR token used in modem’s authenticated requests.

**Approach:**
- Attempt login
- Intercept headers or DOM fields with token values

**Status:**  
🟥 Token not located — modem may not use an explicit bearer token.

---

### `extract_selenium_undetected.py`
**Goal:** Use `undetected-chromedriver` to mimic a real user and capture requests.

**Approach:**
- Launch stealthy Chrome
- Log in and wait for JS-rendered content
- Use Selenium Wire to capture and dump traffic

**Status:**  
🟨 Successfully rendered tables visually, but captured output (`selenium_hnap_capture.json`) was empty — possible race condition or injection delay.

---

### `extract_undetected_with_cdp.py`
**Goal:** Combine `undetected-chromedriver` with CDP traffic logging.

**Approach:**
- Same as above but adds CDP event listener
- Attempt to read request/response events in real time

**Status:**  
🟥 Fails due to `Chrome` object lacking `_devtools_protocol` attribute (undetected driver limitation).

---

### `extract_with_cdp_logging.py`
**Goal:** Use official Selenium CDP API to log all requests/responses.

**Approach:**
- Enable `Network.enable`
- Use `add_cdp_listener` on request and response events
- Attempt to decode and save all JSON traffic

**Status:**  
🟥 Fatal error: `Network.setMonitoringXHREnabled` does not exist — removed from modern CDP spec. Also, tables still didn’t load.

---

### `inject_capture_xhr.py`
**Goal:** Use browser-injected JavaScript to track XHR/fetch requests.

**Approach:**
- Inject script to monkey-patch `fetch` and `XMLHttpRequest.prototype.send`
- Collect all outbound requests
- Retrieve them via `execute_script`

**Status:**  
🟥 JS injected successfully, but resulting capture (`selenium_hnap_capture.json`) had only 2 bytes. Possible HTTPS certificate rejection or timing issue.

---

### `inject_capture_xhr_early.py`
**Goal:** Inject capture JS _before_ login or page JS initializes.

**Approach:**
- Inject XHR monitor before login
- Wait for redirect and let page JS execute
- Pull out collected requests

**Status:**  
🟥 Also failed — likely due to timing (XHRs fired before injection), or JS sandboxing.

---

## 📂 Artifacts and File Sizes

| File                     | Size     | Description                          |
|--------------------------|----------|--------------------------------------|
| `modem_cdp_capture.json` | 2 bytes  | CDP capture — empty                  |
| `selenium_hnap_capture.json` | 2 bytes | JS-injected capture — also empty     |
| `mitm_capture_all.flow`  | ~20MB    | Full proxy capture via mitmproxy     |

---

## 📌 Next Steps

- Investigate direct API calls used by JavaScript (e.g. HNAP1 or status endpoints)
- Consider reverse-engineering from `mitm_capture_all.flow`
- Add HAR support for Chrome via `performance.log` in Selenium
- Try [Playwright](https://playwright.dev/python/) for better network/event control
- Explore modem’s `/HNAP1/` endpoints manually (e.g. via `curl` or Postman)

---

## 🧠 Final Thoughts

Getting upstream/downstream data from an Arris modem is complicated by:
- JavaScript-heavy frontend
- Possibly obfuscated API calls
- TLS interception difficulties
- Browser security preventing clean injection/capture

More stable solutions may involve traffic capture at the network level or firmware reverse engineering.

