import time
import json
import signal
import sys
import argparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Global for graceful shutdown
driver = None

def shutdown_handler(signum, frame):
    print("🛑 Shutting down browser...")
    try:
        if driver:
            print("💾 Retrieving JS-captured requests...")
            captured = driver.execute_script("return window._capturedRequests || []")
            with open("selenium_hnap_capture.json", "w") as f:
                json.dump(captured, f, indent=2)
            print("✅ Done. Captured traffic written to selenium_hnap_capture.json.")
            driver.quit()
    except Exception as e:
        print(f"⚠️ Error during shutdown: {e}")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://192.168.100.1", help="Modem IP or URL")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    global driver

    print("🌐 Launching undetected Chrome browser to modem login page...")

    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")  # Accept self-signed certs
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    driver = uc.Chrome(options=options, headless=False)
    driver.get(args.host)

    print("✏️   Attempting login with provided credentials...")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "loginUsername"))
        )
        username_field = driver.find_element(By.ID, "loginUsername")
        password_field = driver.find_element(By.ID, "loginWAP")
        login_button = driver.find_element(By.ID, "login")

        username_field.send_keys(args.username)
        password_field.send_keys(args.password)
        driver.execute_script("arguments[0].click();", login_button)
        print("✅ Login form submitted. Waiting for modem page...")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print("✅ Page loaded.")
    except Exception as e:
        print("❌ Failed to locate login form.")
        shutdown_handler(None, None)

    # Inject JavaScript to capture all fetch/XHR requests
    js_snippet = """
    (function() {
        window._capturedRequests = [];
        const originalXHROpen = XMLHttpRequest.prototype.open;
        const originalSend = XMLHttpRequest.prototype.send;
        XMLHttpRequest.prototype.open = function(method, url) {
            this._requestUrl = url;
            return originalXHROpen.apply(this, arguments);
        };
        XMLHttpRequest.prototype.send = function() {
            const xhr = this;
            const url = this._requestUrl;
            const payload = arguments[0];
            const startTime = performance.now();
            xhr.addEventListener('loadend', function() {
                const endTime = performance.now();
                window._capturedRequests.push({
                    url,
                    method: xhr.method || "POST",
                    status: xhr.status,
                    duration: endTime - startTime,
                    response: xhr.responseText,
                    payload: payload || null
                });
            });
            return originalSend.apply(this, arguments);
        };

        const originalFetch = window.fetch;
        window.fetch = function() {
            const args = arguments;
            const startTime = performance.now();
            return originalFetch.apply(this, arguments).then(res => {
                const endTime = performance.now();
                res.clone().text().then(body => {
                    window._capturedRequests.push({
                        url: res.url,
                        status: res.status,
                        duration: endTime - startTime,
                        response: body,
                        method: (args[1] && args[1].method) || "GET",
                        payload: (args[1] && args[1].body) || null
                    });
                });
                return res;
            });
        };
    })();
    """

    driver.execute_script(js_snippet)
    print("📦 Injected JS to monitor XHR/fetch requests.")
    print("⏳ Capturing for 30 seconds (or Ctrl+C to exit early)...")

    time.sleep(30)
    shutdown_handler(None, None)

if __name__ == "__main__":
    main()
