import re
from datetime import datetime, timedelta
from dateparser.search import search_dates


def assume_meridiem(hour):
    if 1 <= hour <= 7:
        return "PM"
    elif 8 <= hour <= 11:
        return "AM"
    else:
        return "PM"


def normalize_time_text(text):
    text = re.sub(r'(\d{1,2})(a)\b', r'\1 AM', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d{1,2})(p)\b', r'\1 PM', text, flags=re.IGNORECASE)
    return text


def extract_time_range(text):
    text = normalize_time_text(text)

    match = re.search(
        r'(\d{1,2})(?::(\d{2}))?\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)?',
        text,
        re.IGNORECASE
    )
    if match:
        sh, sm, eh, em, mer = match.groups()
        sm = sm or "00"
        em = em or "00"
        mer = mer.upper() if mer else assume_meridiem(int(sh))

        return f"{sh}:{sm} {mer}", f"{eh}:{em} {mer}"

    match = re.search(r'(\d{1,2}):(\d{2})', text)
    if match:
        h, m = match.groups()
        mer = assume_meridiem(int(h))
        return f"{h}:{m} {mer}", None

    match = re.search(
        r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM)',
        text,
        re.IGNORECASE
    )
    if match:
        h, m, mer = match.groups()
        m = m or "00"
        return f"{h}:{m} {mer.upper()}", None

    return None, None


def extract_fixed_date(text):
    match = re.search(r'\b(\d{1,2})/(\d{1,2})\b', text)
    if match:
        month, day = match.groups()
        year = datetime.now().year
        return datetime(year, int(month), int(day)).date()
    return None


# ✅ ✅ IMPROVED TITLE CLEANER
def clean_title(text):
    text = normalize_time_text(text)

    # Remove numeric dates
    text = re.sub(r'\b\d{1,2}/\d{1,2}\b', '', text)

    # Remove month names + day (May 22)
    text = re.sub(
        r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b\s*\d{1,2}',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Remove times (7 PM, 2:15 PM)
    text = re.sub(
        r'\b\d{1,2}(:\d{2})?\s*(AM|PM)\b',
        '',
        text,
        flags=re.IGNORECASE
    )

    # Remove leftover "a" / "p" shorthand if any slipped
    text = re.sub(r'\b\d{1,2}(a|p)\b', '', text, flags=re.IGNORECASE)

    # Remove filler phrases
    phrases = ["arrives", "arrive", "event is at", "at", "by", ":"]
    for p in phrases:
        text = re.sub(p, '', text, flags=re.IGNORECASE)

    # Remove dashes and junk characters
    text = re.sub(r'[-–—]', ' ', text)

    # Collapse spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def contains_date_keyword(text):
    return bool(
        re.search(r'\d{1,2}/\d{1,2}', text) or
        any(word in text.lower() for word in [
            "today", "tomorrow", "tonight",
            "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
            "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"
        ])
    )


def parse_event(text):
    original_text = text
    text = normalize_time_text(text.strip())

    if len(text) < 5 or "python3" in text.lower():
        return None

    if not contains_date_keyword(text):
        return None

    now = datetime.now()

    fixed_date = extract_fixed_date(text)

    if fixed_date:
        event_date = fixed_date
    else:
        results = search_dates(
            text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": now
            }
        )

        if not results:
            return None

        event_date = results[0][1].date()

        if event_date.year > now.year + 1:
            event_date = event_date.replace(year=now.year)

    start_time, end_time = extract_time_range(text)

    if not start_time:
        if any(word in text.lower() for word in ["due", "tonight"]):
            start_time = "11:59 PM"
        else:
            start_time = "09:00 AM"

    start_dt = datetime.strptime(
        f"{event_date} {start_time}",
        "%Y-%m-%d %I:%M %p"
    )

    if end_time:
        end_dt = datetime.strptime(
            f"{event_date} {end_time}",
            "%Y-%m-%d %I:%M %p"
        )
    else:
        end_dt = start_dt + timedelta(hours=1)

    title = clean_title(original_text)

    if not title:
        title = "Event"

    return {
        "title": title,
        "date": str(event_date),
        "start_time": start_time,
        "end_time": end_dt.strftime("%I:%M %p"),
        "start_dt": start_dt,
        "end_dt": end_dt
    }