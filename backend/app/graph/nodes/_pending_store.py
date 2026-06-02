"""Approval workflow helpers — in-memory pending store and DB resume.

The compliance_scanner node handles the actual policy evaluation and
human-in-the-loop interrupt. This module provides the in-memory store
shared with the REST API endpoints.
"""

from typing import Any

from app.core.database import get_collection

# In-memory store for pending approvals (shared with compliance_scanner)
_pending_approvals: dict[str, dict[str, Any]] = {}


async def resume_approval(transaction_id: str, approved: bool) -> dict[str, Any]:
    """Resume the approval workflow with a manager decision.

    Preserves the AI's recommendation (from compliance_results) on the transaction
    as ``ai_recommendation``, separate from the human's ``approval_status`` decision.
    """
    status = "approved" if approved else "denied"

    # Check in-memory store first
    packet = _pending_approvals.get(transaction_id)
    if packet:
        ai_recommendation = (
            packet.get("compliance_results", {}).get("recommendation")
            or packet.get("transaction", {}).get("recommendation")
        )
        packet["status"] = status
        packet["transaction"]["approval_status"] = status
        del _pending_approvals[transaction_id]

        try:
            collection = await get_collection("transactions")
            update: dict[str, Any] = {
                "approval_status": status,
            }
            if ai_recommendation:
                update["ai_recommendation"] = ai_recommendation
            await collection.update_one(
                {"transaction_id": transaction_id},
                {"$set": update},
            )
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}
    else:
        # Not in memory — update directly in DB
        try:
            collection = await get_collection("transactions")
            existing = await collection.find_one(
                {"transaction_id": transaction_id},
                {"recommendation": 1},
            )
            update: dict[str, Any] = {
                "approval_status": status,
            }
            if existing and existing.get("recommendation"):
                update["ai_recommendation"] = existing["recommendation"]
            result = await collection.update_one(
                {"transaction_id": transaction_id},
                {"$set": update},
            )
            if result.matched_count == 0:
                return {"error": f"No pending approval found for {transaction_id}"}
        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

    return {
        "transaction_id": transaction_id,
        "status": status,
        "message": f"Transaction {transaction_id} has been {status}.",
    }


async def get_pending_approvals() -> list[dict[str, Any]]:
    """Get all pending approvals with context."""
    return [
        {
            "transaction_id": k,
            "transaction": v["transaction"],
            "compliance_results": v.get("compliance_results", {}),
            "employee_context": v.get("employee_context", {}),
            "department_context": v.get("department_context", {}),
            "status": v["status"],
        }
        for k, v in _pending_approvals.items()
    ]
