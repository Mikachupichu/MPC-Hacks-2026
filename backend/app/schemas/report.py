from typing import Any

from pydantic import BaseModel


class ReportRequest(BaseModel):
    transaction_ids: list[str] | None = None
    department: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class ReportResponse(BaseModel):
    report_payload: dict[str, Any]
    compliance_results: dict[str, dict[str, Any]] = {}
    error: str | None = None
