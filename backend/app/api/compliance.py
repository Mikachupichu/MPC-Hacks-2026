import asyncio
import json
import re
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.database import get_collection
from app.core.time_range import get_app_cutoff_date
from app.graph.nodes.compliance_scanner import evaluate_transactions
from app.schemas.compliance import (
    ComplianceRule,
    ComplianceRuleResponse,
    ComplianceScanRequest,
    ComplianceScanResponse,
)

try:
    from google import genai
except ImportError:
    genai = None

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

        # Apply app-wide time range filter
        cutoff = await get_app_cutoff_date()
        query["date"] = {"$gte": cutoff}

        cursor = collection.find(query).limit(100)
        transactions = await cursor.to_list(length=100)

        if not transactions:
            return ComplianceScanResponse(results={}, total_scanned=0, violations_found=0)

        for t in transactions:
            if "_id" in t and isinstance(t["_id"], ObjectId):
                t["_id"] = str(t["_id"])
            if "transaction_id" not in t:
                t["transaction_id"] = str(t.get("_id", ""))

        compliance_results = await evaluate_transactions(transactions)

        violations_found = sum(
            1 for c in compliance_results.values() if c.get("status") == "Violation"
        )

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
    """Create a custom spending rule and re-evaluate matching transactions."""
    try:
        collection = await get_collection("custom_rules")
        doc = rule.model_dump()
        doc["created_at"] = datetime.now()

        if doc.get("code") is None and doc.get("department"):
            from app.mappings import resolve_first_code
            doc["code"] = resolve_first_code(doc["department"])

        result = await collection.insert_one(doc)
        rule_id = str(result.inserted_id)

        # Fire-and-forget: re-evaluate matching transactions in the background
        asyncio.create_task(
            _reevaluate_matching_transactions(doc["text"], doc.get("department", "all"), doc.get("category", "all"))
        )

        return ComplianceRuleResponse(
            id=rule_id,
            text=rule.text,
            code=doc.get("code"),
            department=rule.department,
            category=rule.category,
            severity=rule.severity,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=list[ComplianceRuleResponse])
async def list_rules():
    """List all spending rules — baseline policies first, then custom rules."""
    try:
        result: list[ComplianceRuleResponse] = []

        # 1. Fetch baseline company policies
        policies_collection = await get_collection("company_policies")
        policies = await policies_collection.find({}, {"_id": 0}).to_list(length=50)
        for p in policies:
            result.append(
                ComplianceRuleResponse(
                    id=p.get("type", "policy"),
                    text=p.get("text", ""),
                    code=p.get("code"),
                    department=p.get("department", "all"),
                    category=p.get("category", "all"),
                    severity=p.get("severity", "Medium"),
                    source="baseline",
                )
            )

        # 2. Fetch custom rules (from UI)
        custom_collection = await get_collection("custom_rules")
        custom_rules = await custom_collection.find({}).sort("created_at", -1).to_list(length=100)
        for r in custom_rules:
            result.append(
                ComplianceRuleResponse(
                    id=str(r["_id"]),
                    text=r.get("text", ""),
                    code=r.get("code"),
                    department=r.get("department", "all"),
                    category=r.get("category", "all"),
                    severity=r.get("severity", "Medium"),
                    source="custom",
                )
            )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _reevaluate_matching_transactions(rule_text: str, department: str, category: str):
    """Re-evaluate transactions that match this rule's department and category.

    Only transactions within the app-wide time range are re-evaluated.
    """
    try:
        collection = await get_collection("transactions")

        # Build query for matching transactions
        query: dict[str, Any] = {"approval_status": {"$ne": "not_required"}}
        dept_list = [department] if department != "all" else None
        cat_list = [category] if category != "all" else None

        if dept_list:
            query["department"] = {"$in": dept_list}
        if cat_list:
            query["transaction_type"] = {"$in": cat_list}

        # Apply app-wide time range filter — transactions outside the window are frozen
        cutoff = await get_app_cutoff_date()
        query["date"] = {"$gte": cutoff}

        cursor = collection.find(query).limit(200)
        transactions = await cursor.to_list(length=200)

        if not transactions:
            return

        for t in transactions:
            t["_id"] = str(t["_id"])
            if "transaction_id" not in t:
                t["transaction_id"] = str(t.get("_id", ""))

        # Evaluate each transaction against the new rule via Gemini
        results = await _evaluate_against_rule(transactions, rule_text)

        for txn in transactions:
            txn_id = txn.get("transaction_id", "")
            eval_result = results.get(txn_id)
            if not eval_result or eval_result.get("status") != "Violation":
                continue

            current_status = txn.get("approval_status", "")
            new_reasoning = eval_result.get("reasoning", "")

            if current_status == "approved":
                await collection.update_one(
                    {"transaction_id": txn_id},
                    {
                        "$set": {
                            "approval_status": "pending",
                            "recommendation": "Decline",
                            "reasoning": new_reasoning,
                        },
                        "$push": {
                            "compliance_history": {
                                "scanned_at": datetime.now(),
                                "status": "Re-evaluated",
                                "severity": eval_result.get("severity", "Medium"),
                                "reasoning": f"New rule triggered: {rule_text}. {new_reasoning}",
                            }
                        },
                    },
                )
            elif current_status == "denied":
                existing = txn.get("reasoning", "")
                existing_rec = txn.get("recommendation", "Decline")
                update_reasoning = f"{existing} | Additional violation: {rule_text}. {new_reasoning}"
                await collection.update_one(
                    {"transaction_id": txn_id},
                    {
                        "$set": {"reasoning": update_reasoning, "recommendation": existing_rec},
                        "$push": {
                            "compliance_history": {
                                "scanned_at": datetime.now(),
                                "status": "Re-evaluated",
                                "severity": eval_result.get("severity", "Medium"),
                                "reasoning": f"New rule triggered: {rule_text}. {new_reasoning}",
                            }
                        },
                    },
                )
            elif current_status == "pending":
                await collection.update_one(
                    {"transaction_id": txn_id},
                    {
                        "$set": {"reasoning": new_reasoning, "recommendation": "Decline"},
                        "$push": {
                            "compliance_history": {
                                "scanned_at": datetime.now(),
                                "status": "Re-evaluated",
                                "severity": eval_result.get("severity", "Medium"),
                                "reasoning": f"Re-evaluated against new rule: {rule_text}. {new_reasoning}",
                            }
                        },
                    },
                )

    except Exception:
        pass  # Background task — don't crash the API response


