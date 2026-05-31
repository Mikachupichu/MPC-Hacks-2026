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


COMPLIANCE_SYSTEM_PROMPT = """You are an AI compliance officer for SMB expense management. Your job is to evaluate transactions against company policy and flag violations with human-like contextual reasoning.

Company Policy Document:
{policy_text}

Relevant Custom Rules:
{custom_rules}

For each transaction, evaluate with contextual reasoning:
- Consider the merchant type, amount, category, and employee context
- A $200 team dinner for 5 people is reasonable; a $200 solo dinner at a high-end restaurant may not be
- Repeat patterns matter - flag habitual overspending
- Consider department budgets and typical spending patterns

Respond with a JSON array of objects, one per transaction:
[
  {{
    "transaction_id": "str",
    "status": "Compliant" or "Violation",
    "severity": "Low" or "Medium" or "High",
    "reasoning": "Specific explanation of why this passes or violates policy",
    "policy_sections_violated": ["section1", "section2"]
  }}
]

Be thorough but fair. Not every large expense is a violation - consider context.
"""


async def compliance_scanner_node(state: GraphState) -> dict[str, Any]:
    """Centralized evaluation engine that processes transactions in parallel."""
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"compliance_results": {}, "error": "No transactions to evaluate"}

    try:
        # 1. Fetch baseline policy
        policy_doc = await _fetch_policy()
        policy_text = _format_policy_text(policy_doc) if policy_doc else "No policy found."

        # 2. For each transaction, vector search custom rules
        async def _get_rules_for_txn(txn: dict) -> str:
            return await _semantic_rule_search(txn)

        rules_tasks = [_get_rules_for_txn(t) for t in transactions]
        rules_results = await asyncio.gather(*rules_tasks)

        # 3. Evaluate all transactions in parallel through Gemini
        async def _evaluate(txn: dict, rules_str: str) -> dict:
            return await _evaluate_single(txn, policy_text, rules_str)

        eval_tasks = [_evaluate(t, r) for t, r in zip(transactions, rules_results)]
        eval_results = await asyncio.gather(*eval_tasks)

        # Build results dict
        compliance_results: dict[str, dict[str, Any]] = {}
        for txn, result in zip(transactions, eval_results):
            txn_id = txn.get("transaction_id", txn.get("_id", str(txn)))
            compliance_results[str(txn_id)] = result

        return {"compliance_results": compliance_results}

    except Exception as e:
        return {"compliance_results": {}, "error": f"Compliance scan failed: {str(e)}"}


async def evaluate_transactions(
    transactions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Reusable entry point for compliance evaluation from other nodes."""
    state = GraphState(
        messages=[],
        current_transactions=transactions,
        compliance_results={},
        report_payload={},
        pending_approval=None,
        user_query=None,
        error=None,
    )
    result = await compliance_scanner_node(state)
    return result.get("compliance_results", {})


async def _fetch_policy() -> dict | None:
    try:
        collection = await get_collection("company_policies")
        policy = await collection.find_one({}, {"_id": 0})
        return policy
    except Exception:
        return None


def _format_policy_text(policy: dict) -> str:
    sections = []
    for key, value in policy.items():
        if isinstance(value, str) and value.strip():
            sections.append(f"## {key.replace('_', ' ').title()}\n{value}")
    return "\n\n".join(sections)


async def _semantic_rule_search(transaction: dict) -> str:
    """Search for semantically relevant custom rules."""
    try:
        collection = await get_collection("custom_rules")

        # Build text to vectorize from transaction metadata
        search_text = f"{transaction.get('merchant', '')} {transaction.get('category', '')} {transaction.get('department', '')} {transaction.get('description', '')} {transaction.get('amount', 0)}"

        text_embedding = await _get_embedding(search_text)

        if text_embedding:
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "custom_rules_vector_index",
                        "path": "rule_embedding",
                        "queryVector": text_embedding,
                        "numCandidates": 10,
                        "limit": 5,
                    }
                },
                {"$project": {"_id": 0, "text": 1, "department": 1, "category": 1}},
            ]
            cursor = collection.aggregate(pipeline)
            rules = await cursor.to_list(length=5)
            if rules:
                return json.dumps(rules, default=str)

        # Fallback: return recent rules
        fallback = collection.find({}, {"_id": 0, "text": 1, "department": 1, "category": 1}).limit(3)
        fallback_rules = await fallback.to_list(length=3)
        return json.dumps(fallback_rules, default=str) if fallback_rules else "No custom rules found."
    except Exception:
        return "Rule search unavailable."


async def _get_embedding(text: str) -> list[float] | None:
    """Generate embedding using Gemini."""
    try:
        if genai is None:
            return None
        client = genai.Client(api_key=settings.gemini_api_key)
        result = client.models.embed_content(
            model="models/text-embedding-004", contents=text
        )
        return result.embeddings[0].values if result.embeddings else None
    except Exception:
        return None


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
            {k: v for k, v in transaction.items() if k != "_id"},
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
    """Robust parser for compliance LLM output."""
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
