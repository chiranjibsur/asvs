#!/usr/bin/env python3
"""
take_screenshots.py — Poster-quality screenshot automation for the ASVS visualizer.

Usage:
    python take_screenshots.py

Output:
    poster_screenshots/
        01_ribbon_overview.png
        02_hotspot_ball_stick.png
        03_signal_anomaly.png
        04_signal_rmsf.png
        05_time_navigation.png
        06_hotspot_closeup.png

Requirements:
    pip install playwright
    playwright install chromium

The script starts the Flask development server automatically and takes screenshots
of each view using a headless Chromium browser at high resolution.
"""

import os
import sys
import time
import signal
import subprocess
import threading

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "poster_screenshots")
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5001            # use a dedicated port to avoid conflicts
BASE_URL = f"http://{FLASK_HOST}:{FLASK_PORT}"

# Frame indices of interest (computed from viewer/hotspots_residue.json)
HIGH_ANOMALY_FRAME = 51      # frame with highest average anomaly score
HIGH_HOTSPOT_FRAME = 187     # frame with highest average hotspot score
COMPARISON_FRAME_A = 10      # earlier frame for time-navigation comparison
COMPARISON_FRAME_B = 90      # later  frame for time-navigation comparison

# Viewport dimensions — wide enough for ≥ 3000 px screenshots
VIEWPORT_WIDTH  = 3200
VIEWPORT_HEIGHT = 1800

# How long (ms) to wait for Three.js to finish rendering after initial page load.
# The heatmap loop makes ~388 sequential HTTP requests (hotspot+anomaly per frame).
# With the threading.Lock in TrajectoryAdapter and waitress as the WSGI server,
# requests are handled safely.  We still wait for rendering to complete.
RENDER_WAIT_MS = 8000

# Total wait for ball-and-stick pages which also load three.min.js (600 KB).
# Applied instead of RENDER_WAIT_MS (not in addition to it) for heavy pages.
HEAVY_PAGE_WAIT_MS = RENDER_WAIT_MS + 5000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def start_flask_server():
    """Start app.py in a subprocess and return the Popen object."""
    env = os.environ.copy()
    env["FLASK_APP"] = "app.py"
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=os.path.dirname(__file__),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return proc


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Poll url until it responds or timeout elapses."""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def wait_for_render(page, extra_ms: int = 0):
    """Wait for the page to finish rendering.

    The app continuously polls the server so 'networkidle' never fires.
    We use a time-based wait long enough to cover the 194-frame heatmap loop
    (which fetches ~388 HTTP requests) before we close the context.
    """
    wait_ms = max(extra_ms, RENDER_WAIT_MS)
    page.wait_for_timeout(wait_ms)


def navigate_to_frame(page, frame_idx: int, slider_selector: str):
    """Set a range slider to a given frame and wait for the renderer."""
    # Use JavaScript to set the slider value and fire the 'input' event so the
    # visualiser picks it up.  We do NOT also click the "Load frame" button to
    # avoid calling loadFrame() twice (slider oninput + button click), which
    # would issue two concurrent MDAnalysis trajectory reads and cause a race
    # condition that can deadlock / crash Werkzeug's dev server.
    page.evaluate(
        f"""
        (function() {{
            var s = document.querySelector('{slider_selector}');
            if (!s) return;
            s.value = {frame_idx};
            s.dispatchEvent(new Event('input', {{bubbles: true}}));
        }})();
        """
    )
    page.wait_for_timeout(RENDER_WAIT_MS)


def select_metric(page, metric_value: str):
    """Change the metric selector and wait for the scene to update."""
    page.select_option("#metricSelect", metric_value)
    page.wait_for_timeout(RENDER_WAIT_MS)


def zoom_camera(page, zoom_factor: float):
    """Simulate a pinch/scroll zoom on the canvas to zoom in or out."""
    canvas = page.locator("canvas").first
    box = canvas.bounding_box()
    if not box:
        return
    cx = box["x"] + box["width"]  / 2
    cy = box["y"] + box["height"] / 2
    # Dispatch wheel events interpreted as zoom by OrbitControls / TrackballControls
    delta = -120 * zoom_factor          # negative = zoom in
    page.evaluate(
        f"""
        (function() {{
            var canvas = document.querySelector('canvas');
            if (!canvas) return;
            var evt = new WheelEvent('wheel', {{
                deltaY: {delta},
                clientX: {cx},
                clientY: {cy},
                bubbles: true
            }});
            canvas.dispatchEvent(evt);
        }})();
        """
    )
    page.wait_for_timeout(1500)


def save_screenshot(page, filename: str):
    """Save a full-page screenshot to OUTPUT_DIR."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    page.screenshot(path=path, full_page=False, type="png")
    size = os.path.getsize(path)
    print(f"  ✔  Saved {filename}  ({size // 1024} KB)")
    return path


