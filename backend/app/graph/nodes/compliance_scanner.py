"""Compliance scanner node — policy evaluation with optional human-in-the-loop approval."""

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

try:
    from langgraph.types import Command
except ImportError:
    Command = None

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
    "recommendation": "Approve" or "Decline",
    "reasoning": "Specific explanation"
  }}
]

IMPORTANT: The "recommendation" field is the AI agent's independent recommendation — set it to "Approve" for Compliant transactions and "Decline" for Violations. Do NOT include the recommendation text inside the reasoning field.
"""


async def _fetch_employee_context(employee: str) -> dict:
    """Fetch employee YTD spend and transaction history."""
    if not employee:
        return {}
    try:
        collection = await get_collection("transactions")
        emp_txns = (
            await collection.find(
                {"employee": employee},
                {"_id": 0, "transaction_id": 1, "amount": 1, "merchant": 1, "date": 1},
            )
            .sort("date", -1)
            .to_list(500)
        )
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
        dept_txns = (
            await txns_col.find(
                {"department": department},
                {"_id": 0, "amount": 1, "date": 1},
            )
            .to_list(1000)
        )
        dept_total = sum(t.get("amount", 0) for t in dept_txns)

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
            dept_ctx["budget_used_pct"] = round(
                (dept_total / max(budget.get("annual_budget", 1), 1)) * 100, 1
            )
        return dept_ctx
    except Exception:
        return {"department": department, "error": "Could not fetch budget data"}


BATCH_SIZE = 20


async def _evaluate_batch(
    batch: list[tuple[dict[str, Any], str]],
    policy_text: str,
) -> list[tuple[str, dict[str, Any]]]:
    """Evaluate a batch of transactions in a single Gemini call."""
    if genai is None:
        return [(t.get("transaction_id", str(t.get("_id", ""))), _default_compliance(t)) for t, _ in batch]

    client = genai.Client(api_key=settings.gemini_api_key)
    txns_json = []
    for txn, rules_str in batch:
        txn_clean = {k: v for k, v in txn.items() if k not in ("_id", "items", "notes", "compliance_history")}
        txn_clean["_matched_rules"] = rules_str[:300]
        txns_json.append(txn_clean)

    prompt = (
        f"{COMPLIANCE_SYSTEM_PROMPT.format(policy_text=policy_text, custom_rules='See _matched_rules per transaction below.')}\n\n"
        f"Evaluate these {len(batch)} transactions:\n"
        f"{json.dumps(txns_json, default=str)}\n\n"
        "Respond with a JSON array of results, one entry per transaction."
    )

    try:
        response = await asyncio.wait_for(
            client.aio.models.generate_content(model=settings.gemini_model, contents=prompt),
            timeout=60,
        )
        parsed = _parse_compliance_array(response.text)
        results = []
        for txn, _ in batch:
            txn_id = txn.get("transaction_id", str(txn.get("_id", "")))
            match = next((p for p in parsed if p.get("transaction_id") == txn_id), None)
            if match:
                results.append((txn_id, match))
            else:
                results.append((txn_id, _default_compliance(txn)))
        return results
    except Exception:
        return [(t.get("transaction_id", str(t.get("_id", ""))), _default_compliance(t)) for t, _ in batch]


async def compliance_scanner_node(state: GraphState) -> dict[str, Any]:
    """Evaluate transactions against policy — may interrupt for human approval.

    When ``task_type`` is ``"approval"`` and violations are found, the node
    pauses the graph via ``Command(interrupt=…)`` so a manager can decide.
    The compliance endpoint (``task_type="compliance"``) never interrupts.
    """
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"compliance_results": {}, "error": "No transactions to evaluate"}

    try:
        policy_doc = await _fetch_policy()
        policy_text = _format_policy_text(policy_doc) if policy_doc else "No policy found."

        async def _get_rules_for_txn(txn: dict) -> str:
            return await _match_rules_by_code(txn)

        rules_tasks = [_get_rules_for_txn(t) for t in transactions]
        rules_results = await asyncio.gather(*rules_tasks)

        # Batch transactions into groups and evaluate each batch in parallel
        pairs = list(zip(transactions, rules_results))
        batches = [pairs[i:i + BATCH_SIZE] for i in range(0, len(pairs), BATCH_SIZE)]
        batch_results = await asyncio.gather(*[_evaluate_batch(b, policy_text) for b in batches], return_exceptions=True)

        compliance_results: dict[str, dict[str, Any]] = {}
        for br in batch_results:
            if isinstance(br, Exception):
                continue
            for txn_id, comp in br:
                compliance_results[str(txn_id)] = comp

        # Post-process: detect repeat offenders by employee
        employee_violations: dict[str, list[str]] = {}
        for txn in transactions:
            emp = txn.get("employee", "")
            txn_id = txn.get("transaction_id", "")
            if emp and compliance_results.get(txn_id, {}).get("status") == "Violation":
                employee_violations.setdefault(emp, []).append(txn_id)

        for emp, txn_ids in employee_violations.items():
            if len(txn_ids) >= 2:
                for idx, txn_id in enumerate(txn_ids, 1):
                    existing = compliance_results[txn_id].get("reasoning", "")
                    compliance_results[txn_id]["reasoning"] = (
                        f"[Repeat offender: {idx}/{len(txn_ids)} "
                        f"violation{'s' if len(txn_ids) != 1 else ''} for {emp}] {existing}"
                    )
                    compliance_results[txn_id]["severity"] = "High"

        output: dict[str, Any] = {"compliance_results": compliance_results}

        # Human-in-the-loop: only when explicitly invoked as an approval flow
        task_type = state.get("task_type", "")
        if task_type == "approval":
            violations = {
                tid: r
                for tid, r in compliance_results.items()
                if r.get("status") == "Violation"
            }
            if violations:
                txn_id, comp_result = next(iter(violations.items()))
                txn = next(
                    t for t in transactions if t.get("transaction_id") == txn_id
                )
                txn_id_label = txn.get("transaction_id", str(txn.get("_id", "unknown")))
                employee_context = await _fetch_employee_context(txn.get("employee", ""))
                dept_context = await _fetch_department_context(txn.get("department", ""))

                if not comp_result.get("recommendation"):
                    comp_result["recommendation"] = (
                        "Decline" if comp_result.get("status") == "Violation" else "Approve"
                    )

                approval_packet = {
                    "transaction_id": txn_id_label,
                    "transaction": txn,
                    "status": "pending",
                    "compliance_results": comp_result,
                    "employee_context": employee_context,
                    "department_context": dept_context,
                }

                # Keep in-memory store so GET /api/approve/pending works
                from app.graph.nodes._pending_store import _pending_approvals

                _pending_approvals[txn_id_label] = approval_packet

                # Update state AND pause for human decision
                output["pending_approval"] = approval_packet
                output["messages"] = list(state.get("messages", [])) + [
                    {
                        "role": "assistant",
                        "content": f"Approval request created for transaction {txn_id_label}. "
                        f"Waiting for manager decision.",
                    }
                ]

                if Command is not None:
                    return Command(
                        update=output,
                        interrupt=approval_packet,
                    )

        return output

    except Exception as e:
        return {"compliance_results": {}, "error": f"Compliance scan failed: {str(e)}"}


async def evaluate_transactions(
    transactions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reusable entry point for compliance evaluation — no interrupt (safe for sub-graph use)."""
    return (
        await compliance_scanner_node(
            {
                "messages": [],
                "current_transactions": transactions,
                "compliance_results": {},
                "report_payload": {},
                "pending_approval": None,
                "user_query": None,
                "conversation_id": None,
                "error": None,
                "task_type": "compliance",
            }
        )
    ).get("compliance_results", {})


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

        if txn_code:
            query["$or"].append({"code": txn_code})
        if txn_dept:
            query["$or"].append({"department": txn_dept})
            query["$or"].append({"department": "all"})
        if txn_type:
            query["$or"].append({"category": txn_type})
            query["$or"].append({"category": "all"})

        if not query["$or"]:
            query = {"$or": [{"department": "all"}]}

        cursor = collection.find(
            query, {"_id": 0, "text": 1, "department": 1, "category": 1, "code": 1, "severity": 1}
        ).limit(10)
        rules = await cursor.to_list(length=10)
        return json.dumps(rules, default=str) if rules else "No matching rules found."
    except Exception:
        return "Rule search unavailable."


def _parse_compliance_array(text: str) -> list[dict]:
    """Parse a JSON array from Gemini's batch evaluation response."""
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            arr = json.loads(json_match.group(1))
            if isinstance(arr, list):
                return arr
        except json.JSONDecodeError:
            pass
    array_match = re.search(r"\[.*?\]", text, re.DOTALL)
    if array_match:
        try:
            arr = json.loads(array_match.group(0))
            if isinstance(arr, list):
                return arr
        except json.JSONDecodeError:
            pass
    return []


def _default_compliance(transaction: dict, error: str = "") -> dict:
    txn_id = transaction.get("transaction_id", str(transaction.get("_id", "unknown")))
    result = {
        "transaction_id": str(txn_id),
        "status": "Compliant",
        "severity": "Low",
        "recommendation": "Approve",
        "reasoning": "Unable to evaluate with AI - manual review recommended.",
    }
    if error:
        result["recommendation"] = "Approve"
        result["reasoning"] = f"Evaluation error: {error}"
    return result
