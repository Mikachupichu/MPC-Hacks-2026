from typing import Any

from typing_extensions import TypedDict


class GraphState(TypedDict):
    """Shared LangGraph state for the expense intelligence graph."""

    messages: list[dict[str, Any]]
    current_transactions: list[dict[str, Any]]
    compliance_results: dict[str, dict[str, Any]]
    report_payload: dict[str, Any]
    pending_approval: dict[str, Any] | None
    user_query: str | None
    conversation_id: str | None
    error: str | None
