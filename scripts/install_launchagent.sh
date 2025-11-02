#!/bin/bash
# Install Network Monitor LaunchAgent

set -e

echo "=== Installing Network Monitor LaunchAgent ==="

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_SRC="$PROJECT_DIR/com.netmonitor.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.netmonitor.daemon.plist"

# Check if source plist exists
if [ ! -f "$PLIST_SRC" ]; then
    echo "Error: Source plist not found at $PLIST_SRC"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Replace placeholders
sed "s|/PATH/TO/NetworkMonitor|$PROJECT_DIR|g" "$PLIST_SRC" | \
sed "s|/Users/USERNAME|$HOME|g" > "$PLIST_DEST"

echo "Plist installed to: $PLIST_DEST"

# Unload if already loaded (ignore errors)
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load LaunchAgent
launchctl load "$PLIST_DEST"

echo "LaunchAgent loaded successfully"
echo ""
echo "Network Monitor will now start automatically on login"
echo ""
echo "Useful commands:"
echo "  Check status: launchctl list | grep netmonitor"
echo "  Stop daemon:  launchctl unload $PLIST_DEST"
echo "  View logs:    tail -f ~/.netmonitor/logs/launchagent.log"
