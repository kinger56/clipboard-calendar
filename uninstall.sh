#!/bin/bash
# Stops Clipboard Calendar and removes its launch agents. Leaves the code,
# your settings and any calendar events alone.
set -euo pipefail
DOMAIN="gui/$(id -u)"
for label in com.clipboardcalendar.assistant com.clipboardcalendar.menu; do
  launchctl bootout "$DOMAIN/$label" 2>/dev/null || true
  rm -f "$HOME/Library/LaunchAgents/$label.plist"
  echo "Removed $label"
done
