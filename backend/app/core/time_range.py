from datetime import datetime, timezone

from app.core.database import get_collection

DEFAULT_MONTHS = 12


async def get_app_time_range_months() -> int:
    """Read the app-wide time range setting from the database."""
    try:
        collection = await get_collection("app_settings")
        doc = await collection.find_one({"_key": "time_range"})
        if doc and "months" in doc:
            return int(doc["months"])
    except Exception:
        pass
    return DEFAULT_MONTHS


async def set_app_time_range_months(months: int) -> None:
    """Persist the app-wide time range setting."""
    collection = await get_collection("app_settings")
    await collection.update_one(
        {"_key": "time_range"},
        {"$set": {"months": months}},
        upsert=True,
    )


def compute_cutoff_date(months: int) -> str:
    """Return an ISO date string N months ago from today (UTC)."""
    now = datetime.now(timezone.utc)
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
