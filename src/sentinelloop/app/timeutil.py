"""Time handling for the platform: every stored instant is integer milliseconds since the Unix epoch, UTC.

Naive timestamps (no offset) are refused unless the caller names the time zone they were recorded in;
silently assuming a zone is how a five-and-a-half-hour shift ends up in a maintenance record.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS


class NaiveTimestampError(ValueError):
    """A timestamp without a UTC offset and no declared time zone."""


def parse_ts(value, default_tz: str | None = None) -> int:
    """ISO-8601 text or an aware datetime -> epoch milliseconds (UTC)."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        s = value.strip()
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)          # raises ValueError for unparseable text
    else:
        raise ValueError(f"timestamp must be ISO-8601 text or a datetime, got {type(value).__name__}")
    if dt.tzinfo is None:
        if not default_tz:
            raise NaiveTimestampError(f"timestamp {value!r} has no UTC offset and no time zone was declared")
        dt = dt.replace(tzinfo=ZoneInfo(default_tz))
    return (dt - EPOCH) // timedelta(milliseconds=1)


def iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    dt = EPOCH + timedelta(milliseconds=int(ms))
    if int(ms) % 1000:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(ms) % 1000:03d}Z"
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def now_ms() -> int:
    return (datetime.now(timezone.utc) - EPOCH) // timedelta(milliseconds=1)


def now_iso() -> str:
    return iso(now_ms())
