import json
import signal
import time
import argparse
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


CAPTURE_FILE = "selenium_hnap_capture.json"
LOGIN_URL = "http://192.168.100.1"
USERNAME = "admin"


def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")  # Optional: comment out for visual debugging

    driver = uc.Chrome(options=options, use_subprocess=True)

    # Enable full CDP logging
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Page.enable", {})
    return driver


def wait_for(driver, by, value, timeout=15):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def capture_network_traffic(driver):
    logs = driver.execute_cdp_cmd("Network.getResponseBodyForInterception", {})
    return logs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", required=True, help="Password for modem login")
    parser.add_argument("--host", default=LOGIN_URL, help="Modem IP or URL")
    args = parser.parse_args()

    driver = setup_driver()
    captured_requests = []

    def capture_log(entry):
        captured_requests.append(entry)

    def shutdown_handler(signum, frame):
        print("🛑 Shutting down browser...")
        driver.quit()
        print("💾 Saving captured requests to", CAPTURE_FILE)
        with open(CAPTURE_FILE, "w") as f:
            json.dump(captured_requests, f, indent=2)
        print("✅ Done. Captured traffic written to", CAPTURE_FILE)
        exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    print("🌐 Launching undetected Chrome browser to modem login page...")
    driver.get(args.host)

    # Wait for login form
    print("✏️   Attempting login with provided credentials...")
    try:
        username_input = wait_for(driver, By.ID, "loginUsername")
        password_input = wait_for(driver, By.ID, "loginWAP")
        login_button = wait_for(driver, By.ID, "login")

        username_input.clear()
        username_input.send_keys(USERNAME)
        password_input.clear()
        password_input.send_keys(args.password)
        login_button.click()
    except Exception as e:
        print("❌ Login failed:", e)
        driver.quit()
        return

    print("✅ Login form submitted. Waiting for modem page...")
    time.sleep(3)

    # Confirm table presence
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "dsTable"))
        )
        print("✅ Detected downstream table.")
    except:
        print("⚠️  Downstream table not found yet.")

    # Listen for all network events
    def log_request(request):
        captured_requests.append(request)

    driver.execute_cdp_cmd("Network.setMonitoringXHREnabled", {"enabled": True})
    driver.execute_cdp_cmd("Network.enable", {})

    print("⏳ Capturing for 30 seconds (or Ctrl+C to exit early)...")
    start_time = time.time()
    while time.time() - start_time < 30:
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
                if "Network." in message["method"]:
                    captured_requests.append(message)
            except Exception:
                continue
        time.sleep(1)

    shutdown_handler(None, None)


if __name__ == "__main__":
    main()
