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

        # Merge — prefer in-memory versions for those already in workflow
        from app.graph.nodes.approval_workflow import _fetch_employee_context, _fetch_department_context
        seen_ids = {p["transaction_id"] for p in in_memory}
        for txn in db_pending:
            txn_id = txn.get("transaction_id", "")
            if txn_id not in seen_ids:
                employee_ctx = await _fetch_employee_context(txn.get("employee", ""))
                dept_ctx = await _fetch_department_context(txn.get("department", ""))
                in_memory.append({
                    "transaction_id": txn_id,
                    "transaction": txn,
                    "compliance_results": {
                        "transaction_id": txn_id,
                        "status": "Pending",
                        "severity": "Medium",
                        "reasoning": txn.get("reasoning", "Awaiting AI evaluation."),
                    },
                    "employee_context": employee_ctx,
                    "department_context": dept_ctx,
                    "status": "pending",
                })

        return {"pending_approvals": in_memory, "total": len(in_memory)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
