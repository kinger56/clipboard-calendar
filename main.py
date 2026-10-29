import time
import json
import os
import logging
import pyperclip
import re
from datetime import datetime

from ai_parser import parse_event
from calendar_manager import add_calendar_event
from notification_manager import send_notification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_FILE = os.path.join(BASE_DIR, "processed_events.json")


def setup_logging():
    logging.basicConfig(
        filename="assistant.log",
        level=logging.INFO,
        format="%(asctime)s - %(message)s"
    )

    error_logger = logging.getLogger("error")
    handler = logging.FileHandler("assistant_error.log")
    error_logger.addHandler(handler)

    return error_logger


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
    error_logger = setup_logging()
    processed = load_processed()

    last_text = ""
    seen_errors = set()

    print("Clipboard Assistant is running...")
    print("Copy text containing assignments or events to test.\n")

    while True:
        try:
            text = pyperclip.paste().strip()

            if text and text != last_text:

                event_lines = split_events(text)

                for line in event_lines:
                    line_lower = line.lower()

                    if line_lower in seen_errors:
                        continue

                    print(f"\nDetected: {line}")

                    try:
                        parsed = parse_event(line)
                        print("PARSED RESULT:", parsed)

                        if parsed:
                            if is_duplicate(parsed, processed):
                                send_notification("Duplicate Event", "Event already exists")
                                print("⚠️ Duplicate event skipped.\n")
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

                                print("✅ Event added.\n")

                        else:
                            print("❌ Could not parse event.\n")
                            seen_errors.add(line_lower)

                    except Exception as e:
                        print(f"❌ Processing error: {e}\n")
                        error_logger.error(f"{line} → {e}")
                        seen_errors.add(line_lower)

                last_text = text

            time.sleep(2)

        except Exception as e:
            print(f"Critical error: {e}")
            error_logger.error(str(e))
            time.sleep(2)


if __name__ == "__main__":
    main()
