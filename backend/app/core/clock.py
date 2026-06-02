"""Fixed system clock — freezes the current date to 2026-05-31 23:59."""

from datetime import datetime, timezone

FIXED_DATE = "2026-05-31"
"""Fixed date string (ISO) used for default transaction dates, etc."""

FIXED_DATETIME = datetime(2026, 5, 31, 23, 59)
"""Naive datetime — matches the pattern used by ``datetime.now()`` in the codebase."""

FIXED_DATETIME_UTC = datetime(2026, 5, 31, 23, 59, tzinfo=timezone.utc)
"""Timezoned datetime — used by ``compute_cutoff_date`` in ``time_range.py``."""


def now() -> datetime:
    """Return the fixed current date/time (naive, matching ``datetime.now()``).

    Replace every ``datetime.now()`` call in the system with this so all
    components see the same reference time.
    """
    return FIXED_DATETIME
