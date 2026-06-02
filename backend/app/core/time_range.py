from app.core.clock import FIXED_DATETIME_UTC
from app.core.database import get_collection

DEFAULT_MONTHS = 12

# In-memory cache so reads work even when MongoDB is unreachable
_cached_months: int | None = None


async def get_app_time_range_months() -> int:
    """Read the app-wide time range setting — from in-memory cache if available, else DB."""
    global _cached_months
    if _cached_months is not None:
        return _cached_months
    try:
        collection = await get_collection("app_settings")
        doc = await collection.find_one({"_key": "time_range"})
        if doc and "months" in doc:
            _cached_months = int(doc["months"])
            return _cached_months
    except Exception:
        pass
    return DEFAULT_MONTHS


async def set_app_time_range_months(months: int) -> None:
    """Persist the app-wide time range setting in memory and DB."""
    global _cached_months
    _cached_months = months
    try:
        collection = await get_collection("app_settings")
        await collection.update_one(
            {"_key": "time_range"},
            {"$set": {"months": months}},
            upsert=True,
        )
    except Exception:
        pass  # Memory cache is live even if DB write fails


def compute_cutoff_date(months: int) -> str:
    """Return an ISO date string N months ago from the fixed date (2026-05-31).

    When ``months`` is 0, returns an empty string meaning "no cutoff" —
    callers should skip date filtering.
    """
    if months <= 0:
        return ""
    now = FIXED_DATETIME_UTC
    month = now.month - months
    year = now.year
    while month <= 0:
        month += 12
        year -= 1
    cutoff = now.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    return cutoff.strftime("%Y-%m-%d")


async def get_app_cutoff_date() -> str:
    """Convenience: read setting and return cutoff date string."""
    months = await get_app_time_range_months()
    return compute_cutoff_date(months)
