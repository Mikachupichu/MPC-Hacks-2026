import json
import re
from collections import Counter
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.time_range import get_app_cutoff_date
from app.graph.state import GraphState

try:
    from google import genai
except ImportError:
    genai = None


async def report_compiler_node(state: GraphState) -> dict[str, Any]:
    """Compiles multi-transaction expense logs into a single summary report.

    Uses existing approval_status from the database instead of re-scanning
    every transaction. Skips the LLM for large batches to avoid timeouts.
    """
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {"report_payload": {}, "error": "No transactions provided."}

    try:
        # Build compliance results from existing DB fields
        compliance_results: dict[str, dict[str, Any]] = {}
        for txn in transactions:
            txn_id = txn.get("transaction_id", str(txn.get("_id", "")))
            status = txn.get("approval_status", "approved")
            reasoning = txn.get("reasoning")
            is_violation = status == "denied"
            compliance_results[txn_id] = {
                "transaction_id": txn_id,
                "status": "Violation" if is_violation else "Compliant",
                "severity": "High" if is_violation else "Low",
                "recommendation": txn.get("recommendation"),
                "reasoning": reasoning or "",
            }

        # Double-check a sample of approved and denied transactions against policy
        # Only include transactions within the app-wide time range — older ones are frozen
        cutoff = await get_app_cutoff_date()
        audit_candidates = [t for t in transactions if str(t.get("date", "")) >= cutoff]
        approved_sample = [t for t in audit_candidates if t.get("approval_status") == "approved"][:10]
        denied_sample = [t for t in audit_candidates if t.get("approval_status") == "denied"][:10]
        audit_sample = (approved_sample + denied_sample)[:10]
        if audit_sample:
            from app.core.database import get_collection
            audit_results = await _audit_transactions(audit_sample)
            for txn_id, result in audit_results.items():
                if txn_id in compliance_results:
                    compliance_results[txn_id] = result
                    for txn in audit_sample:
                        if txn.get("transaction_id") == txn_id:
                            old_status = txn.get("approval_status", "")
                            new_rec = result.get("recommendation")
                            new_reasoning = result.get("reasoning", "")
                            if new_rec and new_rec != "Approve" and old_status == "approved":
                                # AI changed its mind — flip to pending
                                collection = await get_collection("transactions")
                                await collection.update_one(
                                    {"transaction_id": txn_id},
                                    {"$set": {"approval_status": "pending", "recommendation": new_rec, "reasoning": new_reasoning},
                                     "$push": {"compliance_history": {"scanned_at": datetime.now(), "status": "Re-evaluated", "severity": "High", "reasoning": f"Audit: previously approved but now recommends {new_rec}."}}}
                                )
                            elif new_rec and new_rec != "Decline" and old_status == "denied":
                                collection = await get_collection("transactions")
                                await collection.update_one(
                                    {"transaction_id": txn_id},
                                    {"$set": {"approval_status": "pending", "recommendation": new_rec, "reasoning": new_reasoning},
                                     "$push": {"compliance_history": {"scanned_at": datetime.now(), "status": "Re-evaluated", "severity": "High", "reasoning": f"Audit: previously denied but now recommends {new_rec}."}}}
                                )
                            break

        # Build report from data (fast aggregation path for any batch size)
        report_payload = _build_aggregated_report(transactions, compliance_results)

        # Extract pending approvals
        pending_approvals = [
            {
                "transaction_id": t.get("transaction_id", ""),
                "merchant": t.get("merchant", ""),
                "amount": t.get("amount", 0),
                "department": t.get("department", ""),
                "transaction_type": t.get("transaction_type", ""),
                "date": str(t.get("date", "")),
                "recommendation": t.get("recommendation"),
                "reasoning": t.get("reasoning", ""),
            }
            for t in transactions
            if t.get("approval_status") == "pending"
        ]
        report_payload["pending_approvals"] = pending_approvals

        return {
            "report_payload": report_payload,
            "compliance_results": compliance_results,
        }

    except Exception as e:
        return {"report_payload": {}, "error": f"Report compilation failed: {str(e)}"}


