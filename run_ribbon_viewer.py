#!/usr/bin/env python
"""
Simple script to run the Trame Ribbon Viewer locally.

Usage:
    python run_ribbon_viewer.py

This will start the server and open it in your default browser.
The viewer will be available at http://localhost:9887

Features:
- Animation playback (play/pause/step)
- Clipping planes (X/Y/Z axis)
- Contact visualization
- Distance/angle measurements
- Residue info cards with ML metrics
- Hover tooltips
- Bookmarks
- Export snapshots
"""

import os
import sys
import webbrowser
import threading
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the Trame ribbon viewer."""
    print("=" * 60)
    print("ASVS Trame Ribbon Viewer")
    print("=" * 60)
    print()
    print("Starting server...")
    print()
    print("Features available:")
    print("  ▶ Animation: Play/pause trajectory with speed control")
    print("  ✂ Clipping: Slice through ribbon on X/Y/Z axis")
    print("  🔗 Contacts: Show top residue-residue contacts")
    print("  📏 Measure: Click residues to measure distance/angle")
    print("  ℹ Info: Click residue to see ML metrics")
    print("  🔖 Bookmarks: Save/load camera positions")
    print("  📷 Snapshot: Export current view as PNG")
    print()
    
    from trame_ribbon_app import start_ribbon_server, DEFAULT_TRAME_HOST, DEFAULT_TRAME_PORT
    
    host = os.environ.get("ASVS_TRAME_RIBBON_HOST", DEFAULT_TRAME_HOST)
    port = int(os.environ.get("ASVS_TRAME_RIBBON_PORT", DEFAULT_TRAME_PORT))
    
    url = f"http://{host}:{port}"
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        print(f"\nOpening browser at {url}")
        webbrowser.open(url)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"Server starting at {url}")
    print("Press Ctrl+C to stop the server")
    print()
    
    try:
        start_ribbon_server(address=host, port=port, background=False)
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
