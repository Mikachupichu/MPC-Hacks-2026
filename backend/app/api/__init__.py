from fastapi import APIRouter

api_router = APIRouter()

from app.api.health import router as health_router  # noqa: E402
from app.api.chat import router as chat_router  # noqa: E402
from app.api.compliance import router as compliance_router  # noqa: E402
from app.api.approval import router as approval_router  # noqa: E402
from app.api.reports import router as reports_router  # noqa: E402
from app.api.transactions import router as transactions_router  # noqa: E402

api_router.include_router(health_router, tags=["health"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(compliance_router, tags=["compliance"])
api_router.include_router(approval_router, tags=["approval"])
api_router.include_router(reports_router, tags=["reports"])
api_router.include_router(transactions_router, tags=["transactions"])
