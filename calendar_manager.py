import subprocess
from datetime import datetime

CALENDAR_NAME = "AI Assistant"


def add_calendar_event(title: str, start_dt: datetime, end_dt: datetime):
    try:
        title = title.replace('"', '\\"')

        start_str = start_dt.strftime("%B %d, %Y %I:%M:%S %p")
        end_str = end_dt.strftime("%B %d, %Y %I:%M:%S %p")

        # ✅ Single-line AppleScript (CRITICAL FIX)
        script = (
            f'tell application "Calendar" '
            f'to tell calendar "{CALENDAR_NAME}" '
            f'to make new event with properties '
            f'{{summary:"{title}", start date:date "{start_str}", end date:date "{end_str}"}}'
        )

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True
        )

        print("Calendar STDOUT:", result.stdout)
        print("Calendar STDERR:", result.stderr)

    except Exception as e:
        print(f"Calendar exception: {e}")