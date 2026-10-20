---
status: accepted
---

# Hand-written iCalendar feeds

Calendar feeds are plain text built in `services/calendar.py`: all-day `VEVENT`s with `UID`, `DTSTAMP`, `DTSTART`/`DTEND` (exclusive end), `SUMMARY`, `DESCRIPTION` and `URL`, with RFC 5545 escaping and line folding. Access is by a random token (192 bit, stored hashed); every fetch re-checks that the owner may still see the content.

A library (`icalendar`) was rejected because the feeds use a handful of fields and no recurrence or time zones; the tests pin the format.
