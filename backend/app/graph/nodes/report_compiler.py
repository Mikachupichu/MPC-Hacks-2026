import json
import re
from typing import Any

from app.core.config import settings
from app.graph.nodes.compliance_scanner import evaluate_transactions
from app.graph.state import GraphState

try:
    from google import genai
except ImportError:
    genai = None


REPORT_SYSTEM_PROMPT = """You are an AI expense report compiler. Your job is to take a batch of transactions with compliance assessments and produce a comprehensive, beautifully structured JSON dashboard document.

The report must include:
1. An executive summary text block describing the overall expense health
2. Overall compliance health status (percentage compliant, total spent, etc.)
3. Nested sub-sections with structured chart data ready for Tremor visualization

Respond ONLY with valid JSON in this exact structure:
{{
  "report_title": "Executive Expense Summary",
  "generated_at": "ISO date string",
  "executive_summary": {{
    "text": "Multi-sentence summary of findings...",
    "total_transactions": 0,
    "total_spent": 0.0,
    "compliant_count": 0,
    "violation_count": 0,
    "compliance_rate": 0.0,
    "total_pending": 0
  }},
  "compliance_health": {{
    "status": "Good" | "Needs Attention" | "Critical",
    "by_department": [
      {{"department": "Engineering", "compliant": 10, "violations": 2, "total": 12000.0}}
    ],
    "by_category": [
      {{"category": "Software", "compliant": 5, "violations": 1, "total": 8000.0}}
    ]
  }},
  "sections": [
    {{
      "title": "Spending by Department",
      "visualization_type": "bar_chart",
      "config": {{"x_key": "department", "y_keys": ["total"], "colors": ["#3b82f6"]}},
      "data": [{{"department": "Engineering", "total": 45000.0}}]
    }},
    {{
      "title": "Monthly Spend Trend",
      "visualization_type": "line_chart",
      "config": {{"x_key": "month", "y_keys": ["spend"], "colors": ["#10b981"]}},
      "data": [{{"month": "2026-01", "spend": 32000.0}}]
    }},
    {{
      "title": "Top Expenses",
      "visualization_type": "table",
      "config": {{"x_key": "merchant", "y_keys": ["amount", "department"]}},
      "data": [{{"merchant": "AWS", "amount": 5200.0, "department": "Engineering"}}]
    }},
    {{
      "title": "Compliance Overview",
      "visualization_type": "text",
      "config": {{}},
      "data": []
    }}
  ]
}}

Be thorough. Generate at least 4-5 sections covering: department breakdown, category breakdown, monthly trend, top expenses, and compliance breakdown.
Ensure all numbers are reasonable and add up correctly.
"""


async def report_compiler_node(state: GraphState) -> dict[str, Any]:
    """Compiles multi-transaction expense logs into a single summary report.

    Receives a batch of transactions, pipes them through compliance scanning,
    then compiles a comprehensive dashboard JSON document.
    """
    transactions = state.get("current_transactions", [])
    if not transactions:
        return {
            "report_payload": {},
            "error": "No transactions provided for report compilation.",
        }

    try:
        # Run compliance scan on the entire batch
        compliance_results = await evaluate_transactions(transactions)

        # Build compliance-augmented transaction list
        augmented_txns = []
        for txn in transactions:
            txn_id = txn.get("transaction_id", str(txn.get("_id", "")))
            compliance = compliance_results.get(txn_id, {})
            augmented_txns.append({**txn, "_compliance": compliance})

        # Generate report via Gemini
        report_payload = await _generate_report(augmented_txns, compliance_results)

        return {
            "report_payload": report_payload,
            "compliance_results": compliance_results,
            "messages": state.get("messages", [])
            + [
                {
                    "role": "assistant",
                    "content": "Report compiled successfully.",
                }
            ],
        }

    except Exception as e:
        return {
            "report_payload": {},
            "error": f"Report compilation failed: {str(e)}",
        }


