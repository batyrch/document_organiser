#!/usr/bin/env python3
"""
Desktop launcher for Document Organizer.

This script:
1. Starts the Streamlit server in-process
2. Opens the user's default browser to the app
3. Handles graceful shutdown

Used by PyInstaller to create a standalone executable.
"""

import os
import sys
import time
import socket
import signal
import webbrowser
import threading
from pathlib import Path

# Required for PyInstaller multiprocessing support
from multiprocessing import freeze_support


def get_free_port():
    """Find a free port to run the server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_server(host, port, timeout=30):
    """Wait for the server to become available."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((host, port))
                return True
        except (socket.error, socket.timeout):
            time.sleep(0.5)
    return False


def get_app_dir():
    """Get the directory containing the application files."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller bundle)
        return Path(sys._MEIPASS)
    else:
        # Running as script
        return Path(__file__).parent.parent


def main():
    # Required for PyInstaller on Windows
    freeze_support()

    app_dir = get_app_dir()
    ui_path = app_dir / "ui.py"

    # Ensure we have the UI file
    if not ui_path.exists():
        print(f"Error: Could not find ui.py at {ui_path}")
        print("The application may be corrupted. Please re-download.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Find a free port
    port = get_free_port()
    host = "localhost"
    local_url = f"http://{host}:{port}"

    # Determine the URL to open
    local_app_html = app_dir / "app.html"
    if local_app_html.exists():
        app_url = f"file://{local_app_html}?port={port}"
    else:
        app_url = local_url

    print(f"Starting Document Organizer...")
    print(f"App directory: {app_dir}")
    print(f"Server will be available at: {local_url}")

    # Set Streamlit configuration via environment
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = host
    os.environ["STREAMLIT_BROWSER_SERVER_ADDRESS"] = host
    os.environ["STREAMLIT_BROWSER_SERVER_PORT"] = str(port)

    # Change to app directory so imports work
    os.chdir(app_dir)

    # Add app_dir to Python path for imports
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    # Open browser after a delay (server needs time to start)
    def open_browser():
        if wait_for_server(host, port, timeout=60):
            print(f"Opening browser to {app_url}")
            webbrowser.open(app_url)
        else:
            print("Warning: Server did not start within timeout")
            print(f"Try manually opening: {local_url}")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Run Streamlit directly (not as subprocess)
    # This avoids PyInstaller's sys.executable issue
    try:
        from streamlit.web import cli as stcli

        sys.argv = [
            "streamlit",
            "run",
            str(ui_path),
            "--server.port", str(port),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.address", host,
        ]

        print(f"Running Streamlit with args: {sys.argv}")
        stcli.main()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
