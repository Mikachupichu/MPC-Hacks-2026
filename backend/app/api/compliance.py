from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import get_collection
from app.graph.nodes.compliance_scanner import evaluate_transactions
from app.schemas.compliance import (
    ComplianceRule,
    ComplianceRuleResponse,
    ComplianceScanRequest,
    ComplianceScanResponse,
)

router = APIRouter()


@router.post("/compliance/scan", response_model=ComplianceScanResponse)
async def compliance_scan(request: ComplianceScanRequest):
    """Feature 2: Scan transactions for policy compliance."""
    try:
        collection = await get_collection("transactions")
        query: dict[str, Any] = {}

        if request.transaction_ids:
            query["transaction_id"] = {"$in": request.transaction_ids}
        if request.department:
            query["department"] = request.department

        cursor = collection.find(query).limit(100)
        transactions = await cursor.to_list(length=100)

        if not transactions:
            return ComplianceScanResponse(results={}, total_scanned=0, violations_found=0)

        # Convert ObjectId to string
        for t in transactions:
            if "_id" in t and isinstance(t["_id"], ObjectId):
                t["_id"] = str(t["_id"])
            if "transaction_id" not in t:
                t["transaction_id"] = str(t.get("_id", ""))

        compliance_results = await evaluate_transactions(transactions)

        violations_found = sum(
            1 for c in compliance_results.values() if c.get("status") == "Violation"
        )

        # Update transactions with compliance results
        for txn in transactions:
            txn_id = txn.get("transaction_id", "")
            if txn_id in compliance_results:
                result = compliance_results[txn_id]
                await collection.update_one(
                    {"transaction_id": txn_id},
                    {
                        "$push": {
                            "compliance_history": {
                                "scanned_at": datetime.now(),
                                "status": result.get("status"),
                                "severity": result.get("severity"),
                                "reasoning": result.get("reasoning"),
                            }
                        }
                    },
                )

        return ComplianceScanResponse(
            results=compliance_results,
            total_scanned=len(transactions),
            violations_found=violations_found,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=ComplianceRuleResponse)
async def create_rule(rule: ComplianceRule):
    """Feature 2: Create a custom spending rule."""
    try:
        collection = await get_collection("custom_rules")
        doc = rule.model_dump()

        # Generate embedding for semantic search
        try:
            from app.graph.nodes.compliance_scanner import _get_embedding

            embed_text = f"{rule.text} {rule.department} {rule.category}"
            embedding = await _get_embedding(embed_text)
            if embedding:
                doc["rule_embedding"] = embedding
        except Exception:
            doc["rule_embedding"] = []

        doc["created_at"] = datetime.now()
        result = await collection.insert_one(doc)

        return ComplianceRuleResponse(
            id=str(result.inserted_id),
            text=rule.text,
            department=rule.department,
            category=rule.category,
            severity=rule.severity,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=list[ComplianceRuleResponse])
async def list_rules():
    """List all custom spending rules."""
    try:
        collection = await get_collection("custom_rules")
        cursor = collection.find({}, {"rule_embedding": 0}).sort("created_at", -1)
        rules = await cursor.to_list(length=100)

        return [
            ComplianceRuleResponse(
                id=str(r["_id"]),
                text=r.get("text", ""),
                department=r.get("department", "all"),
                category=r.get("category", "all"),
                severity=r.get("severity", "Medium"),
            )
            for r in rules
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
