#!/usr/bin/env python3
"""
Enhanced Deep Capture v4.0 - Dual Export
=========================================
ENHANCED VERSION that ensures both HAR and JSON files are properly exported.

Exports:
- deep_capture.har (for Chrome DevTools analysis)
- deep_capture.json (for Python analysis)

Usage:
    python enhanced_deep_capture.py --password "your-password"
"""

import argparse
import asyncio
import json
import logging
import os
import time
from datetime import datetime

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EnhancedDeepCapture:
    """Enhanced deep capture with guaranteed dual export"""

    def __init__(self, host="192.168.100.1", username="admin", password=""):
        self.host = host
        self.username = username
        self.password = password
        self.base_url = f"https://{host}"

        # Output file paths
        self.har_file = "deep_capture.har"
        self.json_file = "deep_capture.json"

        # Capture storage
        self.all_requests = []
        self.cookie_timeline = []
        self.console_logs = []
        self.storage_snapshots = []
        self.timing_data = []
        self.last_request_time = None

        logger.info(f"🚀 Starting {__file__} v4.0 - Enhanced Deep Capture")
        logger.info(f"📅 Session: {datetime.now().isoformat()}")
        logger.info(f"📁 HAR output: {os.path.abspath(self.har_file)}")
        logger.info(f"📁 JSON output: {os.path.abspath(self.json_file)}")
        logger.info("=" * 60)

    async def capture_session(self):
        """Capture complete session with guaranteed dual export"""

        logger.info("🔍 Starting enhanced capture with dual export...")

        async with async_playwright() as p:
            # Launch browser with HAR recording
            browser = await p.chromium.launch(headless=False, args=["--enable-logging", "--v=1"])

            # CRITICAL: Set up HAR recording
            context = await browser.new_context(
                ignore_https_errors=True, record_har_path=self.har_file, record_har_url_filter="**/*"
            )

            page = await context.new_page()

            # Set up all event listeners
            self._setup_event_listeners(page)

            try:
                # Execute the complete capture sequence
                await self._execute_capture_sequence(page)

                logger.info("✅ Capture sequence completed")

            except Exception as e:
                logger.error(f"❌ Error during capture: {e}")
                await page.screenshot(path="enhanced_capture_error.png")

            finally:
                # CRITICAL: Ensure HAR file is written
                logger.info("💾 Finalizing HAR export...")
                await context.close()
                await browser.close()

                # Verify HAR file was created
                if os.path.exists(self.har_file):
                    har_size = os.path.getsize(self.har_file)
                    logger.info(f"✅ HAR file created: {self.har_file} ({har_size} bytes)")
                else:
                    logger.error(f"❌ HAR file not created: {self.har_file}")

        # Prepare JSON export data
        capture_data = {
            "timestamp": datetime.now().isoformat(),
            "requests": self.all_requests,
            "cookies": self.cookie_timeline,
            "console": self.console_logs,
            "storage": self.storage_snapshots,
            "timing": self.timing_data,
            "files_created": {
                "har_file": self.har_file,
                "har_exists": os.path.exists(self.har_file),
                "har_size": os.path.getsize(self.har_file) if os.path.exists(self.har_file) else 0,
            },
        }

        # Export JSON file
        logger.info("💾 Exporting JSON data...")
        try:
            with open(self.json_file, "w") as f:
                json.dump(capture_data, f, indent=2)

            json_size = os.path.getsize(self.json_file)
            logger.info(f"✅ JSON file created: {self.json_file} ({json_size} bytes)")

        except Exception as e:
            logger.error(f"❌ Failed to create JSON file: {e}")

        return capture_data

    def _setup_event_listeners(self, page):
        """Set up all event listeners for comprehensive capture"""

        # Console capture
        page.on(
            "console",
            lambda msg: self.console_logs.append(
                {"timestamp": datetime.now().isoformat(), "level": msg.type, "text": msg.text, "location": msg.location}
            ),
        )

        # Request capture with timing
        def handle_request(request):
            current_time = time.time()
            timing_delta = None

            if self.last_request_time:
                timing_delta = current_time - self.last_request_time

            self.last_request_time = current_time

            request_data = {
                "type": "request",
                "timestamp": datetime.now().isoformat(),
                "timing_delta_ms": timing_delta * 1000 if timing_delta else 0,
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            }

            self.all_requests.append(request_data)

            if "/HNAP1/" in request.url:
                logger.info(
                    f"📤 HNAP Request: {request.method} (∆{timing_delta:.1f}s)"
                    if timing_delta
                    else f"📤 HNAP Request: {request.method}"
                )

        def handle_response(response):
            response_data = {
                "type": "response",
                "timestamp": datetime.now().isoformat(),
                "method": response.request.method,
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
            }

            self.all_requests.append(response_data)

            if "/HNAP1/" in response.url:
                logger.info(f"📥 HNAP Response: {response.status}")

                # Capture response body
                async def capture_body():
                    try:
                        body = await response.text()
                        response_data["content"] = body
                        if len(body) > 50:
                            logger.info(f"   Body: {body[:100]}...")
                    except Exception as e:
                        logger.warning(f"   Could not capture body: {e}")

                asyncio.create_task(capture_body())

        page.on("request", handle_request)
        page.on("response", handle_response)

    async def _execute_capture_sequence(self, page):
        """Execute the complete capture sequence"""

        # Step 1: Initial page load
        logger.info("📄 Step 1: Loading login page...")
        await page.goto(f"{self.base_url}/Login.html", wait_until="networkidle")
        await self._capture_cookies(page)
        await self._capture_storage(page)

        # Step 2: Login process
        logger.info("\n🔑 Step 2: Performing login...")
        await page.fill("#loginUsername", self.username)
        await page.fill("#loginWAP", self.password)

        await self._capture_cookies(page)

        # Click login and wait
        await page.click("#login")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        await self._capture_cookies(page)
        await self._capture_storage(page)

        current_url = page.url
        logger.info(f"   ✅ Post-login URL: {current_url}")

        # Step 3: Load connection status page
        logger.info("\n📊 Step 3: Loading connection status page...")
        await page.goto(f"{self.base_url}/Cmconnectionstatus.html", wait_until="networkidle")
        await self._capture_cookies(page)
        await self._capture_storage(page)

        # Step 4: Wait for automatic requests
        logger.info("\n⏳ Step 4: Waiting for automatic data requests...")
        await asyncio.sleep(10)  # Wait longer to capture all automatic requests

        # Step 5: Capture final state
        await self._capture_cookies(page)
        await self._capture_storage(page)

        logger.info("✅ Capture sequence complete!")

    async def _capture_cookies(self, page):
        """Capture current cookie state"""
        cookies = await page.context.cookies()
        self.cookie_timeline.append({"timestamp": datetime.now().isoformat(), "cookies": cookies})
        logger.info(f"🍪 Cookies captured: {len(cookies)} total")

    async def _capture_storage(self, page):
        """Capture browser storage state"""
        try:
            local_storage = await page.evaluate("() => Object.entries(localStorage)")
            session_storage = await page.evaluate("() => Object.entries(sessionStorage)")

            self.storage_snapshots.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "localStorage": dict(local_storage) if local_storage else {},
                    "sessionStorage": dict(session_storage) if session_storage else {},
                }
            )

            if local_storage or session_storage:
                logger.info(
                    f"💾 Storage captured: localStorage={len(local_storage)}, sessionStorage={len(session_storage)}"
                )
        except Exception as e:
            logger.warning(f"Could not capture storage: {e}")

    def verify_exports(self):
        """Verify both export files were created successfully"""

        logger.info("\n🔍 VERIFYING EXPORTS")
        logger.info("=" * 40)

        # Check HAR file
        if os.path.exists(self.har_file):
            har_size = os.path.getsize(self.har_file)
            logger.info(f"✅ HAR file: {self.har_file} ({har_size:,} bytes)")

            # Try to validate HAR structure
            try:
                with open(self.har_file, "r") as f:
                    har_data = json.load(f)
                    entries = har_data.get("log", {}).get("entries", [])
                    logger.info(f"   📊 HAR contains {len(entries)} network entries")
            except Exception as e:
                logger.warning(f"   ⚠️ HAR file may be corrupted: {e}")
        else:
            logger.error(f"❌ HAR file missing: {self.har_file}")

        # Check JSON file
        if os.path.exists(self.json_file):
            json_size = os.path.getsize(self.json_file)
            logger.info(f"✅ JSON file: {self.json_file} ({json_size:,} bytes)")

            # Try to validate JSON structure
            try:
                with open(self.json_file, "r") as f:
                    json_data = json.load(f)
                    requests = json_data.get("requests", [])
                    logger.info(f"   📊 JSON contains {len(requests)} captured requests")
            except Exception as e:
                logger.warning(f"   ⚠️ JSON file may be corrupted: {e}")
        else:
            logger.error(f"❌ JSON file missing: {self.json_file}")

        # Usage instructions
        logger.info("\n💡 USAGE INSTRUCTIONS:")
        logger.info(f"📊 Chrome DevTools: Import {self.har_file}")
        logger.info(f"🐍 Python analysis: python session_state_analyzer.py --capture {self.json_file}")


async def main():
    parser = argparse.ArgumentParser(description="Enhanced Deep Capture v4.0")
    parser.add_argument("--host", default="192.168.100.1", help="Modem IP address")
    parser.add_argument("--username", default="admin", help="Login username")
    parser.add_argument("--password", required=True, help="Login password")

    args = parser.parse_args()

    capturer = EnhancedDeepCapture(args.host, args.username, args.password)

    try:
        # Perform the capture
        capture_data = await capturer.capture_session()

        # Verify exports
        capturer.verify_exports()

        logger.info("\n🎉 ENHANCED CAPTURE COMPLETE!")
        logger.info("📁 Files created:")
        logger.info(f"   - {capturer.har_file} (for Chrome DevTools)")
        logger.info(f"   - {capturer.json_file} (for Python analysis)")

        logger.info("\n💡 NEXT STEPS:")
        logger.info("1. Open Chrome DevTools and import the HAR file")
        logger.info("2. Run the session state analyzer on the JSON file")
        logger.info("3. Wait 30+ minutes before testing new implementations")

    except Exception as e:
        logger.error(f"❌ Enhanced capture failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
