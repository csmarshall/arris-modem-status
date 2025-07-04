import json
import signal
import sys
import time
from argparse import ArgumentParser

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Notes:
# - This script launches Chrome using undetected-chromedriver.
# - It logs in automatically and captures *all* network traffic using CDP.
# - It avoids selenium-wire and mitmproxy.
# - You can cancel early with Ctrl+C, and it still saves the capture.
# - Tables must be rendered in the browser before capture completes.

def main():
    parser = ArgumentParser(description="Capture modem traffic using CDP and undetected-chromedriver.")
    parser.add_argument("--host", default="https://192.168.100.1", help="Modem host URL")
    parser.add_argument("--username", default="admin", help="Modem username")
    parser.add_argument("--password", required=True, help="Modem password")
    args = parser.parse_args()

    captured_requests = []

    print("🌐 Launching undetected Chrome browser to modem login page...")
    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-site-isolation-trials")
    options.add_argument("--auto-open-devtools-for-tabs")

    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.execute_cdp_cmd("Network.enable", {})

    def handle_request_will_be_sent(params):
        captured_requests.append({
            "url": params.get("request", {}).get("url"),
            "method": params.get("request", {}).get("method"),
            "headers": params.get("request", {}).get("headers"),
        })

    driver.execute_cdp_cmd(
        "Network.setCacheDisabled", {"cacheDisabled": True}
    )
    driver.request_interceptor = None  # Not needed, but for clarity
    driver.execute_cdp_cmd("Network.clearBrowserCache", {})

    # Register callback
    driver._devtools_protocol.register_event_listener(
        "Network.requestWillBeSent", handle_request_will_be_sent
    )

    def shutdown_handler(signum=None, frame=None):
        print("🛑 Shutting down browser...")
        driver.quit()
        print("💾 Saving captured requests to selenium_hnap_capture.json...")
        with open("selenium_hnap_capture.json", "w") as f:
            json.dump(captured_requests, f, indent=2)
        print("✅ Done. Captured traffic written to selenium_hnap_capture.json.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    driver.get(args.host)

    try:
        print("✏️   Attempting login with provided credentials...")
        driver.find_element(By.ID, "loginUsername").send_keys(args.username)
        driver.find_element(By.ID, "loginWAP").send_keys(args.password)
        driver.find_element(By.ID, "login").click()
        print("✅ Login form submitted. Waiting for page content...")
    except Exception as e:
        print(f"⚠️  Login step failed: {e}")

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        print("✅ Detected JavaScript-rendered content. Starting traffic capture...")
    except Exception as e:
        print(f"⚠️  Timeout waiting for table content: {e}")

    print("⏳ Capturing traffic for 30 seconds (or press Ctrl+C to stop early)...")
    time.sleep(30)

    shutdown_handler()


if __name__ == "__main__":
    main()