async def _evaluate_against_rule(
    transactions: list[dict],
    rule_text: str,
) -> dict[str, dict[str, Any]]:
    """Use Gemini to batch-check if transactions violate the new rule."""
    if genai is None or not transactions:
        return {}

    try:
        client = genai.Client(api_key=settings.gemini_api_key)

        # Batch transactions — send up to 30 per call
        BATCH_SIZE = 30
        results: dict[str, dict[str, Any]] = {}

        for i in range(0, len(transactions), BATCH_SIZE):
            batch = transactions[i:i + BATCH_SIZE]
            batch_json = []
            for txn in batch:
                batch_json.append({
                    "transaction_id": txn.get("transaction_id", ""),
                    "merchant": txn.get("merchant", ""),
                    "amount": txn.get("amount", 0),
                    "department": txn.get("department", ""),
                    "transaction_type": txn.get("transaction_type", ""),
                    "date": str(txn.get("date", "")),
                    "current_status": txn.get("approval_status", ""),
                })

            prompt = (
                f"You are evaluating transactions against a new company policy rule.\n\n"
                f"New Rule: \"{rule_text}\"\n\n"
                f"For each transaction, determine if it VIOLATES this new rule.\n"
                f"Be strict — if the transaction clearly violates the rule, flag it.\n\n"
                f"Respond with a JSON array of only the violations:\n"
                f"[{{\"transaction_id\":\"...\", \"status\":\"Violation\", \"severity\":\"Low\"|\"Medium\"|\"High\", "
                f"\"recommendation\":\"Decline\", "
                f"\"reasoning\":\"<explanation>\"}}]\n\n"
                f"Return an empty array [] if none violate.\n\n"
                f"Transactions:\n{json.dumps(batch_json, default=str)}"
            )

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
            )
            parsed = _parse_violation_array(response.text)
            for p in parsed:
                results[p["transaction_id"]] = p

        return results

    except Exception:
        return {}


def _parse_violation_array(text: str) -> list[dict]:
    """Parse Gemini response for a batch transaction evaluation."""
    array_match = re.search(r"\[.*?\]", text, re.DOTALL)
    if array_match:
        try:
            arr = json.loads(array_match.group(0))
            if isinstance(arr, list):
                return [a for a in arr if isinstance(a, dict) and a.get("status") == "Violation"]
        except json.JSONDecodeError:
            pass
    return []


def _parse_violation_json(text: str, expected_id: str) -> dict | None:
    """Parse Gemini response for a single transaction evaluation."""
    array_match = re.search(r"\[.*?\]", text, re.DOTALL)
    if array_match:
        try:
            arr = json.loads(array_match.group(0))
            if arr and isinstance(arr, list):
                return arr[0]
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            obj = json.loads(brace_match.group(0))
            if isinstance(obj, dict) and obj.get("status") == "Violation":
                return obj
        except json.JSONDecodeError:
            pass
    return None
