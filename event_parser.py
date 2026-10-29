"""Finds an event (title, date, start and end time) in a piece of copied text.

How it works:
  1. Find a DATE: "11/5", "Nov 5", "June 2nd", "today", "tomorrow", "Friday".
     No date means it isn't an event: plain text that happens to contain a
     time ("call me at 3 PM") is ignored.
  2. Find a TIME or time range: "2-4 PM", "11-1", "13-15", "9:15am", "2p".
     No time means 9:00 AM, or 11:00-11:59 PM for things that are "due".
  3. The TITLE is what's left after removing the date and time (plus the
     little words that went with them, like "at" or "on").

Each step is a regular expression with word boundaries, so "may" in "you
may want" isn't May, and "at" inside "Data" is never removed.
"""

import re
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple

DEFAULT_TIME = time(9, 0)
# A deadline with no time ("Essay due Friday") is shown as the last hour of
# that day, so the calendar entry doesn't spill past midnight.
DUE_START, DUE_END = time(23, 0), time(23, 59)
TONIGHT_TIME = time(19, 0)
DEFAULT_LENGTH = timedelta(hours=1)
# A date with no year that is more than this far in the past is assumed to
# mean next year (copying "Exam 1/5" in December means January).
PAST_GRACE = timedelta(days=7)

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Little words that belong to a date or time ("on 11/5", "at 3 PM").
# They are removed along with it so the title doesn't end in "at".
_LEAD = r"(?:\b(?:at|on|from|by)\s+|@\s*)?"

