import json
import time
import signal
import argparse
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc

captured_events = []

def signal_handler(sig, frame):
    print("\n🛑 Stopping capture...")
    raise KeyboardInterrupt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--password', required=True)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    print("🌐 Launching undetected Chrome...")
    options = uc.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    driver = uc.Chrome(options=options, use_subprocess=True)
    driver.set_page_load_timeout(15)

    driver.execute_cdp_cmd("Network.enable", {})
    print("📡 CDP Network logging enabled.")

    requests = {}

    def capture_event(method, params):
        if method == "Network.requestWillBeSent":
            requests[params["requestId"]] = {
                "request": params["request"],
                "requestId": params["requestId"],
                "timestamp": time.time(),
                "url": params["request"]["url"]
            }
        elif method == "Network.responseReceived":
            req_id = params["requestId"]
            if req_id in requests:
                requests[req_id]["response"] = params["response"]

    driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    driver.execute_cdp_cmd("Page.enable", {})

    driver.cdp_event_listener = capture_event

    print("🔐 Navigating to modem login page...")
    driver.get("https://192.168.100.1")

    try:
        print("🔐 Waiting for login form...")
        user_field = driver.find_element(By.ID, "loginUsername")
        pass_field = driver.find_element(By.ID, "loginWAP")
        login_button = driver.find_element(By.ID, "login")

        user_field.send_keys("admin")
        pass_field.send_keys(args.password)
        login_button.click()
    except Exception as e:
        print(f"❌ Login error: {e}")

    print("⏳ Capturing network traffic for 30 seconds...")
    time.sleep(30)

    print("💾 Attempting to retrieve response bodies...")
    for req_id, data in requests.items():
        try:
            body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": req_id})
            data["response_body"] = body
        except Exception:
            data["response_body"] = {"error": "Body unavailable"}

    print("🛑 Shutting down...")
    driver.quit()

    with open("modem_cdp_capture.json", "w") as f:
        json.dump(list(requests.values()), f, indent=2)

    print("✅ Capture saved to modem_cdp_capture.json")

if __name__ == "__main__":
    main()
