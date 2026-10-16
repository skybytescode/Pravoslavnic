"""Generate docs/pravoslavnic.ics — the twelve daily services as a calendar.

Each service is a daily-repeating event in Europe/Chisinau (the same zone the
player uses) with a display alarm 5 minutes before it, mirroring the player's
reminder. Importing the file into Apple/Google Calendar gives reminders that
fire even when the app is closed, which iOS web apps can't schedule.

Durations are the read-aloud estimates, rounded up to 5 minutes.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_pages import SCHEDULE

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "pravoslavnic.ics"
SITE = "https://skybytescode.github.io/Pravoslavnic/"
START_DATE = "20261016"         # first day of the series; past days are ignored
REMINDER_MINUTES = 5            # matches REMINDER_OFFSET in docs/js/player.js

DURATION_MINUTES = {
    "01-miezonoptica":   5,
    "02-utrenia":       15,
    "03-ceasul-1":      10,
    "04-mijloceasul-1": 10,
    "05-ceasul-3":      10,
    "06-mijloceasul-3":  5,
    "07-ceasul-6":      15,
    "08-mijloceasul-6":  5,
    "09-ceasul-9":      10,
    "10-mijloceasul-9": 10,
    "11-vecernia":      10,
    "12-pavecernita":   15,
}

# Moldova: EEST from the last Sunday of March 02:00, EET from the last Sunday
# of October 03:00 (local time).
VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Chisinau
BEGIN:DAYLIGHT
TZOFFSETFROM:+0200
TZOFFSETTO:+0300
TZNAME:EEST
DTSTART:19970330T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0300
TZOFFSETTO:+0200
TZNAME:EET
DTSTART:19971026T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def escape(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")


def fold(line):
    """Fold a content line at 75 octets (RFC 5545 §3.1), never splitting a
    UTF-8 character."""
    out, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > (75 if not out else 74):
            out.append(current.decode("utf-8"))
            current = b""
        current += b
    out.append(current.decode("utf-8"))
    return "\r\n ".join(out)


def event(time, slug, title, stamp):
    hh, mm = time.split(":")
    url = f"{SITE}content/{slug}.html"
    return [
        "BEGIN:VEVENT",
        f"UID:{slug}@pravoslavnic.skybytescode.github.io",
        f"DTSTAMP:{stamp}",
        f"DTSTART;TZID=Europe/Chisinau:{START_DATE}T{hh}{mm}00",
        f"DURATION:PT{DURATION_MINUTES[slug]}M",
        "RRULE:FREQ=DAILY",
        f"SUMMARY:☦ {escape(title)}",
        f"DESCRIPTION:{escape(title)} — {url}",
        f"URL:{url}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{escape(title)} în {REMINDER_MINUTES} minute",
        f"TRIGGER:-PT{REMINDER_MINUTES}M",
        "END:VALARM",
        "END:VEVENT",
    ]


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Pravoslavnic//Ceasurile zilei//RO",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Pravoslavnic",
        "X-WR-TIMEZONE:Europe/Chisinau",
        *VTIMEZONE.splitlines(),
    ]
    for time, slug, title, _ in SCHEDULE:
        lines += event(time, slug, title, stamp)
    lines.append("END:VCALENDAR")
    OUT.write_bytes(("\r\n".join(fold(l) for l in lines) + "\r\n").encode("utf-8"))
    print(f"wrote {OUT.relative_to(ROOT)} ({len(SCHEDULE)} events)")


if __name__ == "__main__":
    main()