async def _generate_report(
    transactions: list[dict[str, Any]],
    compliance_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Try LLM report generation for small batches, fall back to aggregation."""
    try:
        if genai is None:
            return _build_aggregated_report(transactions, compliance_results)

        client = genai.Client(api_key=settings.gemini_api_key)

        txn_summary = [
            {
                "merchant": t.get("merchant", ""),
                "amount": t.get("amount", 0),
                "department": t.get("department", ""),
                "transaction_type": t.get("transaction_type", ""),
                "date": str(t.get("date", "")),
                "status": compliance_results.get(t.get("transaction_id", ""), {}).get("status", "Unknown"),
            }
            for t in transactions[:30]  # Limit to 30 for Gemini
        ]

        prompt = (
            f"Generate a brief executive expense report JSON for {len(transactions)} transactions:\n"
            f"{json.dumps(txn_summary, default=str)}\n\n"
            "Respond ONLY with JSON: {{\"report_title\":\"...\",\"executive_summary\":{{\"text\":\"...\",\"total_transactions\":N,\"total_spent\":N,\"compliant_count\":N,\"violation_count\":N,\"compliance_rate\":N}},\"compliance_health\":{{\"status\":\"Good\"|\"Needs Attention\",\"by_department\":[{{\"department\":\"...\",\"total\":N}}],\"by_category\":[{{\"category\":\"...\",\"total\":N}}]}},\"sections\":[{{\"title\":\"...\",\"visualization_type\":\"bar_chart\"|\"table\",\"config\":{{\"x_key\":\"...\",\"y_keys\":[\"...\"],\"colors\":[\"blue\"]}},\"data\":[...]}}]}}"
        )

        response = client.models.generate_content(
            model=settings.gemini_model, contents=prompt
        )

        parsed = _parse_report_json(response.text)
        if parsed:
            return parsed
    except Exception:
        pass

    return _build_aggregated_report(transactions, compliance_results)


def _parse_report_json(text: str) -> dict | None:
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


async def _audit_transactions(transactions: list[dict]) -> dict[str, dict[str, Any]]:
    """Re-evaluate a sample of transactions against company policy via Gemini."""
    try:
        from google import genai
        if genai is None:
            return {}

        client = genai.Client(api_key=settings.gemini_api_key)
        results: dict[str, dict[str, Any]] = {}

        batch_json = [
            {
                "transaction_id": t.get("transaction_id", ""),
                "merchant": t.get("merchant", ""),
                "amount": t.get("amount", 0),
                "department": t.get("department", ""),
                "transaction_type": t.get("transaction_type", ""),
                "current_status": t.get("approval_status", ""),
                "current_reasoning": t.get("reasoning", ""),
                "current_recommendation": t.get("recommendation"),
                "current_status": t.get("approval_status", ""),
            }
            for t in transactions
        ]

        prompt = (
            "You are a policy auditor double-checking expense transactions. "
            "Review each transaction against standard expense policy (all expenses over $50 need receipts, "
            "transactions over $2000 need approval, any transaction over $10000 needs CFO approval).\n\n"
            "For each transaction, decide if the current decision was correct. "
            "If you disagree, set status to 'Violation' and provide your new recommendation.\n\n"
            "Respond with a JSON array. Only include transactions where you disagree:\n"
            "[{\"transaction_id\":\"...\", \"status\":\"Violation\", \"severity\":\"Low\"|\"Medium\"|\"High\", "
            "\"recommendation\":\"Approve\"|\"Decline\", "
            "\"reasoning\":\"<explanation of why the previous decision was wrong>\"}]\n\n"
            "Return [] if all decisions are correct."
        )

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=f"{prompt}\n\nTransactions to audit:\n{json.dumps(batch_json, default=str)}",
        )

        array_match = re.search(r"\[.*?\]", response.text, re.DOTALL)
        if array_match:
            try:
                arr = json.loads(array_match.group(0))
                for item in arr:
                    if isinstance(item, dict) and item.get("status") == "Violation":
                        tid = item["transaction_id"]
                        results[tid] = {
                            "transaction_id": tid,
                            "status": "Violation",
                            "severity": item.get("severity", "Medium"),
                            "recommendation": item.get("recommendation", "Decline"),
                            "reasoning": item.get("reasoning", "Re-evaluated and flagged."),
                        }
            except json.JSONDecodeError:
                pass

        return results
    except Exception:
        return {}


def _build_aggregated_report(
    transactions: list[dict[str, Any]],
    compliance_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Fast aggregated report from transaction data — no LLM calls."""
    total_spent = sum(t.get("amount", 0) for t in transactions)
    total_txns = len(transactions)
    violations = sum(1 for c in compliance_results.values() if c.get("status") == "Violation")
    pending_count = sum(1 for t in transactions if t.get("approval_status") == "pending")
    compliant = total_txns - violations - pending_count

    # Aggregations
    dept_spend: dict[str, float] = {}
    type_spend: dict[str, float] = {}
    monthly_spend: dict[str, float] = {}
    merchant_spend: dict[str, float] = {}

    for t in transactions:
        d = t.get("department", "Unknown")
        c = t.get("transaction_type") or "Other"
        a = t.get("amount", 0)
        month = str(t.get("date", ""))[:7]
        m = t.get("merchant", "Unknown")

        dept_spend[d] = dept_spend.get(d, 0) + a
        type_spend[c] = type_spend.get(c, 0) + a
        monthly_spend[month] = monthly_spend.get(month, 0) + a
        merchant_spend[m] = merchant_spend.get(m, 0) + a

    compliance_rate = round(compliant / max(total_txns, 1) * 100, 1)
    status = "Good" if violations == 0 else "Needs Attention" if violations < total_txns * 0.2 else "Critical"

    # Build monthly data
    all_months = sorted(monthly_spend.keys())
    if len(all_months) > 1:
        monthly_vis = "area_chart"
        monthly_data = [{"month": m, "spend": round(monthly_spend.get(m, 0), 2)} for m in all_months]
    else:
        monthly_vis = "bar_chart"
        monthly_data = [{"month": m, "spend": round(s, 2)} for m, s in sorted(monthly_spend.items())]

    # Build verbal summaries
    top_month_val = sorted(monthly_spend.items(), key=lambda x: -x[1])[-1] if monthly_spend else ("", 0)
    avg_monthly = round(total_spent / max(len(all_months), 1), 2)
    top10_merchants = sorted(merchant_spend.items(), key=lambda x: -x[1])[:10]
    top10_total = sum(v for _, v in top10_merchants)
    sorted_txns = sorted(transactions, key=lambda x: -x.get("amount", 0))
    top_txn = sorted_txns[0] if sorted_txns else {}

    return {
        "report_title": "Expense Summary Report",
        "generated_at": datetime.now().isoformat(),
        "executive_summary": {
            "text": (
                f"Analysis of {total_txns} transactions totaling ${total_spent:,.2f}. "
                f"{compliant} compliant, {violations} violations ({compliance_rate}% compliance rate). "
                f"{pending_count} transactions pending approval."
            ),
            "total_transactions": total_txns,
            "total_spent": round(total_spent, 2),
            "compliant_count": compliant,
            "violation_count": violations,
            "compliance_rate": compliance_rate,
            "total_pending": pending_count,
        },
        "compliance_health": {
            "status": status,
            "by_department": [
                {"department": d, "total": round(t, 2)}
                for d, t in sorted(dept_spend.items(), key=lambda x: -x[1])
            ],
            "by_category": [
                {"category": c, "total": round(t, 2)}
                for c, t in sorted(type_spend.items(), key=lambda x: -x[1])
            ],
        },
        "sections": [
            {
                "title": "Monthly Spend Trend",
                "summary": f"Monthly spending peaked in {top_month_val[0]} at ${top_month_val[1]:,.2f}. "
                           f"Average monthly spend is ${avg_monthly:,.2f} across {len(all_months)} months.",
                "visualization_type": monthly_vis,
                "config": {"x_key": "month", "y_keys": ["spend"], "colors": ["blue"]},
                "data": monthly_data,
            },
            {
                "title": "Top 10 Merchants",
                "summary": f"The top 10 merchants account for ${top10_total:,.2f} in total spending.",
                "visualization_type": "bar_chart",
                "config": {"x_key": "merchant", "y_keys": ["total"], "colors": ["violet"]},
                "data": [{"merchant": m, "total": round(s, 2)} for m, s in top10_merchants],
            },
            {
                "title": "Top Expenses",
                "summary": f"Highest single expense: ${top_txn.get('amount', 0):,.2f} at {top_txn.get('merchant', 'N/A')}.",
                "visualization_type": "table",
                "config": {"x_key": "merchant", "y_keys": ["amount", "department", "transaction_type"]},
                "data": [
                    {"merchant": t.get("merchant", ""), "amount": t.get("amount", 0),
                      "department": t.get("department", ""), "transaction_type": t.get("transaction_type", "")}
                    for t in sorted_txns[:15]
                ],
            },
        ],
    }
