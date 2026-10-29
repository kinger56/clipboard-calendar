"""The "Add to your calendar?" prompt shown before an event is added.

It shows when the event is and lets you fix the title (the parser's guess
isn't always what you'd call it), then Add or Ignore. If you don't answer
within 2 minutes, nothing is added.

Like the calendar script, the AppleScript never changes: the title and
time go in as arguments, so copied text can't become AppleScript code.
"""

import subprocess
from datetime import datetime
from typing import Optional

TIMEOUT_SECONDS = 120

CONFIRM_SCRIPT = """
on run argv
    set eventTitle to item 1 of argv
    set eventWhen to item 2 of argv
    set timeoutSeconds to (item 3 of argv) as integer
    activate -- bring the prompt in front of other windows
    set reply to display dialog ("Add to your calendar?" & return & eventWhen & return & return & "Title:") default answer eventTitle buttons {"Ignore", "Add"} default button "Add" with title "Clipboard Calendar" giving up after timeoutSeconds
    if gave up of reply then return "IGNORE"
    if button returned of reply is "Add" then return "ADD" & linefeed & (text returned of reply)
    return "IGNORE"
end run
"""


def describe_time(start: datetime, end: datetime) -> str:
    """"Thu, Nov 5 · 2:00 PM – 4:00 PM" """
    def clock(dt: datetime) -> str:
        return dt.strftime("%I:%M %p").lstrip("0")

    day = f"{start:%a, %b} {start.day}"
    return f"{day} · {clock(start)} – {clock(end)}"


def run_osascript(script: str, args: list) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["osascript", "-", *args], input=script, capture_output=True, text=True
    )


def ask_to_add(title: str, start: datetime, end: datetime, run=run_osascript) -> Optional[str]:
    """Show the prompt. Returns the title to use (possibly edited), or None
    if the user chose Ignore, didn't answer, or the prompt couldn't show."""
    result = run(CONFIRM_SCRIPT, [title, describe_time(start, end), str(TIMEOUT_SECONDS)])
    if result.returncode != 0:
        return None
    answer = result.stdout.rstrip("\n")
    if not answer.startswith("ADD"):
        return None
    edited = answer[len("ADD"):].strip()
    return edited or title  # an emptied title box keeps the original
