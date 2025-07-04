import json
import signal
import sys
import time
import warnings
from argparse import ArgumentParser

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Notes:
# - This script launches a stealth Chrome instance using undetected-chromedriver.
# - It automatically logs into the Arris modem UI using the provided credentials.
# - It captures ALL HTTP/S requests made during the session (not just HNAP1).
# - Press Ctrl+C to exit early — it will still write the captured requests to disk.
# - Waits up to 30 seconds for the JavaScript-rendered table to appear.

def main():
    parser = ArgumentParser(description="Capture modem traffic using Selenium.")
    parser.add_argument("--host", default="https://192.168.100.1", help="Modem host URL")
    parser.add_argument("--username", default="admin", help="Modem username")
    parser.add_argument("--password", required=True, help="Modem password")
    args = parser.parse_args()

    captured_requests = []

    def shutdown_handler(signum, frame):
        print("\n🛑 Shutting down browser...")
        driver.quit()
        print("💾 Saving captured requests to selenium_hnap_capture.json...")
        with open("selenium_hnap_capture.json", "w") as f:
            json.dump(captured_requests, f, indent=2)
        print("✅ Done. Captured traffic written to selenium_hnap_capture.json.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    warnings.filterwarnings("ignore", category=UserWarning, module='seleniumwire')

    print("🌐 Launching undetected Chrome browser to modem login page...")

    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--auto-open-devtools-for-tabs")

    # Launch the undetected Chrome driver
    driver = uc.Chrome(options=options, headless=False, use_subprocess=True)

    driver.get(args.host)

    try:
        print("✏️  Attempting login with provided credentials...")
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

    print("📡 Extracting captured request data...")
    for request in driver.requests:
        if request.response:
            captured_requests.append({
                "url": request.url,
                "method": request.method,
                "status_code": request.response.status_code,
                "headers": dict(request.headers),
                "response_headers": dict(request.response.headers),
                "body": request.body.decode(errors='replace') if request.body else "",
            })

    shutdown_handler(None, None)


if __name__ == "__main__":
    main()
