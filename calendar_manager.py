"""Adds events to Apple Calendar through AppleScript.

Security: copied text is untrusted (it can come from any web page). The
original version pasted the title into the AppleScript source, so text
with a crafted quote or backslash could break out of the title and run
its own AppleScript (which can run shell commands). Now the script below
never changes: the title and dates go in as separate command-line
arguments (`argv`), so they can only ever be data, never code.
"""

import subprocess
from datetime import datetime

CALENDAR_NAME = "AI Assistant"

# Builds dates from numbers, so it works whatever language/region the Mac
# is set to (parsing "October 29, 2026 3:00 PM" text depends on locale).
ADD_EVENT_SCRIPT = """
on makeDate(y, m, d, h, mi)
    set dt to current date
    set day of dt to 1 -- so changing the month can't overflow (Jan 31 -> Feb)
    set year of dt to y
    set month of dt to m
    set day of dt to d
    set hours of dt to h
    set minutes of dt to mi
    set seconds of dt to 0
    return dt
end makeDate

on run argv
    set eventTitle to item 1 of argv
    set calendarName to item 2 of argv
    set startDate to makeDate((item 3 of argv) as integer, (item 4 of argv) as integer, (item 5 of argv) as integer, (item 6 of argv) as integer, (item 7 of argv) as integer)
    set endDate to makeDate((item 8 of argv) as integer, (item 9 of argv) as integer, (item 10 of argv) as integer, (item 11 of argv) as integer, (item 12 of argv) as integer)
    tell application "Calendar"
        tell calendar calendarName
            make new event with properties {summary:eventTitle, start date:startDate, end date:endDate}
        end tell
    end tell
end run
"""


class CalendarError(Exception):
    """Apple Calendar didn't add the event (e.g. the calendar doesn't exist)."""


def _date_args(dt: datetime) -> list:
    return [str(dt.year), str(dt.month), str(dt.day), str(dt.hour), str(dt.minute)]


def run_osascript(script: str, args: list) -> subprocess.CompletedProcess:
    # "-" means "read the script from stdin"; everything after it is argv.
    return subprocess.run(
        ["osascript", "-", *args], input=script, capture_output=True, text=True
    )


def add_calendar_event(title: str, start_dt: datetime, end_dt: datetime, run=run_osascript):
    """Add an event, or raise CalendarError. `run` is swappable for tests."""
    args = [title, CALENDAR_NAME, *_date_args(start_dt), *_date_args(end_dt)]
    result = run(ADD_EVENT_SCRIPT, args)
    if result.returncode != 0:
        # Don't include stderr: AppleScript errors can echo the title back.
        raise CalendarError(
            f'Calendar refused the event (does a calendar named "{CALENDAR_NAME}" exist?)'
        )
