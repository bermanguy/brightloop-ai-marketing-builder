"""Turn the timestamp formats seen in signals into UTC ISO 8601."""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _zone(name):
    try:
        return ZoneInfo(name) if name else timezone.utc
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def to_utc(value, default_tz=None):
    """Return a UTC ISO string ("2026-10-24T20:30:00Z"), or None if unreadable.

    A time with no zone is read in `default_tz` (the input's `timezone`).
    A bare date stays a date, since it has no time of day to convert.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        moment = datetime.fromtimestamp(value, tz=timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    # "2026-10-24 20:30 UTC" and "...Z" are not accepted by fromisoformat everywhere.
    text = re.sub(r"\s*(UTC|GMT|Z)$", "+00:00", text, flags=re.IGNORECASE)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=_zone(default_tz))
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
