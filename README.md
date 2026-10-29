# macOS Clipboard Calendar Assistant

Automatically detects copied text that looks like events or assignments and adds them to Apple Calendar.

---

## Features

- Monitors clipboard continuously
- Detects events using natural language
- Supports:
  - "tomorrow"
  - "next Friday"
  - "June 2 at 3 PM"
  - "5/23 1-3 PM"
- Adds events to Apple Calendar via AppleScript
- Sends macOS notifications
- Prevents duplicate events
- Logs activity and errors

---

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py