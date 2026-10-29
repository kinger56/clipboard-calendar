"""Menu-bar app: shows whether the assistant is running and controls it.

🟢📋 = running, 🔴📋 = stopped. The status is checked with launchd every few
seconds, so it's always accurate, even if the assistant was started or
stopped some other way.
"""

import json
import os
from datetime import date

import rumps

import service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_events.json")


def upcoming_events(events: list, today: date, limit: int = 10) -> list:
    """Saved events from today on, soonest first."""
    future = [e for e in events if isinstance(e, dict) and e.get("date", "") >= today.isoformat()]
    return sorted(future, key=lambda e: (e["date"], e.get("start_time", "")))[:limit]


class ClipboardAssistantApp(rumps.App):

    def __init__(self):
        super().__init__("📋", quit_button=None)
        self.menu = [
            "Start Assistant",
            "Stop Assistant",
            "Restart Assistant",
            None,
            "Show Upcoming Events",
            "Clear Memory",
            None,
            "Quit",
        ]
        self.refresh_status(None)

    @rumps.timer(5)
    def refresh_status(self, _):
        self.title = "🟢📋" if service.is_running() else "🔴📋"

    @rumps.clicked("Start Assistant")
    def on_start(self, _):
        service.start()
        rumps.notification("Clipboard Calendar", "Started", "")
        self.refresh_status(None)

    @rumps.clicked("Stop Assistant")
    def on_stop(self, _):
        service.stop()
        rumps.notification("Clipboard Calendar", "Stopped", "Copied text is no longer being read.")
        self.refresh_status(None)

    @rumps.clicked("Restart Assistant")
    def on_restart(self, _):
        service.restart()
        rumps.notification("Clipboard Calendar", "Restarted", "")
        self.refresh_status(None)

    @rumps.clicked("Show Upcoming Events")
    def on_events(self, _):
        # Used to launch a second copy of the assistant instead of showing events.
        try:
            with open(PROCESSED_FILE) as f:
                events = upcoming_events(json.load(f), date.today())
        except (OSError, ValueError):
            events = []
        if events:
            lines = [f"{e['date']}  {e.get('start_time', '')}  {e.get('title', '')}" for e in events]
            rumps.alert("Upcoming events", "\n".join(lines))
        else:
            rumps.alert("Upcoming events", "No upcoming events added yet.")

    @rumps.clicked("Clear Memory")
    def on_clear(self, _):
        try:
            if os.path.exists(PROCESSED_FILE):
                os.remove(PROCESSED_FILE)
            rumps.notification("Clipboard Calendar", "Memory cleared", "")
        except OSError:
            rumps.notification("Clipboard Calendar", "Could not clear memory", "")

    @rumps.clicked("Quit")
    def on_quit(self, _):
        service.stop()
        # The menu app is a KeepAlive launch agent too, so plain quitting
        # would just relaunch it. Unloading its own service quits for real.
        service.stop(service.MENU_LABEL)
        rumps.quit_application()


if __name__ == "__main__":
    ClipboardAssistantApp().run()
