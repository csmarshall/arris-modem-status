import json
import os
import signal
import subprocess
import sys
import time
from argparse import ArgumentParser
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

# Output file
CAPTURE_FILE = "selenium_hnap_capture.json"

# mitmdump options
MITMDUMP_PATH = os.path.join(os.environ.get("VIRTUAL_ENV", ""), "bin", "mitmdump")
MITM_PORT = 8080
MITM_LOG = "mitmproxy.log"

mitm_process = None

def start_mitmdump():
    global mitm_process
    print("🚀 Starting mitmdump in background...")
    if not os.path.isfile(MITMDUMP_PATH):
        raise FileNotFoundError("Could not find mitmdump in virtualenv bin/ directory.")

    # Start mitmdump with cert verification disabled
    mitm_process = subprocess.Popen([
        MITMDUMP_PATH,
        "--listen-port", str(MITM_PORT),
        "--mode", "regular",
        "--set", "ssl_insecure=true",
        "--set", "connection_strategy=lazy",
        "-w", CAPTURE_FILE
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(2)
    if mitm_process.poll() is not None:
        stdout, stderr = mitm_process.communicate()
        print(f"❌ mitmdump failed to start.\nstdout:\n{stdout.decode()}\nstderr:\n{stderr.decode()}")
        raise RuntimeError("mitmdump did not start correctly")
    print("✅ mitmdump started successfully.")

def stop_mitmdump():
    global mitm_process
    if mitm_process and mitm_process.poll() is None:
        print("🛑 Stopping mitmdump...")
        mitm_process.terminate()
        mitm_process.wait()
        print("✅ mitmdump stopped.")

def shutdown_handler(signum, frame):
    stop_mitmdump()
    print(f"📦 Traffic written to {CAPTURE_FILE}")
    sys.exit(0)

def main():
    parser = ArgumentParser(description="Capture modem traffic via mitmdump + undetected Chrome")
    parser.add_argument("--host", default="https://192.168.100.1", help="Modem host")
    parser.add_argument("--username", default="admin", help="Username for modem")
    parser.add_argument("--password", required=True, help="Password for modem")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, shutdown_handler)

    start_mitmdump()

    print("🌐 Launching undetected Chrome with proxy settings...")
    options = Options()
    options.add_argument(f"--proxy-server=http://127.0.0.1:{MITM_PORT}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options, headless=False, use_subprocess=True)
    driver.get(args.host)

    print("✏️   Logging into modem...")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "loginUsername"))).send_keys(args.username)
        driver.find_element(By.ID, "loginWAP").send_keys(args.password)
        driver.find_element(By.ID, "login").click()
        print("✅ Logged in successfully.")
    except Exception as e:
        print(f"⚠️ Login failed or already logged in: {e}")

    try:
        print("⏳ Capturing traffic for 30 seconds (or Ctrl+C to cancel early)...")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, "//table")))
    except Exception:
        print("⚠️ JavaScript-rendered content may not have loaded.")

    time.sleep(30)
    driver.quit()
    shutdown_handler(None, None)

if __name__ == "__main__":
    main()
