from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import get_collection
from app.graph.nodes.report_compiler import report_compiler_node
from app.graph.state import GraphState
from app.schemas.report import ReportRequest, ReportResponse

router = APIRouter()


@router.post("/reports/compile", response_model=ReportResponse)
async def compile_report(request: ReportRequest):
    """Feature 4: Compile an automated expense report from transactions."""
    try:
        collection = await get_collection("transactions")
        query = {}

        if request.transaction_ids:
            query["transaction_id"] = {"$in": request.transaction_ids}
        if request.department:
            query["department"] = request.department
        if request.date_from or request.date_to:
            date_query = {}
            if request.date_from:
                date_query["$gte"] = request.date_from
            if request.date_to:
                date_query["$lte"] = request.date_to
            if date_query:
                query["date"] = date_query

        cursor = collection.find(query).sort("date", -1).limit(500)
        transactions = await cursor.to_list(length=500)

        if not transactions:
            return ReportResponse(report_payload={}, error="No transactions found matching criteria")

        # Convert ObjectId to string
        for t in transactions:
            if "_id" in t and isinstance(t["_id"], ObjectId):
                t["_id"] = str(t["_id"])
            if "transaction_id" not in t:
                t["transaction_id"] = str(t.get("_id", ""))

        state = GraphState(
            messages=[],
            current_transactions=transactions,
            compliance_results={},
            report_payload={},
            pending_approval=None,
            user_query="report",
            error=None,
        )

        result = await report_compiler_node(state)

        return ReportResponse(
            report_payload=result.get("report_payload", {}),
            compliance_results=result.get("compliance_results", {}),
            error=result.get("error"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
