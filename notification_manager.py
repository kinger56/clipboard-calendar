"""macOS notifications through AppleScript.

Like calendar_manager.py, the script never changes and the text goes in as
arguments, so notification text can't be turned into AppleScript code.
"""

import subprocess  # nosec B404 - only runs the fixed osascript path below

# Full path, so a program named "osascript" planted earlier on PATH can't
# run instead. Arguments are passed as a list (no shell), so copied text
# can't become a command.
OSASCRIPT = "/usr/bin/osascript"

NOTIFY_SCRIPT = """
on run argv
    display notification (item 2 of argv) with title (item 1 of argv)
end run
"""


def send_notification(title: str, message: str):
    # A failed notification isn't worth crashing over, so errors are ignored.
    subprocess.run(
        [OSASCRIPT, "-", title, message],  # nosec B603 - text only as arguments
        input=NOTIFY_SCRIPT,
        capture_output=True,
        text=True,
    )