async def _generate_report(
    transactions: list[dict[str, Any]],
    compliance_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Generate the comprehensive report JSON via Gemini."""
    try:
        if genai is None:
            return _build_fallback_report(transactions, compliance_results)

        client = genai.Client(api_key=settings.gemini_api_key)

        txn_summary = []
        for txn in transactions[:100]:  # Limit to 100 for token budget
            txn_id = txn.get("transaction_id", "")
            compliance = compliance_results.get(txn_id, {})
            txn_summary.append({
                "transaction_id": txn_id,
                "merchant": txn.get("merchant", ""),
                "amount": txn.get("amount", 0),
                "department": txn.get("department", ""),
                "category": txn.get("category", ""),
                "date": str(txn.get("date", "")),
                "compliance_status": compliance.get("status", "Unknown"),
                "severity": compliance.get("severity", "None"),
            })

        prompt = (
            f"{REPORT_SYSTEM_PROMPT}\n\n"
            f"Generate a comprehensive expense report from these {len(transactions)} transactions:\n"
            f"{json.dumps(txn_summary, default=str)}\n\n"
            f"Respond with the complete JSON report only."
        )

        response = client.models.generate_content(
            model=settings.gemini_model, contents=prompt
        )

        parsed = _parse_report_json(response.text)
        if parsed:
            return parsed

    except Exception:
        pass

    return _build_fallback_report(transactions, compliance_results)


def _parse_report_json(text: str) -> dict | None:
    """Robust JSON parser for report output."""
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


def _build_fallback_report(
    transactions: list[dict[str, Any]],
    compliance_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a structured report from data without LLM."""
    total_spent = sum(t.get("amount", 0) for t in transactions)
    total_txns = len(transactions)
    violations = sum(
        1 for c in compliance_results.values() if c.get("status") == "Violation"
    )
    compliant = total_txns - violations

    dept_spend: dict[str, float] = {}
    cat_spend: dict[str, float] = {}
    for t in transactions:
        d = t.get("department", "Unknown")
        c = t.get("category", "Unknown")
        a = t.get("amount", 0)
        dept_spend[d] = dept_spend.get(d, 0) + a
        cat_spend[c] = cat_spend.get(c, 0) + a

    return {
        "report_title": "Expense Summary Report",
        "generated_at": str(__import__("datetime").datetime.now()),
        "executive_summary": {
            "text": f"Analysis of {total_txns} transactions totaling ${total_spent:,.2f}. "
            f"Found {violations} policy violations ({violations/max(total_txns,1)*100:.0f}% violation rate).",
            "total_transactions": total_txns,
            "total_spent": round(total_spent, 2),
            "compliant_count": compliant,
            "violation_count": violations,
            "compliance_rate": round(compliant / max(total_txns, 1) * 100, 1),
            "total_pending": 0,
        },
        "compliance_health": {
            "status": "Good" if violations == 0 else "Needs Attention" if violations < total_txns * 0.2 else "Critical",
            "by_department": [
                {"department": d, "total": round(t, 2)}
                for d, t in sorted(dept_spend.items(), key=lambda x: -x[1])
            ],
            "by_category": [
                {"category": c, "total": round(t, 2)}
                for c, t in sorted(cat_spend.items(), key=lambda x: -x[1])
            ],
        },
        "sections": [
            {
                "title": "Spending by Department",
                "visualization_type": "bar_chart",
                "config": {"x_key": "department", "y_keys": ["total"], "colors": ["#3b82f6"]},
                "data": [{"department": d, "total": round(t, 2)} for d, t in sorted(dept_spend.items(), key=lambda x: -x[1])],
            },
            {
                "title": "Spending by Category",
                "visualization_type": "bar_chart",
                "config": {"x_key": "category", "y_keys": ["total"], "colors": ["#10b981"]},
                "data": [{"category": c, "total": round(t, 2)} for c, t in sorted(cat_spend.items(), key=lambda x: -x[1])],
            },
            {
                "title": "Top Expenses",
                "visualization_type": "table",
                "config": {"x_key": "merchant", "y_keys": ["amount", "department", "category"]},
                "data": sorted(
                    [{"merchant": t.get("merchant", ""), "amount": t.get("amount", 0),
                      "department": t.get("department", ""), "category": t.get("category", "")}
                     for t in transactions],
                    key=lambda x: -x["amount"],
                )[:10],
            },
        ],
    }
