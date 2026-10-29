import time
import json
import os
import logging
from logging.handlers import RotatingFileHandler
import pyperclip
import re
from datetime import datetime

from ai_parser import parse_event
from calendar_manager import CalendarError, add_calendar_event
from notification_manager import send_notification

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
    for event in processed_events:
        matches = 0

        if event["title"].lower() == parsed_event["title"].lower():
            matches += 1
        if event["date"] == parsed_event["date"]:
            matches += 1
        if event["start_time"] == parsed_event["start_time"]:
            matches += 1

        if matches >= 2:
            return True

    return False


# ✅ ✅ SMART EVENT SPLITTING (DATE-BASED)
def split_events(text):
    text = text.replace("\n", " ")

    pattern = re.compile(
        r'(?:\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b\s*\d{1,2}|\b\d{1,2}/\d{1,2})',
        re.IGNORECASE
    )

    matches = list(pattern.finditer(text))

    events = []

    if not matches:
        return [text]

    for i in range(len(matches)):
        start = matches[i].start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        event = text[start:end].strip()
        event = event.strip(", ")

        if len(event) > 5:
            events.append(event)

    return events


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

                event_lines = split_events(text)

                for line in event_lines:
                    line_lower = line.lower()

                    if line_lower in seen_errors:
                        continue

                    try:
                        parsed = parse_event(line)

                        if parsed:
                            if is_duplicate(parsed, processed):
                                send_notification("Duplicate Event", "Event already exists")
                                logger.info("Skipped duplicate event on %s", parsed["date"])
                            else:
                                add_calendar_event(
                                    parsed["title"],
                                    parsed["start_dt"],
                                    parsed["end_dt"]
                                )

                                send_notification(
                                    "Event Added",
                                    f"{parsed['title']} on {parsed['date']} from {parsed['start_time']} to {parsed['end_time']}"
                                )

                                processed.append({
                                    "title": parsed["title"],
                                    "date": parsed["date"],
                                    "start_time": parsed["start_time"]
                                })

                                save_processed(processed)

                                logger.info("Added event on %s at %s", parsed["date"], parsed["start_time"])

                        else:
                            seen_errors.add(line_lower)

                    except CalendarError as e:
                        # Not the text's fault, so don't remember it as
                        # unparseable: copying it again will retry.
                        send_notification("Couldn't add event", str(e))
                        logger.error("Calendar refused an event")

                    except Exception as e:
                        # Log the kind of error only: the message can
                        # contain the copied text.
                        logger.warning("Could not process a copied line (%s)", type(e).__name__)
                        seen_errors.add(line_lower)

                last_text = text

            time.sleep(2)

        except Exception as e:
            logger.error("Unexpected error (%s)", type(e).__name__)
            time.sleep(2)


if __name__ == "__main__":
    main()
