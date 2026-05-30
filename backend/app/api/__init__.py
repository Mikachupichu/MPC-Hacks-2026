from fastapi import APIRouter

api_router = APIRouter()

from app.api.health import router as health_router  # noqa: E402

api_router.include_router(health_router, tags=["health"])
