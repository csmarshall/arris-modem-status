import json
import time
import signal
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

captured = []
request_ids = set()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP (no scheme)")
    parser.add_argument("--username", default="admin", help="Modem username")
    parser.add_argument("--password", required=True, help="Modem password")
    parser.add_argument("--duration", type=int, default=30, help="Capture duration in seconds")
    args = parser.parse_args()

    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")

    print("🌐 Launching undetected Chrome...")
    driver = uc.Chrome(options=options)
    driver.set_window_size(1200, 900)

    print("📡 Enabling CDP network logging...")
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})

    def handle_request(params):
        url = params["request"]["url"]
        if True:
            request_ids.add(params["requestId"])
            captured.append({
                "type": "request",
                "requestId": params["requestId"],
                "timestamp": params.get("timestamp"),
                "data": params
            })

    def handle_response(params):
        url = params["response"]["url"]
        request_id = params["requestId"]
        if args.host in url:
            entry = {
                "type": "response",
                "requestId": request_id,
                "timestamp": params.get("timestamp"),
                "data": params
            }
            try:
                body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                entry["body"] = body
            except Exception as e:
                entry["body_error"] = str(e)
            captured.append(entry)

    driver.execute_cdp_cmd("Network.enable", {})

    driver._devtools_listener = driver.execute_cdp_cmd  # keeps alive for undetected_chromedriver
    driver._cdp_listeners = [
        driver.add_cdp_listener("Network.requestWillBeSent", handle_request),
        driver.add_cdp_listener("Network.responseReceived", handle_response),
    ]

    def shutdown_handler(sig, frame):
        print("\n🛑 Caught signal, shutting down...")
        try:
            driver.quit()
        except:
            pass
        with open("modem_cdp_capture.json", "w") as f:
            json.dump(captured, f, indent=2)
        print("✅ Saved capture to modem_cdp_capture.json")
        exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)

    print("🔐 Logging into modem...")
    driver.get(f"http://{args.host}")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "loginUsername"))).send_keys(args.username)
    driver.find_element(By.ID, "loginWAP").send_keys(args.password)
    driver.find_element(By.ID, "login").click()

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "mainContent")))
        print("✅ Logged in and modem page loaded.")
    except:
        print("⚠️  Login might have failed. Continuing capture...")

    print(f"⏳ Capturing all modem traffic for {args.duration} seconds...")
    time.sleep(args.duration)

    print("🛑 Done. Shutting down...")
    driver.quit()
    with open("modem_cdp_capture.json", "w") as f:
        json.dump(captured, f, indent=2)
    print("✅ Capture saved to modem_cdp_capture.json")

if __name__ == "__main__":
    main()
