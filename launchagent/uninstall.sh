#!/bin/bash
# Network Monitor - LaunchAgent Uninstallation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PLIST_NAME="com.networkmonitor.daemon.plist"
INSTALL_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
SUDOERS_FILE="/etc/sudoers.d/network-monitor"

echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  Network Monitor LaunchAgent Removal  ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
echo

# Check if LaunchAgent is installed
if [ ! -f "$INSTALL_PATH" ]; then
    echo -e "${YELLOW}⚠️  LaunchAgent not found at:${NC}"
    echo "   $INSTALL_PATH"
    echo "   (May already be uninstalled)"
    echo
else
    # Unload the LaunchAgent if running
    if launchctl list | grep -q "com.networkmonitor.daemon"; then
        echo -e "${YELLOW}⚙️  Stopping LaunchAgent...${NC}"
        launchctl unload "$INSTALL_PATH"
        echo -e "${GREEN}✅ LaunchAgent stopped${NC}"
    fi

    # Remove the plist file
    echo -e "${YELLOW}🗑️  Removing LaunchAgent file...${NC}"
    rm "$INSTALL_PATH"
    echo -e "${GREEN}✅ LaunchAgent file removed${NC}"
fi

# Remove sudoers entry
if [ -f "$SUDOERS_FILE" ]; then
    echo -e "${YELLOW}🔐 Removing sudo configuration (requires password)...${NC}"
    sudo rm "$SUDOERS_FILE"
    echo -e "${GREEN}✅ Sudo configuration removed${NC}"
else
    echo -e "${YELLOW}⚠️  Sudoers file not found (may already be removed)${NC}"
fi

echo
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Uninstallation Complete!          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo
echo "The Network Monitor will no longer start automatically on login."
echo
echo "To run manually: cd $(dirname "$(dirname "${BASH_SOURCE[0]}")") && sudo uv run python main.py"
echo
echo "To reinstall: cd $(dirname "${BASH_SOURCE[0]}") && ./install.sh"
