from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_collection
from app.mappings import resolve_department, resolve_transaction_type
from app.schemas.transactions import CreateTransactionRequest

router = APIRouter()


@router.get("/transactions")
async def list_transactions(
    department: str | None = None,
    transaction_type: str | None = None,
    transaction_code: int | None = None,
    status: str | None = None,
    debit_or_credit: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
):
    """List transactions with optional filtering."""
    try:
        collection = await get_collection("transactions")
        query = {}

        if department:
            query["department"] = department
        if transaction_type:
            query["transaction_type"] = transaction_type
        if transaction_code:
            query["transaction_code"] = transaction_code
        if status:
            query["approval_status"] = status
        if debit_or_credit:
            query["debit_or_credit"] = debit_or_credit
        if search:
            query["$or"] = [
                {"transaction_id": {"$regex": search, "$options": "i"}},
                {"merchant": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]

        total = await collection.count_documents(query)
        cursor = collection.find(query, {"_id": 0}).sort("date", -1).skip(offset).limit(limit)
        transactions = await cursor.to_list(length=limit)

        return {
            "transactions": transactions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions")
async def create_transaction(request: CreateTransactionRequest):
    """Create a new transaction with auto-mapped code/department/type fields."""
    try:
        collection = await get_collection("transactions")
        code = request.transaction_code

        # Auto-resolve department and transaction type from code and category
        department = resolve_department(code)
        transaction_type = resolve_transaction_type(request.transaction_category, request.merchant_category_code)

        doc = request.model_dump()
        doc["department"] = department
        doc["transaction_type"] = transaction_type
        doc["tags"] = _derive_tags(transaction_type, request.amount)
        doc["compliance_history"] = []
        doc["payment_method"] = "corporate_card"
        doc["is_reimbursable"] = False
        doc["items"] = request.items or []
        doc["notes"] = []

        # Evaluate against custom rules and policy before setting approval
        matching_rules = await _fetch_matching_rules(department, transaction_type, request.amount)
        policy_violation = await _check_policy_violation(transaction_type, request.amount, request.merchant)

        if request.amount < 50:
            doc["approval_status"] = "not_required"
            doc["recommendation"] = None
            doc["reasoning"] = None
        else:
            doc["approval_status"] = "pending"
            if policy_violation:
                doc["recommendation"] = "Decline"
                doc["reasoning"] = policy_violation
            elif matching_rules:
                rule = matching_rules[0]
                if rule.get("severity") == "High" and request.amount > 500:
                    doc["recommendation"] = "Decline"
                    doc["reasoning"] = (
                        f"Flagged by high-severity rule: {rule['text']}. "
                        f"Transaction of ${request.amount:,.2f} at {request.merchant} requires review."
                    )
                else:
                    doc["recommendation"] = "Approve"
                    doc["reasoning"] = (
                        f"Transaction of ${request.amount:,.2f} at {request.merchant} "
                        f"for {department}/{transaction_type} passes policy and custom rule checks."
                    )
            elif request.amount > 2000:
                doc["recommendation"] = "Approve"
                doc["reasoning"] = (
                    f"Transaction amount of ${request.amount:,.2f} at {request.merchant} "
                    f"exceeds the $2,000 automatic approval threshold. Awaiting finance team review."
                )
            else:
                doc["recommendation"] = "Approve"
                doc["reasoning"] = (
                    f"Transaction of ${request.amount:,.2f} at {request.merchant} "
                    f"for {department}/{transaction_type} is within policy limits. Auto-approved."
                )

        # If no employee provided, assign one based on department
        if not doc.get("employee"):
            ops_emps = [
                "Marcus Johnson", "Sarah Chen", "David Rodriguez", "Emily Thompson",
                "James Wilson", "Maria Garcia", "Robert Kim",
            ]
            fin_emps = ["Rachel Green", "Thomas Wright", "Nancy Baker"]
            pool = fin_emps if code in (108, 137, 375, 401, 404) else ops_emps
            doc["employee"] = pool[hash(str(request.merchant)) % len(pool)]

        await collection.insert_one(doc)

        # Remove ObjectId for JSON serialization
        doc.pop("_id", None)

        return {
            "message": "Transaction created",
            "transaction": doc,
            "auto_mapped": {
                "department": department,
                "transaction_type": transaction_type,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _derive_tags(transaction_type: str, amount: float) -> list[str]:
    tags = []
    if transaction_type == "Fuel":
        tags.append("fuel")
    if amount > 1000:
        tags.append("high-value")
    return tags


async def _fetch_matching_rules(
    department: str,
    transaction_type: str,
    amount: float,
) -> list[dict]:
    """Fetch custom rules that apply to this transaction."""
    try:
        collection = await get_collection("custom_rules")
        query = {"$or": [
            {"department": "all"},
            {"department": department},
        ]}
        cursor = collection.find(query, {"_id": 0, "text": 1, "severity": 1, "code": 1, "department": 1, "category": 1})
        rules = await cursor.to_list(length=50)
        # Filter by category match
        matching = []
        for r in rules:
            cat = r.get("category", "all")
            if cat == "all" or cat == transaction_type:
                matching.append(r)
        return matching
    except Exception:
        return []


async def _check_policy_violation(
    transaction_type: str,
    amount: float,
    merchant: str,
) -> str | None:
    """Check against baseline policy rules and return violation text if any."""
    # Policy: expenses over $50 need pre-authorization and receipts
    # Policy: tips above 20% not allowed
    # Policy: alcoholic beverages not permitted unless dining with customer
    # Policy: no traffic or parking tickets reimbursed
    try:
        collection = await get_collection("company_policies")
        # Not doing LLM calls here — quick deterministic checks
        if transaction_type == "Cash Advance" and amount > 500:
            return "Cash advance exceeds $500 per-trip limit without pre-approval per company policy."
        if amount > 10000:
            return "Any single transaction over $10,000 requires CFO approval per company policy."
    except Exception:
        pass
    return None


@router.get("/transactions/types")
async def list_transaction_types():
    """List all distinct transaction types with stats."""
    try:
        collection = await get_collection("transactions")
        pipeline = [
            {
                "$group": {
                    "_id": "$transaction_type",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$amount"},
                    "min_amount": {"$min": "$amount"},
                    "max_amount": {"$max": "$amount"},
                    "avg_amount": {"$avg": "$amount"},
                }
            },
            {"$sort": {"total": -1}},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=50)
        return {
            "types": [
                {
                    "name": r["_id"],
                    "count": r["count"],
                    "total": round(r["total"], 2),
                    "min_amount": round(r["min_amount"], 2),
                    "max_amount": round(r["max_amount"], 2),
                    "avg_amount": round(r["avg_amount"], 2),
                }
                for r in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/departments")
async def list_departments():
    """List all departments with aggregated stats."""
    try:
        collection = await get_collection("transactions")
        pipeline = [
            {
                "$group": {
                    "_id": "$department",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$amount"},
                    "avg": {"$avg": "$amount"},
                }
            },
            {"$sort": {"total": -1}},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=50)
        return {
            "departments": [
                {
                    "name": r["_id"],
                    "count": r["count"],
                    "total": round(r["total"], 2),
                    "avg": round(r["avg"], 2),
                }
                for r in results
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions/codes")
async def list_transaction_codes():
    """List all transaction codes with stats."""
    try:
        from app.mappings import ALL_CODES, CODE_TO_DEPT

        collection = await get_collection("transactions")
        pipeline = [
            {
                "$group": {
                    "_id": "$transaction_code",
                    "count": {"$sum": 1},
                    "total": {"$sum": "$amount"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=50)

        codes = []
        for r in results:
            code_val = r["_id"]
            dept = CODE_TO_DEPT.get(code_val, "Unknown")
            codes.append({
                "code": code_val,
                "department": dept,
                "count": r["count"],
                "total": round(r["total"], 2),
            })

        return {"codes": codes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
