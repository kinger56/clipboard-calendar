"""Event parser tests. Each bug found in the review has a test here.

`now` is fixed to Thursday, Oct 29, 2026 at 10:00 AM so results don't
depend on the day the tests run.
"""

from datetime import datetime

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from event_parser import parse_event
from main import is_duplicate

NOW = datetime(2026, 10, 29, 10, 0)  # a Thursday


def parsed(text, now=NOW):
    event = parse_event(text, now=now)
    assert event is not None, f"expected an event in {text!r}"
    return event["title"], event["start_dt"], event["end_dt"]


# ---- bugs from the review ---------------------------------------------------


def test_title_keeps_words_containing_at():
    # Was "Da Structures exam 2": "at" was deleted even inside words.
    title, start, end = parsed("Data Structures exam 11/5 2-4 PM")
    assert title == "Data Structures exam"
    assert (start, end) == (datetime(2026, 11, 5, 14), datetime(2026, 11, 5, 16))


def test_title_drops_date_words_but_keeps_names():
    # Was "Ch with Nhan about the startup tomorrow".
    title, start, _ = parsed("Chat with Nathan about the startup tomorrow at 3 PM")
    assert title == "Chat with Nathan about the startup"
    assert start == datetime(2026, 10, 30, 15)


def test_range_across_noon_ends_after_it_starts():
    # Was 11:00 AM to 1:00 AM.
    _, start, end = parsed("Study group 11/7 11-1")
    assert (start, end) == (datetime(2026, 11, 7, 11), datetime(2026, 11, 7, 13))


def test_24_hour_times():
    # Was a crash, and "13" was read as the 13th.
    title, start, end = parsed("Office hours Friday 13-15")
    assert title == "Office hours"
    assert (start, end) == (datetime(2026, 10, 30, 13), datetime(2026, 10, 30, 15))


def test_impossible_date_is_ignored_not_a_crash():
    assert parse_event("Lab report due 13/45", now=NOW) is None


def test_fractions_are_not_dates():
    assert parse_event("Mix 1/2 cup of water", now=NOW) is None
    assert parse_event("Use 3/4 of the solution", now=NOW) is None


def test_may_the_verb_is_not_may_the_month():
    assert parse_event("You may want to review the notes", now=NOW) is None


def test_january_through_april_are_recognized():
    title, start, _ = parsed("Jan 15 midterm 10 AM")
    assert title == "midterm"
    assert start == datetime(2027, 1, 15, 10)  # Jan 15, 2026 has passed


def test_date_without_year_rolls_into_next_year():
    _, start, _ = parsed("Exam 1/5 9 AM", now=datetime(2026, 12, 20, 12))
    assert start == datetime(2027, 1, 5, 9)


def test_words_containing_month_abbreviations_are_not_dates():
    assert parse_event("Separate the precipitate", now=NOW) is None
    assert parse_event("Decrease the temperature", now=NOW) is None


def test_different_events_at_the_same_time_are_not_duplicates():
    chem = {"title": "Chem quiz", "date": "2026-11-05", "start_time": "09:00 AM"}
    bio = {"title": "Bio quiz", "date": "2026-11-05", "start_time": "09:00 AM"}
    assert not is_duplicate(bio, [chem])
    assert is_duplicate({**chem, "title": "CHEM QUIZ"}, [chem])


# ---- formats from the README keep working ------------------------------------


@pytest.mark.parametrize("text, title, start, end", [
    ("Meeting 5/23 1-3 PM", "Meeting", datetime(2027, 5, 23, 13), datetime(2027, 5, 23, 15)),
    ("Dentist June 2 at 3 PM", "Dentist", datetime(2027, 6, 2, 15), datetime(2027, 6, 2, 16)),
    ("Club meeting next Friday 6:30 PM", "Club meeting", datetime(2026, 10, 30, 18, 30), datetime(2026, 10, 30, 19, 30)),
    ("Quiz Monday 2p", "Quiz", datetime(2026, 11, 2, 14), datetime(2026, 11, 2, 15)),
    ("Essay due tomorrow", "Essay due", datetime(2026, 10, 30, 23, 59), datetime(2026, 10, 31, 0, 59)),
    ("Exam on 11/5 at 2 PM in room 204", "Exam in room 204", datetime(2026, 11, 5, 14), datetime(2026, 11, 5, 15)),
    ("Standup today 9:15am", "Standup", datetime(2026, 10, 29, 9, 15), datetime(2026, 10, 29, 10, 15)),
    ("Movie Nov 3rd 7-9", "Movie", datetime(2026, 11, 3, 19), datetime(2026, 11, 3, 21)),
])
def test_supported_formats(text, title, start, end):
    assert parsed(text) == (title, start, end)


def test_text_without_a_date_is_not_an_event():
    assert parse_event("Remember to buy milk", now=NOW) is None
    assert parse_event("Call me at 3 PM", now=NOW) is None  # a time alone isn't enough


# ---- property: the parser never crashes ---------------------------------------

date_like = st.sampled_from(
    ["11/5", "13/45", "0/0", "Jan 15", "may", "Friday", "tomorrow", "2-4 PM", "11-1", "25-30",
     "13:75", "1/2 cup", "9a", "12 PM", "99:99", "2026-10-29", "-", "at", " "]
)


@settings(max_examples=300)
@given(st.lists(st.one_of(date_like, st.text(max_size=8)), max_size=8))
def test_parser_never_crashes(parts):
    event = parse_event(" ".join(parts), now=NOW)
    if event is not None:
        assert event["end_dt"] > event["start_dt"]
        assert event["title"]


# ---- the full path: copied text -> events added -------------------------------


def events_added(text):
    import main
    added = []
    main.process_text(text, [], set(), add_event=lambda title, s, e: added.append((title, s)),
                      notify=lambda *a: None, save=lambda *a: None)
    return [title for title, _ in added]


def test_title_before_the_date_is_kept():
    # split_events used to cut the text at the date, so this became "Event".
    assert events_added("Data Structures exam 11/5 2-4 PM") == ["Data Structures exam"]


def test_one_event_per_line():
    text = "Quiz 1 11/5 9 AM\nLab report due 11/12\n\nNo date on this line"
    assert events_added(text) == ["Quiz 1", "Lab report due"]


def test_syllabus_line_with_several_dates():
    assert events_added("11/5 Quiz 1 11/12 Quiz 2 11/19 Final review") == [
        "Quiz 1", "Quiz 2", "Final review",
    ]
