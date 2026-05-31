import asyncio
import json
import re
from typing import Any

from app.core.config import settings
from app.core.database import get_collection
from app.graph.state import GraphState

try:
    from google import genai
except ImportError:
    genai = None


COMPLIANCE_SYSTEM_PROMPT = """You are an AI compliance officer for SMB expense management. Evaluate transactions against company policy and flag violations with contextual reasoning.

Company Policy Document:
{policy_text}

Relevant Custom Rules:
{custom_rules}

For each transaction, evaluate with contextual reasoning:
- Consider the merchant type, amount, department, and transaction type
- A $200 multi-item fuel stop for a fleet is reasonable; an outsized single fuel transaction may indicate personal use
- Repeat patterns matter — flag habitual overspending
- Consider each department's typical spend profile
- WATCH FOR SPLIT TRANSACTIONS: If multiple transactions from the same merchant or similar amounts appear close together that collectively exceed a threshold, flag them as potential split-purchases designed to dodge approval limits
- FLAG REPEAT OFFENDERS: If an employee has multiple violations, note the repeat pattern in the reasoning (e.g. "Third policy violation from this employee this period")

Respond with a JSON array:
[
  {{
    "transaction_id": "str",
    "status": "Compliant" or "Violation",
    "severity": "Low" or "Medium" or "High",
    "reasoning": "Specific explanation"
  }}
]
"""


async def compliance_scanner_node(state: GraphState) -> dict[str, Any]:
    """Centralized evaluation engine using code/department-based rule matching."""
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"compliance_results": {}, "error": "No transactions to evaluate"}

    try:
        policy_doc = await _fetch_policy()
        policy_text = _format_policy_text(policy_doc) if policy_doc else "No policy found."

        # Match rules by code and department instead of vector search
        async def _get_rules_for_txn(txn: dict) -> str:
            return await _match_rules_by_code(txn)

        rules_tasks = [_get_rules_for_txn(t) for t in transactions]
        rules_results = await asyncio.gather(*rules_tasks)

        async def _evaluate(txn: dict, rules_str: str) -> dict:
            return await _evaluate_single(txn, policy_text, rules_str)

        eval_tasks = [_evaluate(t, r) for t, r in zip(transactions, rules_results)]
        eval_results = await asyncio.gather(*eval_tasks)

        compliance_results: dict[str, dict[str, Any]] = {}
        for txn, result in zip(transactions, eval_results):
            txn_id = txn.get("transaction_id", txn.get("_id", str(txn)))
            compliance_results[str(txn_id)] = result

        # Post-process: detect repeat offenders by employee
        employee_violations: dict[str, list[str]] = {}
        for txn in transactions:
            emp = txn.get("employee", "")
            txn_id = txn.get("transaction_id", "")
            if emp and compliance_results.get(txn_id, {}).get("status") == "Violation":
                employee_violations.setdefault(emp, []).append(txn_id)

        for emp, txn_ids in employee_violations.items():
            if len(txn_ids) >= 2:
                for txn_id in txn_ids:
                    result = compliance_results.get(txn_id, {})
                    repeat_count = txn_ids.index(txn_id) + 1
                    existing = result.get("reasoning", "")
                    result["reasoning"] = f"[Repeat offender: {repeat_count}/{len(txn_ids)} violation{'' if len(txn_ids) == 1 else 's'} for {emp}] {existing}"
                    result["severity"] = "High"
                    compliance_results[txn_id] = result

        return {"compliance_results": compliance_results}

    except Exception as e:
        return {"compliance_results": {}, "error": f"Compliance scan failed: {str(e)}"}


async def evaluate_transactions(
    transactions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reusable entry point for compliance evaluation from other nodes."""
    return (await compliance_scanner_node({
        "messages": [],
        "current_transactions": transactions,
        "compliance_results": {},
        "report_payload": {},
        "pending_approval": None,
        "user_query": None,
        "conversation_id": None,
        "error": None,
    })).get("compliance_results", {})


async def _fetch_policy() -> dict | None:
    try:
        collection = await get_collection("company_policies")
        pipeline = [{"$sample": {"size": 1}}, {"$project": {"_id": 0}}]
        cursor = collection.aggregate(pipeline)
        docs = await cursor.to_list(length=1)
        return docs[0] if docs else None
    except Exception:
        return None


def _format_policy_text(policy: dict) -> str:
    sections = []
    for key, value in policy.items():
        if isinstance(value, str) and value.strip():
            sections.append(f"## {key.replace('_', ' ').title()}\n{value}")
    return "\n\n".join(sections)


async def _match_rules_by_code(transaction: dict) -> str:
    """Match custom rules using transaction_code and department instead of vector search."""
    try:
        collection = await get_collection("custom_rules")
        txn_code = transaction.get("transaction_code")
        txn_dept = transaction.get("department", "")
        txn_type = transaction.get("transaction_type", "")

        query: dict[str, Any] = {"$or": []}

        # Match by transaction code (most specific)
        if txn_code:
            query["$or"].append({"code": txn_code})

        # Match by department
        if txn_dept:
            query["$or"].append({"department": txn_dept})
            query["$or"].append({"department": "all"})

        # Match by category/type
        if txn_type:
            query["$or"].append({"category": txn_type})
            query["$or"].append({"category": "all"})

        if not query["$or"]:
            query = {"$or": [{"department": "all"}]}

        cursor = collection.find(query, {"_id": 0, "text": 1, "department": 1, "category": 1, "code": 1, "severity": 1}).limit(10)
        rules = await cursor.to_list(length=10)
        return json.dumps(rules, default=str) if rules else "No matching rules found."
    except Exception:
        return "Rule search unavailable."


async def _evaluate_single(
    transaction: dict,
    policy_text: str,
    custom_rules: str,
) -> dict:
    """Evaluate a single transaction through Gemini."""
    try:
        if genai is None:
            return _default_compliance(transaction)

        client = genai.Client(api_key=settings.gemini_api_key)

        txn_str = json.dumps(
            {k: v for k, v in transaction.items() if k not in ("_id", "items", "notes", "compliance_history")},
            default=str,
        )

        prompt = (
            f"{COMPLIANCE_SYSTEM_PROMPT.format(policy_text=policy_text, custom_rules=custom_rules)}\n\n"
            f"Evaluate this single transaction:\n{txn_str}\n\n"
            "Respond with the JSON object for this transaction only, not an array."
        )

        response = client.models.generate_content(
            model=settings.gemini_model, contents=prompt
        )

        return _parse_compliance_json(response.text, transaction)

    except Exception as e:
        return _default_compliance(transaction, error=str(e))


def _parse_compliance_json(text: str, transaction: dict) -> dict:
    json_match = re.search(r"\[.*?\]", text, re.DOTALL)
    if json_match:
        try:
            arr = json.loads(json_match.group(0))
            if arr and isinstance(arr, list):
                return arr[0]
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return _default_compliance(transaction)


def _default_compliance(transaction: dict, error: str = "") -> dict:
    txn_id = transaction.get("transaction_id", str(transaction.get("_id", "unknown")))
    result = {
        "transaction_id": str(txn_id),
        "status": "Compliant",
        "severity": "Low",
        "reasoning": "Unable to evaluate with AI - manual review recommended.",
    }
    if error:
        result["reasoning"] = f"Evaluation error: {error}"
    return result
