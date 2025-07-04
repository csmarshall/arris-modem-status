
import json
import signal
import sys
import time
import warnings
from argparse import ArgumentParser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from seleniumwire import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

warnings.filterwarnings("ignore", category=UserWarning, module='seleniumwire')

# Notes:
# - This script launches Chrome and logs into the modem automatically.
# - It captures all requests (not just HNAP1).
# - If you Ctrl+C, it still writes the capture to selenium_hnap_capture.json.
# - It waits up to 30 seconds for JavaScript-rendered tables to appear.

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

    print("🌐 Launching undetected Chrome browser to modem login page...")
    chrome_options = Options()
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--auto-open-devtools-for-tabs")

    driver = uc.Chrome(options=chrome_options, seleniumwire_options={})

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
