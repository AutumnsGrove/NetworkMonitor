#!/bin/bash
# Uninstall Network Monitor LaunchAgent

set -e

echo "=== Uninstalling Network Monitor LaunchAgent ==="

PLIST_DEST="$HOME/Library/LaunchAgents/com.netmonitor.daemon.plist"

if [ ! -f "$PLIST_DEST" ]; then
    echo "LaunchAgent not installed"
    exit 1
fi

# Unload LaunchAgent
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Remove plist
rm "$PLIST_DEST"

echo "LaunchAgent uninstalled successfully"
echo ""
echo "Network Monitor will no longer start automatically on login"
echo ""
echo "Note: This does not remove the Network Monitor application files"
echo "      or your data in ~/.netmonitor/"
