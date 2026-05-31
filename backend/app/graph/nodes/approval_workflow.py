from typing import Any

from app.graph.state import GraphState

# In-memory store for pending approvals (in production, use MongoDB checkpoints)
_pending_approvals: dict[str, dict[str, Any]] = {}


async def approval_workflow_node(state: GraphState) -> dict[str, Any]:
    """Handles the Human-in-the-Loop approval lifecycle.

    This node logs the approval request, pauses, and waits for a manager decision
    via the /api/approve/resume endpoint. LangGraph's interrupt_before handles
    the graph pause; this function prepares the data packet.
    """
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"pending_approval": None, "error": "No transaction for approval"}

    # Take the first transaction as the approval request
    txn = transactions[0]
    txn_id = txn.get("transaction_id", str(txn.get("_id", "unknown")))

    approval_packet = {
        "transaction_id": txn_id,
        "transaction": txn,
        "status": "pending",
        "compliance_results": state.get("compliance_results", {}).get(txn_id, {}),
    }

    # Store for resume endpoint
    _pending_approvals[txn_id] = approval_packet

    return {
        "pending_approval": approval_packet,
        "messages": state.get("messages", [])
        + [
            {
                "role": "assistant",
                "content": f"Approval request created for transaction {txn_id}. "
                f"Waiting for manager decision.",
            }
        ],
    }


async def resume_approval(transaction_id: str, approved: bool) -> dict[str, Any]:
    """Resume the approval workflow with a manager decision."""
    packet = _pending_approvals.get(transaction_id)
    if not packet:
        return {"error": f"No pending approval found for {transaction_id}"}

    packet["status"] = "approved" if approved else "denied"

    if approved:
        packet["transaction"]["approval_status"] = "approved"
    else:
        packet["transaction"]["approval_status"] = "denied"

    # Cleanup
    del _pending_approvals[transaction_id]

    return {
        "transaction_id": transaction_id,
        "status": packet["status"],
        "transaction": packet["transaction"],
        "message": f"Transaction {transaction_id} has been {'approved' if approved else 'denied'}.",
    }


async def get_pending_approvals() -> list[dict[str, Any]]:
    """Get all pending approvals."""
    return [
        {
            "transaction_id": k,
            "transaction": v["transaction"],
            "compliance_results": v.get("compliance_results", {}),
            "status": v["status"],
        }
        for k, v in _pending_approvals.items()
    ]
