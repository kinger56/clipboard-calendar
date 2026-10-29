"""The calendar code must treat copied text as data, never as AppleScript."""

import subprocess
from datetime import datetime

import pytest

from calendar_manager import ADD_EVENT_SCRIPT, CalendarError, add_calendar_event

CALENDAR_NAME = "Test Calendar"

START = datetime(2026, 11, 5, 14, 0)
END = datetime(2026, 11, 5, 16, 30)


class FakeOsascript:
    def __init__(self, returncode=0):
        self.returncode = returncode
        self.calls = []

    def __call__(self, script, args):
        self.calls.append((script, args))
        return subprocess.CompletedProcess(["osascript"], self.returncode, "", "")


def test_title_and_dates_are_passed_as_arguments():
    run = FakeOsascript()
    add_calendar_event("Data Structures exam", START, END, run=run, calendar_name=CALENDAR_NAME)
    script, args = run.calls[0]
    assert script == ADD_EVENT_SCRIPT  # the script itself never changes
    assert args == ["Data Structures exam", CALENDAR_NAME,
                    "2026", "11", "5", "14", "0", "2026", "11", "5", "16", "30"]


@pytest.mark.parametrize("evil_title", [
    'x" & (do shell script "touch /tmp/pwned") & "',
    'ends with a backslash \\',
    '\\" & (do shell script "id") & \\"',
])
def test_injection_attempts_stay_plain_data(evil_title):
    run = FakeOsascript()
    add_calendar_event(evil_title, START, END, run=run, calendar_name=CALENDAR_NAME)
    script, args = run.calls[0]
    assert "do shell script" not in script
    assert args[0] == evil_title  # passed through untouched, as one argument


def test_calendar_failure_raises_without_echoing_the_title():
    with pytest.raises(CalendarError) as error:
        add_calendar_event("Secret plans", START, END, run=FakeOsascript(returncode=1),
                           calendar_name=CALENDAR_NAME)
    assert "Secret plans" not in str(error.value)
    assert CALENDAR_NAME in str(error.value)
