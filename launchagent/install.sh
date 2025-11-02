#!/bin/bash
# Network Monitor - LaunchAgent Installation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PLIST_NAME="com.networkmonitor.daemon.plist"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST_TEMPLATE="$PROJECT_DIR/launchagent/$PLIST_NAME"
INSTALL_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Network Monitor LaunchAgent Setup    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo

# Check if template exists
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo -e "${RED}❌ Error: LaunchAgent template not found at:${NC}"
    echo "   $PLIST_TEMPLATE"
    exit 1
fi

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$HOME/Library/LaunchAgents"

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: UV package manager not found${NC}"
    echo "   Please install UV first: https://github.com/astral-sh/uv"
    exit 1
fi

# Check if dependencies are synced
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Running 'uv sync'...${NC}"
    cd "$PROJECT_DIR"
    uv sync
    echo
fi

# Create a temporary plist with substituted values
echo -e "${YELLOW}📝 Creating LaunchAgent configuration...${NC}"
TEMP_PLIST=$(mktemp)
sed "s|PROJECT_DIR|$PROJECT_DIR|g; s|USER_HOME|$HOME|g" "$PLIST_TEMPLATE" > "$TEMP_PLIST"

# Copy the plist to LaunchAgents
cp "$TEMP_PLIST" "$INSTALL_PATH"
rm "$TEMP_PLIST"

echo -e "${GREEN}✅ LaunchAgent plist installed at:${NC}"
echo "   $INSTALL_PATH"
echo

# Configure sudo to allow passwordless execution for this script
echo -e "${YELLOW}🔐 Configuring passwordless sudo (requires your password once)...${NC}"
echo

SUDOERS_FILE="/etc/sudoers.d/network-monitor"
SUDO_RULE="$USER ALL=(ALL) NOPASSWD: $(which uv) run python $PROJECT_DIR/main.py"

# Create sudoers entry
echo "$SUDO_RULE" | sudo tee "$SUDOERS_FILE" > /dev/null
sudo chmod 440 "$SUDOERS_FILE"

echo -e "${GREEN}✅ Sudo configuration complete${NC}"
echo

# Unload existing LaunchAgent if running
if launchctl list | grep -q "com.networkmonitor.daemon"; then
    echo -e "${YELLOW}⚙️  Unloading existing LaunchAgent...${NC}"
    launchctl unload "$INSTALL_PATH" 2>/dev/null || true
fi

# Load the LaunchAgent
echo -e "${YELLOW}⚙️  Loading LaunchAgent...${NC}"
launchctl load "$INSTALL_PATH"

# Wait a moment for it to start
sleep 2

# Check if it's running
if launchctl list | grep -q "com.networkmonitor.daemon"; then
    echo
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Installation Complete!            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo
    echo -e "${GREEN}The Network Monitor will now start automatically on login.${NC}"
    echo
    echo "Access dashboard: http://localhost:7500/dashboard/"
    echo "View logs: tail -f ~/.netmonitor/logs/network_monitor.log"
    echo
    echo "To uninstall: cd $PROJECT_DIR/launchagent && ./uninstall.sh"
else
    echo
    echo -e "${RED}❌ Warning: LaunchAgent installed but may not be running${NC}"
    echo "Check logs: tail ~/.netmonitor/logs/launchagent_error.log"
    echo
    echo "To start manually: launchctl load $INSTALL_PATH"
fi
