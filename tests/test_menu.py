from datetime import date

from menu_app import upcoming_events


def test_upcoming_events_are_future_only_and_sorted():
    events = [
        {"title": "Past", "date": "2026-10-01", "start_time": "09:00 AM"},
        {"title": "Later", "date": "2026-11-20", "start_time": "09:00 AM"},
        {"title": "Today", "date": "2026-10-29", "start_time": "03:00 PM"},
        "not a dict",
    ]
    titles = [e["title"] for e in upcoming_events(events, date(2026, 10, 29))]
    assert titles == ["Today", "Later"]
