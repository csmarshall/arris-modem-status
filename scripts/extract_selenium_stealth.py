import json
import signal
import sys
import time
import warnings
from argparse import ArgumentParser
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

warnings.filterwarnings("ignore", category=UserWarning, module='seleniumwire')


def apply_stealth(driver):
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // spoof the WebGL vendor
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel Iris OpenGL Engine';
            return getParameter(parameter);
        };
        window.chrome = { runtime: {} };
        """,
    })


def main():
    parser = ArgumentParser(description="Stealth capture of modem traffic with Selenium Wire.")
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

    print("🌐 Launching Chrome with stealth options...")
    chrome_options = Options()
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-site-isolation-trials")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,1000")
    chrome_options.add_argument("--user-data-dir=/tmp/arris_stealth_profile")

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options
    )

    apply_stealth(driver)

    driver.get(args.host)

    try:
        print("✏️  Logging in...")
        driver.find_element(By.ID, "loginUsername").send_keys(args.username)
        driver.find_element(By.ID, "loginWAP").send_keys(args.password)
        driver.find_element(By.ID, "login").click()
        print("✅ Login form submitted.")
    except Exception as e:
        print(f"⚠️  Login step failed: {e}")

    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        print("✅ Detected JS-rendered tables.")
    except Exception as e:
        print(f"⚠️  Table render timeout: {e}")

    print("⏳ Capturing traffic for 30 seconds (or Ctrl+C to cancel early)...")
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
