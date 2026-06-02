"""LangGraph state graph definition — 3-node orchestrator."""

from functools import lru_cache
from typing import Any

from app.graph.nodes.compliance_scanner import compliance_scanner_node
from app.graph.nodes.conversational_analyst import conversational_analyst_node
from app.graph.nodes.report_compiler import report_compiler_node
from app.graph.state import GraphState

try:
    from langgraph.graph import END, StateGraph

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None
    END = None


def _route_from_analyst(state: GraphState) -> str:
    """Route from conversational_analyst based on task_type or keyword match."""
    task_type = state.get("task_type", "") or ""

    if task_type == "chat":
        return END
    if task_type in ("compliance", "approval"):
        return "compliance_scanner"
    if task_type == "report":
        return "report_compiler"

    intent = state.get("user_query", "")
    if not intent:
        return END

    intent_lower = intent.lower()
    if any(word in intent_lower for word in ("scan", "compliance", "violation", "policy")):
        return "compliance_scanner"
    if any(word in intent_lower for word in ("report", "summary", "compile")):
        return "report_compiler"
    if any(word in intent_lower for word in ("approve", "approval", "pre-approve")):
        return "compliance_scanner"

    return END


def build_expense_graph() -> Any:
    """Build the 3-node LangGraph for expense intelligence.

    Nodes:
      1. conversational_analyst  — chat entry point
      2. compliance_scanner      — policy evaluation, may interrupt for human approval
      3. report_compiler         — generates expense reports
    """
    if not HAS_LANGGRAPH:
        raise ImportError("langgraph is required to build the graph")

    workflow = StateGraph(GraphState)

    workflow.add_node("conversational_analyst", conversational_analyst_node)
    workflow.add_node("compliance_scanner", compliance_scanner_node)
    workflow.add_node("report_compiler", report_compiler_node)

    workflow.set_entry_point("conversational_analyst")

    workflow.add_conditional_edges(
        "conversational_analyst",
        _route_from_analyst,
        {
            "compliance_scanner": "compliance_scanner",
            "report_compiler": "report_compiler",
            END: END,
        },
    )

    workflow.add_edge("compliance_scanner", END)
    workflow.add_edge("report_compiler", END)

    return workflow.compile()


@lru_cache(maxsize=1)
def get_graph() -> Any:
    """Return a cached compiled graph singleton."""
    return build_expense_graph()


__all__ = [
    "conversational_analyst_node",
    "compliance_scanner_node",
    "report_compiler_node",
    "build_expense_graph",
    "get_graph",
]
