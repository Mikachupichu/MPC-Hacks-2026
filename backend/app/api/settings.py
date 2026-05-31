from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.time_range import get_app_time_range_months, set_app_time_range_months

router = APIRouter()


class TimeRangeRequest(BaseModel):
    months: int = Field(ge=1, le=12)


class TimeRangeResponse(BaseModel):
    months: int


@router.get("/settings/time-range", response_model=TimeRangeResponse)
async def get_time_range():
    """Get the application-wide time range setting."""
    try:
        months = await get_app_time_range_months()
        return TimeRangeResponse(months=months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/time-range", response_model=TimeRangeResponse)
async def set_time_range(request: TimeRangeRequest):
    """Set the application-wide time range setting."""
    try:
        await set_app_time_range_months(request.months)
        return TimeRangeResponse(months=request.months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