def wait_for_server_ready(base_url: str, timeout: int = 15) -> bool:
    """Poll a simple endpoint until the server responds (server-side readiness check)."""
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{base_url}/", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    # Start the app with waitress — a production-grade WSGI server that handles
    # abrupt browser-context closes (broken TCP connections) gracefully, unlike
    # Werkzeug's dev server which crashes on a broken-socket write.
    patch_cmd = (
        "import app as _app; "
        "from waitress import serve; "
        f"serve(_app.app, host='{FLASK_HOST}', port={FLASK_PORT}, threads=8)"
    )

    print("=" * 60)
    print("ASVS Poster Screenshot Generator")
    print("=" * 60)
    print(f"Output directory : {OUTPUT_DIR}")
    print(f"Server           : {BASE_URL}")
    print()

    # -- 1. Start Flask server -------------------------------------------
    print("[1/3] Starting Flask server …")
    env = os.environ.copy()
    server_proc = subprocess.Popen(
        [sys.executable, "-c", patch_cmd],
        cwd=os.path.dirname(__file__) or ".",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    if not wait_for_server(BASE_URL, timeout=30):
        print("ERROR: Flask server did not start within 30 seconds.")
        server_proc.kill()
        sys.exit(1)
    print("      Server ready.\n")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            print("[2/3] Taking screenshots …\n")
            os.makedirs(OUTPUT_DIR, exist_ok=True)

            def open_fresh_page():
                """Open a fresh browser context and page for each screenshot."""
                ctx = browser.new_context(
                    viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                    device_scale_factor=1,
                )
                p = ctx.new_page()
                p.set_default_timeout(60000)
                p.on("console", lambda m: None)
                return ctx, p

            def screenshot_page(url, filename, slider_id, metric, frame_idx, zoom=0,
                                heavy_page=False):
                """
                Open a fresh browser context, load the given URL, configure it,
                save a screenshot, then close the context.

                For "heavy" pages (ball-and-stick) we wait longer before closing so
                that three.min.js (600 KB) and the 194-frame heatmap loop finish
                loading.  Closing the browser context while those transfers are still
                in-flight breaks Werkzeug's dev-server socket, making it unresponsive.
                """
                # Wait for the server to be responsive before each screenshot.
                if not wait_for_server_ready(BASE_URL, timeout=30):
                    print(f"  WARNING: server not ready before {filename}")
                ctx, p = open_fresh_page()
                try:
                    p.goto(url, wait_until="commit")
                    # Heavy pages (ball-and-stick) load three.min.js (600 KB) on
                    # top of the normal 388-request heatmap loop, so they need
                    # more time.  HEAVY_PAGE_WAIT_MS already includes RENDER_WAIT_MS.
                    initial_wait = HEAVY_PAGE_WAIT_MS if heavy_page else RENDER_WAIT_MS
                    p.wait_for_timeout(initial_wait)
                    if metric:
                        select_metric(p, metric)
                    if frame_idx is not None:
                        navigate_to_frame(p, frame_idx, slider_id)
                    if zoom:
                        zoom_camera(p, zoom)
                    save_screenshot(p, filename)
                finally:
                    ctx.close()

            # ----------------------------------------------------------------
            # 01 — Points overview — hotspot coloring
            # ----------------------------------------------------------------
            print("Screenshot 01: Points overview — hotspot coloring …")
            screenshot_page(
                url=f"{BASE_URL}/viewer",
                filename="01_ribbon_overview.png",
                slider_id="#frameSlider",
                metric="hotspot",
                frame_idx=HIGH_HOTSPOT_FRAME,
            )

            # ----------------------------------------------------------------
            # 02 — Hotspot frame — Ball-and-Stick
            # ----------------------------------------------------------------
            print("Screenshot 02: Hotspot frame — Ball-and-Stick …")
            screenshot_page(
                url=f"{BASE_URL}/viewer/ballstick",
                filename="02_hotspot_ball_stick.png",
                slider_id="#slider",
                metric="hotspot",
                frame_idx=HIGH_HOTSPOT_FRAME,
                zoom=5,
                heavy_page=True,
            )

            # ----------------------------------------------------------------
            # 03 — Signal: anomaly
            # ----------------------------------------------------------------
            print("Screenshot 03: Signal switch — Anomaly …")
            screenshot_page(
                url=f"{BASE_URL}/viewer",
                filename="03_signal_anomaly.png",
                slider_id="#frameSlider",
                metric="anomaly",
                frame_idx=HIGH_ANOMALY_FRAME,
            )

            # ----------------------------------------------------------------
            # 04 — Signal: RMSF
            # ----------------------------------------------------------------
            print("Screenshot 04: Signal switch — RMSF …")
            screenshot_page(
                url=f"{BASE_URL}/viewer",
                filename="04_signal_rmsf.png",
                slider_id="#frameSlider",
                metric="rmsf",
                frame_idx=COMPARISON_FRAME_B,
            )

            # ----------------------------------------------------------------
            # 05 — Time navigation (two frames tiled side-by-side)
            # ----------------------------------------------------------------
            print("Screenshot 05: Time navigation — frames A and B …")
            path_a = os.path.join(OUTPUT_DIR, "_tmp_frame_a.png")
            path_b = os.path.join(OUTPUT_DIR, "_tmp_frame_b.png")

            if not wait_for_server_ready(BASE_URL, timeout=30):
                print("  WARNING: server not ready before screenshot 05")
            nav_ctx, p = open_fresh_page()
            try:
                p.goto(f"{BASE_URL}/viewer", wait_until="commit")
                wait_for_render(p, RENDER_WAIT_MS)
                select_metric(p, "hotspot")

                navigate_to_frame(p, COMPARISON_FRAME_A, "#frameSlider")
                p.screenshot(path=path_a, full_page=False, type="png")

                navigate_to_frame(p, COMPARISON_FRAME_B, "#frameSlider")
                p.screenshot(path=path_b, full_page=False, type="png")
            finally:
                nav_ctx.close()

            try:
                from PIL import Image
                img_a = Image.open(path_a)
                img_b = Image.open(path_b)
                w = img_a.width + img_b.width
                h = max(img_a.height, img_b.height)
                composite = Image.new("RGB", (w, h), color=(15, 16, 18))
                composite.paste(img_a, (0, 0))
                composite.paste(img_b, (img_a.width, 0))
                out = os.path.join(OUTPUT_DIR, "05_time_navigation.png")
                composite.save(out, "PNG")
                size = os.path.getsize(out)
                print(f"  ✔  Saved 05_time_navigation.png  ({size // 1024} KB)")
            except ImportError:
                import shutil
                shutil.copy(path_b, os.path.join(OUTPUT_DIR, "05_time_navigation.png"))
                print("  ✔  Saved 05_time_navigation.png  (PIL unavailable — single frame)")
            finally:
                for tmp in (path_a, path_b):
                    if os.path.exists(tmp):
                        os.remove(tmp)

            # ----------------------------------------------------------------
            # 06 — Close-up: Ball-and-Stick, high-anomaly frame, zoomed in
            # ----------------------------------------------------------------
            print("Screenshot 06: Close-up — Ball-and-Stick high-anomaly region …")
            screenshot_page(
                url=f"{BASE_URL}/viewer/ballstick",
                filename="06_hotspot_closeup.png",
                slider_id="#slider",
                metric="anomaly",
                frame_idx=HIGH_ANOMALY_FRAME,
                zoom=10,
                heavy_page=True,
            )

            browser.close()

        print()
        print("[3/3] All screenshots saved to:", OUTPUT_DIR)
        print()
        for fname in sorted(os.listdir(OUTPUT_DIR)):
            if fname.endswith(".png"):
                fpath = os.path.join(OUTPUT_DIR, fname)
                size  = os.path.getsize(fpath)
                print(f"  {fname}  —  {size // 1024} KB")

    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()


if __name__ == "__main__":
    main()
