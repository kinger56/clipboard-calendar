#!/bin/bash
# Installs Clipboard Calendar for the current user:
#   1. creates a Python virtual environment with the dependencies
#   2. registers two launch agents, so the assistant and its menu-bar icon
#      start at login and restart if they crash
# Run it again any time to reinstall. Undo with ./uninstall.sh.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"

echo "Setting up Python environment..."
python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install --quiet -r "$DIR/requirements.txt"

# Paths go into XML, so escape the characters XML treats specially.
xml_escape() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' <<<"$1"; }
PYTHON_XML="$(xml_escape "$DIR/venv/bin/python3")"
DIR_XML="$(xml_escape "$DIR")"

install_agent() {
  local label="$1" script="$2"
  local plist="$AGENTS/$label.plist"
  mkdir -p "$AGENTS"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_XML</string>
    <string>$DIR_XML/$script</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR_XML</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <!-- The app writes its own (privacy-safe) log; discard raw output. -->
  <key>StandardOutPath</key><string>/dev/null</string>
  <key>StandardErrorPath</key><string>/dev/null</string>
</dict>
</plist>
PLIST
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || true  # if already installed
  launchctl bootstrap "$DOMAIN" "$plist"
  echo "Started $label"
}

install_agent com.clipboardcalendar.assistant main.py
install_agent com.clipboardcalendar.menu menu_app.py

echo
echo "Done. Look for the 📋 icon in your menu bar."
echo "Events go into the Apple Calendar named \"Clipboard Calendar\": create it in"
echo "Calendar (File > New Calendar) if you haven't yet."
