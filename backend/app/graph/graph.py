"""LangGraph state graph definition for the Agentic Expense Intelligence platform."""

from typing import Any

from app.graph.nodes.approval_workflow import approval_workflow_node
from app.graph.nodes.compliance_scanner import compliance_scanner_node
from app.graph.nodes.conversational_analyst import conversational_analyst_node
from app.graph.nodes.report_compiler import report_compiler_node
from app.graph.state import GraphState

# LangGraph may not be available if only running API routes directly
try:
    from langgraph.graph import END, StateGraph

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False
    StateGraph = None
    END = None


def build_expense_graph() -> Any:
    """Build the LangGraph state graph for expense intelligence.

    Graph structure:
        1. conversational_analyst_node (chat entry point)
        2. compliance_scanner_node (policy evaluation)
        3. approval_workflow_node (human-in-the-loop)
        4. report_compiler_node (expense report)

    The graph routes based on the user's intent, which is set in the state
    by the calling API route before invoking the graph.
    """
    if not HAS_LANGGRAPH:
        raise ImportError("langgraph is required to build the graph")

    workflow = StateGraph(GraphState)

    # Register nodes
    workflow.add_node("conversational_analyst", conversational_analyst_node)
    workflow.add_node("compliance_scanner", compliance_scanner_node)
    workflow.add_node("approval_workflow", approval_workflow_node)
    workflow.add_node("report_compiler", report_compiler_node)

    # Set entry point
    workflow.set_entry_point("conversational_analyst")

    # Define routing logic based on intent
    def route_from_analyst(state: GraphState) -> str:
        intent = state.get("user_query", "")
        if not intent:
            return END

        intent_lower = intent.lower()

        # Check for compliance/report intents
        if any(word in intent_lower for word in ["scan", "compliance", "violation", "policy"]):
            return "compliance_scanner"

        if any(word in intent_lower for word in ["report", "summary", "compile"]):
            return "report_compiler"

        if any(word in intent_lower for word in ["approve", "approval", "pre-approve"]):
            return "approval_workflow"

        # Default: stay in conversational loop
        return END

    # Add conditional edges
    workflow.add_conditional_edges(
        "conversational_analyst",
        route_from_analyst,
        {
            "compliance_scanner": "compliance_scanner",
            "report_compiler": "report_compiler",
            "approval_workflow": "approval_workflow",
            END: END,
        },
    )

    # Compliance scanner can route to report compiler if needed
    workflow.add_edge("compliance_scanner", END)

    # Approval workflow ends after decision
    workflow.add_edge("approval_workflow", END)

    # Report compiler feeds back to conversational
    workflow.add_edge("report_compiler", END)

    return workflow.compile()


# Export nodes for direct use by API routes
__all__ = [
    "conversational_analyst_node",
    "compliance_scanner_node",
    "approval_workflow_node",
    "report_compiler_node",
    "build_expense_graph",
]
