from typing import Any

from pydantic import BaseModel


class ComplianceRule(BaseModel):
    text: str
    code: int | None = None
    department: str = "all"
    category: str = "all"
    severity: str = "Medium"


class ComplianceRuleResponse(BaseModel):
    id: str
    text: str
    code: int | None = None
    department: str
    category: str | None = "all"
    severity: str
    source: str = "custom"


class ComplianceScanRequest(BaseModel):
    transaction_ids: list[str] | None = None
    department: str | None = None


class ComplianceResult(BaseModel):
    transaction_id: str
    status: str
    severity: str
    reasoning: str


class ComplianceScanResponse(BaseModel):
    results: dict[str, dict[str, Any]]
    total_scanned: int
    violations_found: int
