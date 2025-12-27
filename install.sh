#!/bin/bash
#
# Document Organizer Installer
#
# This script:
# 1. Creates a virtual environment with all dependencies
# 2. Creates a 'docorg' command to launch the app
# 3. Optionally creates an Automator app for dock/Finder launching
#

set -e

echo "========================================"
echo "  Document Organizer Installer"
echo "========================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/document-organizer"
BIN_DIR="$HOME/.local/bin"
VENV_DIR="$INSTALL_DIR/venv"

# Check for Python 3.10+
find_python() {
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
    echo "❌ Error: Python 3.10 or later is required."
    echo ""
    echo "Install Python via Homebrew:"
    echo "  brew install python@3.12"
    echo ""
    echo "Or download from python.org"
    exit 1
fi

echo "✓ Found Python: $PYTHON ($($PYTHON --version))"

# Create installation directory
echo ""
echo "Installing to: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copy application files
echo "Copying application files..."
for file in ui.py document_organizer.py ai_providers.py settings.py device_auth.py icons.py jd_system.py jd_builder.py jd_prompts.py config.yaml requirements.txt .env.example; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        cp "$SCRIPT_DIR/$file" "$INSTALL_DIR/"
        echo "  ✓ $file"
    fi
done

# Copy .env if exists (for user configuration)
if [ -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env" "$INSTALL_DIR/"
    echo "  ✓ .env (user configuration)"
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "  Removing existing venv..."
    rm -rf "$VENV_DIR"
fi

"$PYTHON" -m venv "$VENV_DIR"
echo "  ✓ Virtual environment created"

# Install dependencies
echo ""
echo "Installing dependencies (this may take a few minutes)..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "  ✓ Dependencies installed"

# Create launcher script
LAUNCHER="$BIN_DIR/docorg"
cat > "$LAUNCHER" << 'LAUNCHER_SCRIPT'
#!/bin/bash
#
# Document Organizer Launcher
#

INSTALL_DIR="$HOME/.local/share/document-organizer"
VENV_DIR="$INSTALL_DIR/venv"
LOG_FILE="$INSTALL_DIR/launcher.log"

# Find a free port
find_free_port() {
    python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
}

PORT=$(find_free_port)

echo "Starting Document Organizer on port $PORT..."

cd "$INSTALL_DIR"

# Set Streamlit config
export STREAMLIT_SERVER_PORT="$PORT"
export STREAMLIT_SERVER_HEADLESS="true"
export STREAMLIT_BROWSER_GATHER_USAGE_STATS="false"

# Start Streamlit in background
"$VENV_DIR/bin/python" -m streamlit run ui.py \
    --server.port "$PORT" \
    --server.headless true \
    --browser.gatherUsageStats false \
    >> "$LOG_FILE" 2>&1 &

STREAMLIT_PID=$!

# Wait for server
echo "Waiting for server to start..."
for i in {1..60}; do
    if curl -s "http://localhost:$PORT/_stcore/health" > /dev/null 2>&1; then
        echo "✓ Server ready!"
        open "http://localhost:$PORT"
        echo ""
        echo "Document Organizer is running at http://localhost:$PORT"
        echo "Press Ctrl+C to stop."
        echo ""
        wait $STREAMLIT_PID
        exit 0
    fi
    sleep 0.5
done

echo "❌ Server failed to start. Check $LOG_FILE for details."
kill $STREAMLIT_PID 2>/dev/null
exit 1
LAUNCHER_SCRIPT

chmod +x "$LAUNCHER"
echo ""
echo "✓ Created launcher: $LAUNCHER"

# Add ~/.local/bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "Adding ~/.local/bin to your PATH..."

    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.bash_profile" ]; then
        SHELL_RC="$HOME/.bash_profile"
    fi

    if [ -n "$SHELL_RC" ]; then
        if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
            echo '' >> "$SHELL_RC"
            echo '# Document Organizer' >> "$SHELL_RC"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
            echo "  Added to $SHELL_RC"
        fi
    fi
fi

# Create macOS app (optional dock/Finder launcher)
echo ""
read -p "Create a macOS app for Dock/Finder? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    APP_PATH="/Applications/Document Organizer.app"

    echo "Creating macOS app..."

    # Remove existing
    rm -rf "$APP_PATH"

    # Create app structure
    mkdir -p "$APP_PATH/Contents/MacOS"
    mkdir -p "$APP_PATH/Contents/Resources"

    # Create Info.plist
    cat > "$APP_PATH/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.documentorganizer.app</string>
    <key>CFBundleName</key>
    <string>Document Organizer</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
PLIST

    # Create launcher that opens Terminal
    cat > "$APP_PATH/Contents/MacOS/launcher" << APPLAUNCHER
#!/bin/bash
# This opens Terminal and runs docorg, which has your normal permissions
osascript -e 'tell application "Terminal" to do script "$HOME/.local/bin/docorg"'
osascript -e 'tell application "Terminal" to activate'
APPLAUNCHER

    chmod +x "$APP_PATH/Contents/MacOS/launcher"

    echo "  ✓ Created: $APP_PATH"
    echo ""
    echo "  The app opens Terminal to run Document Organizer."
    echo "  This ensures proper file permissions."
fi

echo ""
echo "========================================"
echo "  Installation Complete!"
echo "========================================"
echo ""
echo "To start Document Organizer:"
echo "  docorg"
echo ""
echo "Or open 'Document Organizer' from Applications/Dock."
echo ""
