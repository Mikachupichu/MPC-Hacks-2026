from typing import Any

from app.core.database import get_collection
from app.graph.state import GraphState

# In-memory store for pending approvals (in production, use MongoDB checkpoints)
_pending_approvals: dict[str, dict[str, Any]] = {}


async def _fetch_employee_context(employee: str) -> dict:
    """Fetch employee YTD spend and transaction history."""
    if not employee:
        return {}
    try:
        collection = await get_collection("transactions")
        emp_txns = await collection.find(
            {"employee": employee},
            {"_id": 0, "transaction_id": 1, "amount": 1, "merchant": 1, "date": 1},
        ).sort("date", -1).to_list(500)
        total_spent = sum(t.get("amount", 0) for t in emp_txns)
        return {
            "employee": employee,
            "total_spent_ytd": round(total_spent, 2),
            "transaction_count": len(emp_txns),
            "recent_transactions": emp_txns[:5],
        }
    except Exception:
        return {"employee": employee, "error": "Could not fetch history"}


async def _fetch_department_context(department: str) -> dict:
    """Fetch department YTD spend and budget."""
    if not department:
        return {}
    try:
        txns_col = await get_collection("transactions")
        dept_txns = await txns_col.find(
            {"department": department},
            {"_id": 0, "amount": 1, "date": 1},
        ).to_list(1000)
        dept_total = sum(t.get("amount", 0) for t in dept_txns)

        # Fetch department budget
        budget = None
        try:
            budget_col = await get_collection("department_budgets")
            budget_doc = await budget_col.find_one({"department": department}, {"_id": 0})
            budget = budget_doc
        except Exception:
            pass

        months = len(set(str(t.get("date", ""))[:7] for t in dept_txns if t.get("date")))
        monthly_avg = round(dept_total / max(months, 1), 2)

        dept_ctx = {
            "department": department,
            "total_spent_ytd": round(dept_total, 2),
            "monthly_avg_spend": monthly_avg,
            "transaction_count": len(dept_txns),
        }
        if budget:
            dept_ctx["annual_budget"] = budget.get("annual_budget")
            dept_ctx["monthly_budget"] = budget.get("monthly_budget")
            dept_ctx["budget_remaining"] = round(budget.get("annual_budget", 0) - dept_total, 2)
            dept_ctx["budget_used_pct"] = round((dept_total / max(budget.get("annual_budget", 1), 1)) * 100, 1)
        return dept_ctx
    except Exception:
        return {"department": department, "error": "Could not fetch budget data"}


async def approval_workflow_node(state: GraphState) -> dict[str, Any]:
    """Handles the Human-in-the-Loop approval lifecycle."""
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"pending_approval": None, "error": "No transaction for approval"}

    txn = transactions[0]
    txn_id = txn.get("transaction_id", str(txn.get("_id", "unknown")))

    employee_context = await _fetch_employee_context(txn.get("employee", ""))
    dept_context = await _fetch_department_context(txn.get("department", ""))

    approval_packet = {
        "transaction_id": txn_id,
        "transaction": txn,
        "status": "pending",
        "compliance_results": state.get("compliance_results", {}).get(txn_id, {}),
        "employee_context": employee_context,
        "department_context": dept_context,
    }

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
    status = "approved" if approved else "denied"

    # Check in-memory store first
    packet = _pending_approvals.get(transaction_id)
    if packet:
        packet["status"] = status
        packet["transaction"]["approval_status"] = status
        del _pending_approvals[transaction_id]
    else:
        # Not in memory — update directly in DB
        try:
            from app.core.database import get_collection
            collection = await get_collection("transactions")
            result = await collection.update_one(
                {"transaction_id": transaction_id},
                {"$set": {"approval_status": status}},
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
