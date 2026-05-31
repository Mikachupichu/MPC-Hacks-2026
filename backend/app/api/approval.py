import asyncio
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from app.core.database import get_collection
from app.graph.nodes.approval_workflow import (
    get_pending_approvals as get_in_memory_pending,
    resume_approval,
)
from app.schemas.approval import ApprovalResumeRequest, ApprovalResumeResponse

router = APIRouter()


@router.post("/approve/submit")
async def submit_for_approval():
    return {"message": "Approval request submitted.", "status": "pending"}


@router.post("/approve/resume", response_model=ApprovalResumeResponse)
async def resume_approval_endpoint(request: ApprovalResumeRequest):
    try:
        result = await resume_approval(request.transaction_id, request.approved)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return ApprovalResumeResponse(
            transaction_id=result["transaction_id"],
            status=result["status"],
            message=result["message"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approve/pending")
async def list_pending_approvals():
    """List all pending approvals from both in-memory store and database."""
    try:
        # Get from in-memory store (LangGraph workflow approvals)
        in_memory = await get_in_memory_pending()

        # Get from database (transactions with pending status not yet in workflow)
        collection = await get_collection("transactions")
        cursor = collection.find(
            {"approval_status": "pending"},
            {"_id": 0},
        ).sort("date", -1).limit(100)
        db_pending = await cursor.to_list(length=100)

        seen_ids = {p["transaction_id"] for p in in_memory}
        unseen = [t for t in db_pending if t.get("transaction_id", "") not in seen_ids]
        if not unseen:
            return {"pending_approvals": in_memory, "total": len(in_memory)}

        # Batch-fetch employee and department context (avoids 2 queries per txn)
        employees = list({t.get("employee", "") for t in unseen if t.get("employee")})
        departments = list({t.get("department", "") for t in unseen if t.get("department")})

        emp_ctx_map: dict[str, dict] = {}
        dept_ctx_map: dict[str, dict] = {}

        async def _fetch_employees():
            if not employees:
                return
            txns_collection = await get_collection("transactions")
            emp_txns = await txns_collection.find(
                {"employee": {"$in": employees}},
                {"_id": 0, "transaction_id": 1, "amount": 1, "merchant": 1, "date": 1, "employee": 1},
            ).sort("date", -1).to_list(500)
            by_emp: dict[str, list[dict]] = defaultdict(list)
            for t in emp_txns:
                by_emp[t["employee"]].append(t)
            for emp, txns in by_emp.items():
                emp_ctx_map[emp] = {
                    "employee": emp,
                    "total_spent_ytd": round(sum(t.get("amount", 0) for t in txns), 2),
                    "transaction_count": len(txns),
                    "recent_transactions": txns[:5],
                }

        async def _fetch_departments():
            if not departments:
                return
            txns_collection = await get_collection("transactions")
            dept_txns = await txns_collection.find(
                {"department": {"$in": departments}},
                {"_id": 0, "amount": 1, "date": 1, "department": 1},
            ).to_list(1000)
            by_dept: dict[str, list[dict]] = defaultdict(list)
            for t in dept_txns:
                by_dept[t["department"]].append(t)

            # Fetch budgets
            budget_map: dict[str, dict] = {}
            try:
                budget_col = await get_collection("department_budgets")
                budgets = await budget_col.find({"department": {"$in": departments}}, {"_id": 0}).to_list(50)  # type: ignore[arg-type]
                for b in budgets:
                    budget_map[b["department"]] = b
            except Exception:
                pass

            for dept, txns in by_dept.items():
                dept_total = sum(t.get("amount", 0) for t in txns)
                months = len(set(str(t.get("date", ""))[:7] for t in txns if t.get("date")))
                ctx: dict = {
                    "department": dept,
                    "total_spent_ytd": round(dept_total, 2),
                    "monthly_avg_spend": round(dept_total / max(months, 1), 2),
                    "transaction_count": len(txns),
                }
                if dept in budget_map:
                    b = budget_map[dept]
                    ctx["annual_budget"] = b.get("annual_budget")
                    ctx["monthly_budget"] = b.get("monthly_budget")
                    ctx["budget_remaining"] = round(b.get("annual_budget", 0) - dept_total, 2)
                    ctx["budget_used_pct"] = round((dept_total / max(b.get("annual_budget", 1), 1)) * 100, 1)
                dept_ctx_map[dept] = ctx

        await asyncio.gather(_fetch_employees(), _fetch_departments())

        for txn in unseen:
            txn_id = txn.get("transaction_id", "")
            in_memory.append({
                "transaction_id": txn_id,
                "transaction": txn,
                "compliance_results": {
                    "transaction_id": txn_id,
                    "status": "Pending",
                    "severity": "Medium",
                    "recommendation": txn.get("recommendation"),
                    "reasoning": txn.get("reasoning", "Awaiting AI evaluation."),
                },
                "employee_context": emp_ctx_map.get(txn.get("employee", ""), {}),
                "department_context": dept_ctx_map.get(txn.get("department", ""), {}),
                "status": "pending",
            })

        return {"pending_approvals": in_memory, "total": len(in_memory)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
