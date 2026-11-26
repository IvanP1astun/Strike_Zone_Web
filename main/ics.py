"""Minimal iCalendar (RFC 5545) writer for game events, standard library only."""
from datetime import timedelta

from django.utils import timezone

PRODID = '-//StrikeZone//Games//RU'
LINE_LIMIT = 75  # octets per line, continuation lines start with a space


def escape_text(value):
    """Escape a TEXT value: backslash, semicolon, comma and line breaks."""
    return (
        str(value)
        .replace('\\', '\\\\')
        .replace(';', '\\;')
        .replace(',', '\\,')
        .replace('\r\n', '\\n')
        .replace('\n', '\\n')
        .replace('\r', '\\n')
    )


def fold(line):
    """Fold a content line to at most 75 octets without splitting a character."""
    if len(line.encode('utf-8')) <= LINE_LIMIT:
        return line
    parts = []
    current = b''
    for char in line:
        encoded = char.encode('utf-8')
        if len(current) + len(encoded) > LINE_LIMIT:
            parts.append(current.decode('utf-8'))
            current = b' '
        current += encoded
    parts.append(current.decode('utf-8'))
    return '\r\n'.join(parts)


def _event_lines(game, url, host, stamp):
    description = [game.description] if game.description else []
    if game.price:
        description.append('%s ₽' % game.price)
    description.append(url)
    lines = [
        'BEGIN:VEVENT',
        'UID:game-%s@%s' % (game.pk, host),
        'DTSTAMP:%s' % stamp,
        # Games have a date but no start time: an all-day event.
        'DTSTART;VALUE=DATE:%s' % game.date.strftime('%Y%m%d'),
        'DTEND;VALUE=DATE:%s' % (game.date + timedelta(days=1)).strftime('%Y%m%d'),
        'SUMMARY:%s' % escape_text(game.name),
        'DESCRIPTION:%s' % escape_text('\n'.join(description)),
        'URL:%s' % url,
    ]
    if game.location:
        lines.append('LOCATION:%s' % escape_text(game.location))
    lines.append('END:VEVENT')
    return lines


def build_calendar(games, url_for, host, name='StrikeZone', now=None):
    """Return the text of a .ics file (CRLF line endings) for the given games.

    url_for(game) must return the absolute URL of the game page.
    """
    stamp = (now or timezone.now()).strftime('%Y%m%dT%H%M%SZ')
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:%s' % PRODID,
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        'X-WR-CALNAME:%s' % escape_text(name),
    ]
    for game in games:
        lines.extend(_event_lines(game, url_for(game), host, stamp))
    lines.append('END:VCALENDAR')
    return '\r\n'.join(fold(line) for line in lines) + '\r\n'
