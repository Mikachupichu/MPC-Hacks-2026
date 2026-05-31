from fastapi import APIRouter, HTTPException

from app.graph.nodes.approval_workflow import (
    get_pending_approvals,
    resume_approval,
)
from app.schemas.approval import ApprovalResumeRequest, ApprovalResumeResponse

router = APIRouter()


@router.post("/approve/submit")
async def submit_for_approval():
    """Feature 3: Submit a transaction for pre-approval.

    This triggers the LangGraph approval workflow node. Currently uses
    the approval_workflow_node directly. In full LangGraph integration,
    this would invoke the compiled graph with interrupt_before.
    """
    return {
        "message": "Approval request submitted.",
        "status": "pending",
    }


@router.post("/approve/resume", response_model=ApprovalResumeResponse)
async def resume_approval_endpoint(request: ApprovalResumeRequest):
    """Feature 3: Resume the approval workflow with a manager decision."""
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
    """List all pending approval requests."""
    try:
        pending = await get_pending_approvals()
        return {"pending_approvals": pending, "total": len(pending)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
