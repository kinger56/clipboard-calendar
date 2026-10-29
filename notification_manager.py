"""macOS notifications through AppleScript.

Like calendar_manager.py, the script never changes and the text goes in as
arguments, so notification text can't be turned into AppleScript code.
"""

import subprocess

NOTIFY_SCRIPT = """
on run argv
    display notification (item 2 of argv) with title (item 1 of argv)
end run
"""


def send_notification(title: str, message: str):
    # A failed notification isn't worth crashing over, so errors are ignored.
    subprocess.run(
        ["osascript", "-", title, message],
        input=NOTIFY_SCRIPT,
        capture_output=True,
        text=True,
    )
