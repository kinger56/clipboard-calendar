import time
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import pyperclip
from datetime import datetime

from ai_parser import FRACTION_UNIT, MONTH_DATE, NUMERIC_DATE, parse_event
from calendar_manager import CalendarError, add_calendar_event
from confirm_dialog import ask_to_add
from notification_manager import send_notification
from settings import load_settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_events.json")


LOG_FILE = os.path.join(BASE_DIR, "assistant.log")

logger = logging.getLogger("clipboard_calendar")


def setup_logging():
    """Log what the assistant DOES, never what you copied.

    The clipboard can hold passwords, messages, anything. So log lines only
    say things like "added event on 2026-11-05 at 02:00 PM", and the file
    is capped at 1 MB (plus 2 old copies) instead of growing forever.
    """
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=2)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            data = json.load(f)
            return [i for i in data if isinstance(i, dict)]
    return []


def save_processed(data):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f, indent=4)


def is_duplicate(parsed_event, processed_events):
    """Same title (ignoring case), date AND time as an event already added.

    It used to be any 2 of the 3, so "Bio quiz" was skipped as a duplicate
    of "Chem quiz" at the same date and time.
    """
    key = (parsed_event["title"].lower(), parsed_event["date"], parsed_event["start_time"])
    return any(
        (e["title"].lower(), e["date"], e["start_time"]) == key for e in processed_events
    )


def _date_starts(line):
    """Where each date in a line starts (skipping fractions like "1/2 cup")."""
    starts = []
    for m in NUMERIC_DATE.finditer(line):
        if not FRACTION_UNIT.match(line, m.end()):
            starts.append(m.start())
    starts += [m.start() for m in MONTH_DATE.finditer(line)]
    return sorted(starts)


def split_events(text):
    """Split copied text into one candidate event per piece.

    Each line is its own piece. A line with several dates, like a syllabus
    row "11/5 Quiz 1 11/12 Quiz 2", is split at each date, but text before
    the first date stays with it ("Exam 11/5 2 PM" keeps its title).
    """
    pieces = []
    for line in text.splitlines():
        line = line.strip()
        starts = _date_starts(line)
        cuts = [0] + starts[1:] + [len(line)]
        for a, b in zip(cuts, cuts[1:]):
            piece = line[a:b].strip(" ,;")
            if len(piece) > 5:
                pieces.append(piece)
    return pieces


def confirm_from_settings(title, start_dt, end_dt):
    """Ask first if "Ask Before Adding" is on (the default). Read on every
    event, so toggling it in the menu works without a restart."""
    if load_settings()["ask_before_adding"]:
        return ask_to_add(title, start_dt, end_dt)
    return title


def process_text(text, processed, seen_errors,
                 add_event=add_calendar_event, notify=send_notification, save=save_processed,
                 confirm=None):
    """Handle one new clipboard value: find events in it and add them.

    The add/notify/save/confirm functions can be swapped out, so tests can
    run this without touching Apple Calendar or the real saved-events file.
    `confirm(title, start, end)` returns the title to use, or None to skip;
    with no `confirm`, events are added without asking.
    """
    for line in split_events(text):
        line_lower = line.lower()

        if line_lower in seen_errors:
            continue

        try:
            parsed = parse_event(line)

            if not parsed:
                seen_errors.add(line_lower)
            elif is_duplicate(parsed, processed):
                notify("Duplicate Event", "Event already exists")
                logger.info("Skipped duplicate event on %s", parsed["date"])
            else:
                title = confirm(parsed["title"], parsed["start_dt"], parsed["end_dt"]) if confirm else parsed["title"]
                if title is None:
                    logger.info("You chose not to add an event on %s", parsed["date"])
                    continue
                add_event(title, parsed["start_dt"], parsed["end_dt"])
                notify(
                    "Event Added",
                    f"{title} on {parsed['date']} from {parsed['start_time']} to {parsed['end_time']}"
                )
                processed.append({
                    "title": title,
                    "date": parsed["date"],
                    "start_time": parsed["start_time"]
                })
                save(processed)
                logger.info("Added event on %s at %s", parsed["date"], parsed["start_time"])

        except CalendarError as e:
            # Not the text's fault, so don't remember it as
            # unparseable: copying it again will retry.
            notify("Couldn't add event", str(e))
            logger.error("Calendar refused an event")

        except Exception as e:
            # Log the kind of error only: the message can
            # contain the copied text.
            logger.warning("Could not process a copied line (%s)", type(e).__name__)
            seen_errors.add(line_lower)


def main():
    setup_logging()
    processed = load_processed()

    last_text = ""
    seen_errors = set()

    logger.info("Clipboard assistant started")

    while True:
        try:
            text = pyperclip.paste().strip()

            if text and text != last_text:
                process_text(text, processed, seen_errors, confirm=confirm_from_settings)
                last_text = text

            time.sleep(2)

        except Exception as e:
            logger.error("Unexpected error (%s)", type(e).__name__)
            time.sleep(2)


if __name__ == "__main__":
    main()
