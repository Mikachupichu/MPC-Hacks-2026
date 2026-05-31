from typing import Any

from pydantic import BaseModel


class ComplianceRule(BaseModel):
    text: str
    department: str = "all"
    category: str = "all"
    severity: str = "Medium"


class ComplianceRuleResponse(BaseModel):
    id: str
    text: str
    department: str
    category: str
    severity: str


class ComplianceScanRequest(BaseModel):
    transaction_ids: list[str] | None = None
    department: str | None = None


class ComplianceResult(BaseModel):
    transaction_id: str
    status: str  # "Compliant" or "Violation"
    severity: str  # "Low", "Medium", "High"
    reasoning: str


class ComplianceScanResponse(BaseModel):
    results: dict[str, dict[str, Any]]
    total_scanned: int
    violations_found: int
