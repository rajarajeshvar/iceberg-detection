from datetime import datetime, timezone, timedelta
from typing import Union


def parse_timestamp(ts: Union[str, datetime]) -> datetime:
    """
    Parse an ISO-8601 timestamp string or return timezone-aware datetime.
    """
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts

    # Remove 'Z' suffix for Python datetime fromisoformat compatibility if needed
    clean_ts = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
    dt = datetime.fromisoformat(clean_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def format_iso(dt: datetime) -> str:
    """
    Format a datetime object as an ISO-8601 UTC string ending in 'Z'.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def add_hours(dt: datetime, hours: float) -> datetime:
    """
    Add a specified number of hours to a datetime.
    """
    return dt + timedelta(hours=hours)
