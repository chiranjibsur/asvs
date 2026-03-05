#!/usr/bin/env python3
"""
take_trame_ribbon_screenshot.py — Capture a poster-quality screenshot of the
ASVS trame ribbon visualizer using an offscreen VTK pipeline.

Usage:
    python take_trame_ribbon_screenshot.py

Output:
    poster_screenshots/07_trame_ribbon.png

The script starts a virtual X display (Xvfb) so that VTK's OpenGL renderer
works without a physical display, then imports the trame ribbon VTK pipeline,
loads a representative trajectory frame, and writes a PNG at 1280×720.

Requirements (already in requirements.txt):
    pip install vtk trame trame-vuetify trame-vtk
    apt-get install xvfb   (or equivalent)
"""

import os
import sys
import subprocess
import time
import signal

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "poster_screenshots")
OUTPUT_FILE = "07_trame_ribbon.png"

# Frame and metric to visualise.  Frame 187 has the highest average hotspot
# score in this trajectory (same as screenshot 02 in take_screenshots.py).
CAPTURE_FRAME = 187
CAPTURE_METRIC = "hotspot"

# VTK render-window dimensions (matches trame_ribbon_app defaults)
WIDTH = 1280
HEIGHT = 720

# ---------------------------------------------------------------------------
# Step 1: Start a virtual framebuffer so VTK/OpenGL can render without a
# physical display.  We spawn Xvfb ourselves so the script is self-contained.
# ---------------------------------------------------------------------------

def _start_xvfb(display: str = ":99") -> subprocess.Popen:
    """Start Xvfb on *display* and return the Popen handle."""
    proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", f"{WIDTH}x{HEIGHT}x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Give it a moment to initialise.
    time.sleep(1.5)
    return proc


def _xvfb_display() -> str:
    """Return a DISPLAY string where Xvfb is (or can be) running."""
    return os.environ.get("DISPLAY", ":99")


# ---------------------------------------------------------------------------
# Step 2: Import the trame ribbon app, which builds the VTK pipeline at module
# level (renderer, ribbon filter, mapper, actor, render_window, …).
# ---------------------------------------------------------------------------

def _import_ribbon_app():
    """Import trame_ribbon_app and return its module namespace."""
    # Ensure the repo root is on sys.path
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # trame_ribbon_app creates the trame server object at module level but does
    # NOT call server.start() unless __main__.  Importing is safe.
    import trame_ribbon_app as rapp
    return rapp


# ---------------------------------------------------------------------------
# Step 3: Load the trajectory frame, render, and save.
# ---------------------------------------------------------------------------

def _save_vtk_screenshot(rapp, frame: int, metric: str, output_path: str) -> None:
    """Drive the ribbon pipeline for *frame*/*metric* and write a PNG."""
    import vtk

    # Resize the render window (it was created 1280×720 already but be explicit)
    rapp.render_window.SetSize(WIDTH, HEIGHT)

    # Load trajectory data into the VTK pipeline
    print(f"  Loading frame {frame}, metric '{metric}' …")
    rapp.update_ribbon_geometry(frame, metric)

    # Reset the camera so the whole ribbon is in view
    rapp.renderer.ResetCamera()

    # Render the scene
    rapp.render_window.Render()

    # Capture via vtkWindowToImageFilter
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rapp.render_window)
    w2i.SetScale(1)
    w2i.ReadFrontBufferOff()
    w2i.Update()

    # Write PNG
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(output_path)
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("ASVS Trame Ribbon Screenshot")
    print("=" * 60)
    print(f"Output directory : {OUTPUT_DIR}")
    print(f"Output file      : {OUTPUT_FILE}")
    print()

    xvfb_proc = None
    display = _xvfb_display()

    # Start Xvfb only if there is no real display already available
    if not os.environ.get("DISPLAY"):
        print("[1/3] Starting virtual framebuffer (Xvfb) …")
        xvfb_proc = _start_xvfb(display)
        os.environ["DISPLAY"] = display
        print(f"      DISPLAY={display}\n")
    else:
        print(f"[1/3] Using existing DISPLAY={display}\n")

    try:
        print("[2/3] Initialising VTK ribbon pipeline …")
        rapp = _import_ribbon_app()
        print(f"      Trajectory: {rapp.NUM_FRAMES} frames, {rapp.NUM_RESIDUES} residues\n")

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)

        print("[3/3] Rendering and saving screenshot …")
        _save_vtk_screenshot(rapp, CAPTURE_FRAME, CAPTURE_METRIC, output_path)

        size = os.path.getsize(output_path)
        print(f"\n  ✔  Saved {OUTPUT_FILE}  ({size // 1024} KB)")
        print(f"     Path: {output_path}")

    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb_proc.kill()

    print()


if __name__ == "__main__":
    main()
