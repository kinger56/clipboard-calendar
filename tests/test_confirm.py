"""The "Add to your calendar?" prompt and the setting that turns it on/off."""

import subprocess
from datetime import datetime

import main
from confirm_dialog import CONFIRM_SCRIPT, ask_to_add, describe_time
from settings import DEFAULTS, load_settings, save_settings

START, END = datetime(2026, 11, 5, 14), datetime(2026, 11, 5, 16)


def fake_dialog(stdout, returncode=0):
    calls = []

    def run(script, args):
        calls.append((script, args))
        return subprocess.CompletedProcess(["osascript"], returncode, stdout, "")

    return run, calls


# ---- the prompt ---------------------------------------------------------------


def test_add_keeps_the_title():
    run, calls = fake_dialog("ADD\nData Structures exam\n")
    assert ask_to_add("Data Structures exam", START, END, run=run) == "Data Structures exam"
    script, args = calls[0]
    assert script == CONFIRM_SCRIPT  # copied text goes in as arguments, never as code
    assert args == ["Data Structures exam", "Thu, Nov 5 · 2:00 PM – 4:00 PM", "120"]


def test_edited_title_is_used():
    run, _ = fake_dialog("ADD\nCSCI 61 midterm\n")
    assert ask_to_add("Data Structures exam", START, END, run=run) == "CSCI 61 midterm"


def test_emptied_title_keeps_the_original():
    run, _ = fake_dialog("ADD\n\n")
    assert ask_to_add("Quiz", START, END, run=run) == "Quiz"


def test_ignore_timeout_or_failure_adds_nothing():
    for stdout, code in [("IGNORE\n", 0), ("", 0), ("", 1)]:
        run, _ = fake_dialog(stdout, code)
        assert ask_to_add("Quiz", START, END, run=run) is None


def test_describe_time():
    assert describe_time(datetime(2026, 12, 1, 9, 5), datetime(2026, 12, 1, 10, 5)) == \
        "Tue, Dec 1 · 9:05 AM – 10:05 AM"


# ---- process_text with a prompt --------------------------------------------------


def run_process(text, confirm, processed=None):
    added, saved = [], []
    main.process_text(text, processed if processed is not None else [], set(),
                      add_event=lambda title, s, e: added.append(title),
                      notify=lambda *a: None, save=lambda events: saved.append(list(events)),
                      confirm=confirm)
    return added, saved


def test_ignored_event_is_not_added_or_saved():
    added, saved = run_process("Exam 11/5 2 PM", confirm=lambda *a: None)
    assert added == [] and saved == []


def test_edited_title_is_added_and_remembered():
    added, saved = run_process("Exam 11/5 2 PM", confirm=lambda *a: "CSCI 61 midterm")
    assert added == ["CSCI 61 midterm"]
    assert saved[-1][-1]["title"] == "CSCI 61 midterm"


def test_duplicates_are_skipped_without_asking():
    asked = []
    previous = [{"title": "Exam", "date": "2026-11-05", "start_time": "02:00 PM"}]
    run_process("Exam 11/5 2 PM", confirm=lambda *a: asked.append(a), processed=previous)
    assert asked == []


# ---- the setting --------------------------------------------------------------


def test_settings_default_to_asking(tmp_path):
    defaults = load_settings(str(tmp_path / "missing.json"))
    assert defaults == DEFAULTS
    assert defaults["ask_before_adding"] is True
    assert defaults["calendar_name"] == "Clipboard Calendar"


def test_settings_round_trip_and_ignore_junk(tmp_path):
    path = str(tmp_path / "settings.json")
    save_settings({"ask_before_adding": False}, path)
    assert load_settings(path) == {**DEFAULTS, "ask_before_adding": False}

    (tmp_path / "settings.json").write_text("{not json")
    assert load_settings(path) == DEFAULTS


def test_turning_asking_off_skips_the_prompt(monkeypatch):
    shown = []
    monkeypatch.setattr(main, "load_settings", lambda: {"ask_before_adding": False})
    monkeypatch.setattr(main, "ask_to_add", lambda *a: shown.append(a))
    assert main.confirm_from_settings("Quiz", START, END) == "Quiz"
    assert shown == []
