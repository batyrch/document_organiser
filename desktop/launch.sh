#!/bin/bash
#
# Document Organizer Launcher
# This script sets up a Python virtual environment and launches the Streamlit app.
#

set -e

# Get the directory where this script is located (inside .app bundle)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")/Resources"

# User data directory for venv and logs
DATA_DIR="$HOME/Library/Application Support/DocumentOrganizer"
VENV_DIR="$DATA_DIR/venv"
LOG_FILE="$DATA_DIR/launcher.log"

# Create data directory if needed
mkdir -p "$DATA_DIR"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting Document Organizer..."
log "App directory: $APP_DIR"
log "Data directory: $DATA_DIR"

# Check for Python 3
find_python() {
    # Try common Python 3 locations
    for py in python3 /usr/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
        if command -v "$py" &> /dev/null; then
            version=$("$py" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                echo "$py"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON=$(find_python)
if [ -z "$PYTHON" ]; then
    log "ERROR: Python 3.10+ not found"
    osascript -e 'display dialog "Python 3.10 or later is required.\n\nPlease install Python from python.org or via Homebrew:\n\nbrew install python@3.12" buttons {"OK"} default button "OK" with title "Document Organizer" with icon stop'
    exit 1
fi

log "Using Python: $PYTHON ($($PYTHON --version))"

# Create or update virtual environment
REQUIREMENTS_FILE="$APP_DIR/requirements.txt"
REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements_hash"

get_requirements_hash() {
    if [ -f "$REQUIREMENTS_FILE" ]; then
        shasum -a 256 "$REQUIREMENTS_FILE" | cut -d' ' -f1
    else
        echo "none"
    fi
}

CURRENT_HASH=$(get_requirements_hash)
STORED_HASH=""
if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
    STORED_HASH=$(cat "$REQUIREMENTS_HASH_FILE")
fi

if [ ! -d "$VENV_DIR" ] || [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    log "Setting up Python environment..."

    # Show progress dialog
    osascript -e 'display notification "Setting up Python environment. This may take a minute..." with title "Document Organizer"' &

    # Create fresh venv
    rm -rf "$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"

    # Upgrade pip and install dependencies
    "$VENV_DIR/bin/pip" install --upgrade pip >> "$LOG_FILE" 2>&1

    if [ -f "$REQUIREMENTS_FILE" ]; then
        log "Installing dependencies..."
        "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE" >> "$LOG_FILE" 2>&1
    fi

    # Store requirements hash
    echo "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
    log "Environment setup complete"
fi

# Find a free port
find_free_port() {
    python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
}

PORT=$(find_free_port)
log "Using port: $PORT"

# Set up environment variables
export STREAMLIT_SERVER_PORT="$PORT"
export STREAMLIT_SERVER_HEADLESS="true"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"
export STREAMLIT_SERVER_ADDRESS="localhost"

# Change to app directory
cd "$APP_DIR"

# Launch Streamlit in background
log "Starting Streamlit server..."
"$VENV_DIR/bin/python" -m streamlit run ui.py \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false \
    >> "$LOG_FILE" 2>&1 &

STREAMLIT_PID=$!
log "Streamlit PID: $STREAMLIT_PID"

# Wait for server to be ready
wait_for_server() {
    local port=$1
    local timeout=60
    local start=$(date +%s)

    while true; do
        if curl -s "http://localhost:$port/_stcore/health" > /dev/null 2>&1; then
            return 0
        fi

        local now=$(date +%s)
        if [ $((now - start)) -ge $timeout ]; then
            return 1
        fi

        # Check if process is still running
        if ! kill -0 $STREAMLIT_PID 2>/dev/null; then
            return 1
        fi

        sleep 0.5
    done
}

log "Waiting for server to start..."
if wait_for_server "$PORT"; then
    log "Server ready, opening browser..."
    open "http://localhost:$PORT"
else
    log "ERROR: Server failed to start"
    osascript -e 'display dialog "Failed to start the application.\n\nCheck the log file at:\n'"$LOG_FILE"'" buttons {"OK"} default button "OK" with title "Document Organizer" with icon stop'
    kill $STREAMLIT_PID 2>/dev/null || true
    exit 1
fi

# Keep running and handle termination
cleanup() {
    log "Shutting down..."
    kill $STREAMLIT_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGTERM SIGINT SIGHUP

# Wait for Streamlit to exit
wait $STREAMLIT_PID
log "Application exited"
