#!/usr/bin/env python3
"""
Desktop launcher for Document Organizer.

This script:
1. Starts the Streamlit server in the background
2. Opens the user's default browser to the app
3. Handles graceful shutdown

Used by PyInstaller to create a standalone executable.
"""

import os
import sys
import time
import socket
import signal
import subprocess
import webbrowser
import threading
from pathlib import Path


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
        # Running as compiled executable
        return Path(sys._MEIPASS)
    else:
        # Running as script
        return Path(__file__).parent.parent


def main():
    app_dir = get_app_dir()
    ui_path = app_dir / "ui.py"

    # Ensure we have the UI file
    if not ui_path.exists():
        print(f"Error: Could not find ui.py at {ui_path}")
        sys.exit(1)

    # Find a free port
    port = get_free_port()
    host = "localhost"
    url = f"http://{host}:{port}"

    print(f"Starting Document Organizer...")
    print(f"App directory: {app_dir}")
    print(f"Server will be available at: {url}")

    # Set up environment
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_SERVER_ADDRESS"] = host

    # Determine the Python/Streamlit executable
    if getattr(sys, 'frozen', False):
        # When frozen, streamlit should be in the same directory
        if sys.platform == "win32":
            streamlit_cmd = str(app_dir / "streamlit.exe")
        else:
            streamlit_cmd = str(app_dir / "streamlit")

        # Fallback to module execution
        if not Path(streamlit_cmd).exists():
            streamlit_cmd = [sys.executable, "-m", "streamlit"]
        else:
            streamlit_cmd = [streamlit_cmd]
    else:
        streamlit_cmd = [sys.executable, "-m", "streamlit"]

    # Build the command
    cmd = streamlit_cmd + [
        "run",
        str(ui_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--server.address", host,
    ]

    print(f"Running: {' '.join(cmd)}")

    # Start the Streamlit server
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Handle shutdown signals
    def shutdown(signum=None, frame=None):
        print("\nShutting down...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, shutdown)

    # Wait for server to start, then open browser
    def open_browser():
        if wait_for_server(host, port):
            print(f"Opening browser to {url}")
            webbrowser.open(url)
        else:
            print("Warning: Server did not start within timeout")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Stream output from the server
    try:
        for line in process.stdout:
            print(line, end="")
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
