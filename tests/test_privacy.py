"""Copied text must never be written to the log."""

import logging

import main
from calendar_manager import CalendarError

SECRET = "my password is hunter2 and my bank PIN is 4821"


def run_and_capture_log(text, tmp_path, add_event=lambda *a: None):
    log_file = tmp_path / "test.log"
    handler = logging.FileHandler(log_file)
    main.logger.addHandler(handler)
    main.logger.setLevel(logging.INFO)
    try:
        main.process_text(text, [], set(), add_event=add_event,
                          notify=lambda *a: None, save=lambda *a: None)
    finally:
        main.logger.removeHandler(handler)
        handler.close()
    return log_file.read_text()


def test_unparseable_text_is_not_logged(tmp_path):
    assert "hunter2" not in run_and_capture_log(SECRET, tmp_path)


def test_added_event_logs_date_not_title(tmp_path):
    log = run_and_capture_log("Therapy appointment 11/5 2-3 PM", tmp_path)
    assert "Added event on" in log
    assert "Therapy" not in log


def test_text_that_crashes_the_parser_is_not_logged(tmp_path):
    log = run_and_capture_log("Lab report due 13/45 " + SECRET, tmp_path)
    assert "hunter2" not in log


def test_calendar_failure_is_reported_but_not_saved(tmp_path):
    saved, notes = [], []

    def failing_add(*args):
        raise CalendarError("Calendar refused the event")

    main.process_text("Exam 11/5 2-4 PM", [], set(), add_event=failing_add,
                      notify=lambda title, msg: notes.append(title),
                      save=lambda events: saved.append(events))
    assert notes == ["Couldn't add event"]
    assert saved == []