# 11/5 or 11/5/2026. Not part of a longer number or path.
NUMERIC_DATE = re.compile(_LEAD + r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?(?![\d/])")
# "1/2 cup", "3/4 of": fractions followed by a unit are not dates.
FRACTION_UNIT = re.compile(
    r"\s*(?:cups?|tsp|tbsp|teaspoons?|tablespoons?|oz|ounces?|lbs?|pounds?|inch(?:es)?|"
    r"miles?|kg|grams?|ml|liters?|litres?|of|hours?|hrs?)\b",
    re.IGNORECASE,
)
# Nov 5, November 5th, Sept. 12. The month name must be followed by a day
# number, so "may" (the verb) or "separate" never count.
MONTH_DATE = re.compile(
    _LEAD + r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.IGNORECASE,
)
RELATIVE_DATE = re.compile(
    _LEAD + r"\b(today|tonight|tomorrow|(?:next\s+|this\s+)?(?:" + "|".join(WEEKDAYS) + r"))\b",
    re.IGNORECASE,
)

# am/pm after a number: "2 PM", "2pm", "2 p.m.", or the shorthand "2p" (no space).
_MER = r"(?:\s*([ap])\.?m\b\.?|([ap])\b)"
TIME_RANGE = re.compile(
    _LEAD + r"(?<![\d/:.\-])(\d{1,2})(?::(\d{2}))?" + _MER + r"?\s*(?:-|–|—|to)\s*"
    r"(\d{1,2})(?::(\d{2}))?" + _MER + r"?(?![\d/:])",
    re.IGNORECASE,
)
SINGLE_TIME = re.compile(
    _LEAD + r"(?<![\d/:.\-])(\d{1,2})(?::(\d{2}))?" + _MER + r"(?![\d/:])"  # 3 PM, 9:15am, 2p
    r"|" + _LEAD + r"(?<![\d/:.\-])(\d{1,2}):(\d{2})(?![\d/:])",  # 14:30 or 2:30
    re.IGNORECASE,
)


def _guess_meridiem(hour: int) -> str:
    """For times like "2" with no AM/PM: 1-7 is probably afternoon/evening
    (class at 2 means 2 PM), 8-11 probably morning, 12 noon."""
    return "a" if 8 <= hour <= 11 else "p"


def _to_24h(hour: int, meridiem: str) -> int:
    return hour % 12 + (12 if meridiem == "p" else 0)


def _valid_time(hour: int, minute: int) -> bool:
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _find_time(text: str) -> Tuple[Optional[time], Optional[time], List[Tuple[int, int]]]:
    """(start, end, spans to remove from the title). end may be None."""
    for m in TIME_RANGE.finditer(text):
        sh, sm, smer1, smer2, eh, em, emer1, emer2 = m.groups()
        sh, eh, sm, em = int(sh), int(eh), int(sm or 0), int(em or 0)
        smer = (smer1 or smer2 or "").lower() or None
        emer = (emer1 or emer2 or "").lower() or None

        if sh > 12 or eh > 12:  # 24-hour clock: "13-15"
            start_h, end_h = sh, eh
        elif smer and emer:
            start_h, end_h = _to_24h(sh, smer), _to_24h(eh, emer)
        elif emer:  # "11-1 PM": 11 AM to 1 PM, "1-3 PM": 1 PM to 3 PM
            end_h = _to_24h(eh, emer)
            start_h = _to_24h(sh, emer)
            if start_h > end_h:
                start_h -= 12
        else:  # "2-4", "11-1", or "9am-2"
            start_h = _to_24h(sh, smer or _guess_meridiem(sh))
            end_h = _to_24h(eh, "a" if start_h < 12 else "p")
            if end_h <= start_h:  # crossed noon: "11-1" ends at 1 PM
                end_h += 12
            end_h %= 24

        if _valid_time(start_h, sm) and _valid_time(end_h, em):
            return time(start_h, sm), time(end_h, em), [m.span()]

    for m in SINGLE_TIME.finditer(text):
        h1, m1, mer1, mer2, h2, m2 = m.groups()
        if h1 is not None:
            hour, minute = int(h1), int(m1 or 0)
            meridiem = (mer1 or mer2).lower()
            if hour > 12:
                continue
            hour = _to_24h(hour, meridiem)
        else:
            hour, minute = int(h2), int(m2)
            if hour <= 12:  # "2:30" without AM/PM
                hour = _to_24h(hour, _guess_meridiem(hour))
        if _valid_time(hour, minute):
            return time(hour, minute), None, [m.span()]

    return None, None, []


def _with_year(month: int, day: int, year: Optional[int], today: date) -> Optional[date]:
    try:
        if year is not None:
            return date(year if year > 99 else 2000 + year, month, day)
        candidate = date(today.year, month, day)
        if candidate < today - PAST_GRACE:
            candidate = date(today.year + 1, month, day)
        return candidate
    except ValueError:  # 13/45, Feb 30, ...
        return None


def _find_date(text: str, today: date) -> Tuple[Optional[date], List[Tuple[int, int]], bool]:
    """(date, spans to remove, said "tonight")."""
    for m in NUMERIC_DATE.finditer(text):
        if FRACTION_UNIT.match(text, m.end()):
            continue
        month, day, year = m.groups()
        found = _with_year(int(month), int(day), int(year) if year else None, today)
        if found:
            return found, [m.span()], False

    for m in MONTH_DATE.finditer(text):
        month_name, day = m.groups()
        found = _with_year(MONTHS[month_name[:3].lower()], int(day), None, today)
        if found:
            return found, [m.span()], False

    m = RELATIVE_DATE.search(text)
    if m:
        word = m.group(1).lower()
        if word in ("today", "tonight"):
            return today, [m.span()], word == "tonight"
        if word == "tomorrow":
            return today + timedelta(days=1), [m.span()], False
        weekday = WEEKDAYS.index(word.split()[-1])
        days_ahead = (weekday - today.weekday()) % 7
        if word.startswith("next") and days_ahead == 0:
            days_ahead = 7  # "next Friday" said on a Friday means a week out
        return today + timedelta(days=days_ahead), [m.span()], False

    return None, [], False


def _clean_title(text: str, spans: List[Tuple[int, int]]) -> str:
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + " " + text[end:]
    text = re.sub(r"\s+", " ", text)
    # Leftover punctuation or connecting words at either end: "Exam -", "at".
    junk = r"[\s,;:@\-–—]+|\b(?:at|on|from|by)\b"
    previous = None
    while previous != text:
        previous = text
        text = re.sub(rf"^(?:{junk})\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(rf"\s*(?:{junk})$", "", text, flags=re.IGNORECASE)
    return text.strip()


def parse_event(text: str, now: Optional[datetime] = None) -> Optional[dict]:
    """The event in `text`, or None if it doesn't contain one."""
    now = now or datetime.now()
    text = text.strip()
    if len(text) < 5:
        return None

    event_date, date_spans, tonight = _find_date(text, now.date())
    if event_date is None:
        return None

    # Look for the time only outside the date, so "11/5" can't be read as a time.
    masked = text
    for start, end in date_spans:
        masked = masked[:start] + " " * (end - start) + masked[end:]
    start_time, end_time, time_spans = _find_time(masked)

    if start_time is None:
        if re.search(r"\bdue\b", text, re.IGNORECASE):
            start_time, end_time = DUE_START, DUE_END
        elif tonight:
            start_time = TONIGHT_TIME
        else:
            start_time = DEFAULT_TIME

    start_dt = datetime.combine(event_date, start_time)
    if end_time is None:
        end_dt = start_dt + DEFAULT_LENGTH
    else:
        end_dt = datetime.combine(event_date, end_time)
        if end_dt <= start_dt:  # "11 PM - 1 AM" ends the next day
            end_dt += timedelta(days=1)

    title = _clean_title(text, date_spans + time_spans) or "Event"

    return {
        "title": title,
        "date": event_date.isoformat(),
        "start_time": start_dt.strftime("%I:%M %p"),
        "end_time": end_dt.strftime("%I:%M %p"),
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


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
