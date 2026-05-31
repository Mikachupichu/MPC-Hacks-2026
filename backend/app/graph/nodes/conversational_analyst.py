"""Conversational analyst node - Text-to-MQL with conversation history."""

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


SYSTEM_PROMPT = """You are an AI financial analyst for SMB expense data. You help finance managers explore their company's spending by converting natural language questions into MongoDB aggregation pipelines.

The transactions collection schema:
- transaction_id: string
- date: ISO date string (e.g. "2025-09-02")
- merchant: string (merchant name)
- amount: float (transaction amount in local currency)
- currency: string ("CAD" for Canadian, "USD" for US)
- conversion_rate: float (USD to CAD rate if applicable)
- department: string — one of ["Operations", "Finance"]
- transaction_category: integer — numeric category (1=operations, 2=interest, 3=cash, 10=fees, 12=card fees, 19=payments)
- transaction_type: string — human-readable: "Fuel", "Permit", "Toll", "Vehicle Maintenance", "Car Wash", "Shipping", "Equipment", "Telecom", "Lodging", "Meals", "Transportation", "Office Supplies", "Software", "Services", "Cash Advance", "Operations Expense", "Interest Charge", "Card Fee", "Payment", "Other"
- description: string
- items: array of {"description": str, "amount": float}
- tags: array of strings (e.g. "fuel", "high-value", "usd", "transportation")
- compliance_history: array
- approval_status: string ("approved", "pending", "denied", "not_required")
- payment_method: string ("corporate_card" or "personal")
- is_reimbursable: boolean
- merchant_city: string
- merchant_state: string
- merchant_country: string ("USA" or "CAN")
- merchant_category_code: integer (MCC)
- original_transaction_code: integer

AVAILABLE DATA FACTS (IMPORTANT - use these to answer accurately):
- Date range of data: August 2025 to March 2026 (NOT 2023 or 2024)
- Two departments: Operations (fleet/trucking company — most data), Finance (bill payments, fees)
- Transaction codes 3001/3006 are Operations fleet card (fuel, permits, tolls, maintenance)
- Transaction code 3005 is Operations — cash advances for drivers
- Transaction codes 108/137/375/401/404 are Finance (bill payments, card fees, rewards, interest)
- "Fuel" type transactions have tags: ["fuel"] and MCCs 5541/5542
- "Permit" type has MCC 9399 (government permits) — very common
- Category 1 includes: Fuel, Permit, Toll, Vehicle Maintenance, Car Wash, Shipping, Equipment, Telecom, Lodging, Meals, etc. broken down by MCC
- Category 2 = Interest (code 404), Category 3 = Cash Advance (code 3005), Category 10 = Fee (code 401), Category 12 = Card Fee (code 137), Category 19 = Payment (code 108)
- USD transactions have currency="USD" with a conversion_rate field

Your tasks:
1. Read conversation history for context (follow-ups reference prior queries).
2. Generate a MongoDB aggregation pipeline (JSON array of stages) that answers the query.
3. ONLY include $match stages for dates, departments, categories the user specifically asked about.

Rules:
- Use $match, $group, $sort, $project, $limit, $unwind, $dateToString as needed.
- For date ranges use ISO strings with $gte/$lte: "2025-08-01"
- For department/category comparisons, include ALL groups to show comparison context.
- ALWAYS limit results to a reasonable number (max 20 items for charts).

CRITICAL: Only generate a pipeline + chart when the user's question requires querying data. If the question is conversational or just asks about what was already shown, set pipeline to [] and visualization_type to "text".

ALWAYS respond with valid JSON. No markdown, no code fences, just raw JSON:
{
  "pipeline": [...],
  "explanation": "Brief summary of findings",
  "visualization_type": "bar_chart" | "line_chart" | "area_chart" | "donut_chart" | "table" | "text",
  "config": {
    "x_key": "field_name",
    "y_keys": ["field1"],
    "colors": ["blue", "emerald", "violet", "amber"]
  }
}

RULES for visualization_type:
- bar_chart: Comparing items side-by-side (spending by dept, by merchant, by category)
- line_chart: Trends over time across many periods (monthly spend trend)
- area_chart: Cumulative or filled trends (running totals, stacked time series)
- donut_chart: Percentage or distribution breakdowns (what % each dept/category represents)
- table: When exact numbers matter more than visual comparison
- text: Greetings, follow-ups about existing data, conversational clarifications ("are these in CAD?", "what period is this?"), thanks — no chart needed

IMPORTANT: Use Tremor color names (blue, cyan, indigo, violet, purple, fuchsia, pink, rose, emerald, teal, amber, orange) NOT hex codes.
"""

# In-memory conversation store
_conversations: dict[str, list[dict[str, str]]] = {}


async def conversational_analyst_node(state: GraphState) -> dict[str, Any]:
    """Handles conversational Text-to-MQL with memory of prior exchanges."""
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")
    conversation_id = state.get("conversation_id", "")

    if not user_query and messages:
        last_msg = messages[-1]
        user_query = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

    if not user_query:
        return {
            "messages": messages + [{"role": "assistant", "content": "How can I help you with your expense data?"}],
        }

    client = _get_gemini_client()
    model = settings.gemini_model

    # Build history context
    history = _conversations.get(conversation_id, [])
    history_str = _format_history(history)

    # LLM generates the pipeline + viz config
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Conversation history:\n{history_str}\n\n"
        f"Current user query: {user_query}\n\n"
        f"Respond with JSON only."
    )

    response = client.models.generate_content(model=model, contents=prompt)
    parsed = _parse_llm_json(response.text)

    pipeline = parsed.get("pipeline", [])
    explanation = parsed.get("explanation", "")
    viz_type = parsed.get("visualization_type", "text")
    config = parsed.get("config", {})

    # Execute pipeline
    data = []
    if pipeline:
        try:
            collection = await get_collection("transactions")
            cursor = collection.aggregate(pipeline)
            data = await cursor.to_list(length=None)
        except Exception as e:
            explanation = f"I ran into an issue with that query: {str(e)}"
            viz_type = "text"

    # If pipeline returned data but LLM gave a generic/no explanation, summarize
    if data and not explanation:
        data_str = json.dumps(data[:50], default=str)
        summary_prompt = (
            f"History:\n{history_str}\n\n"
            f"Query: '{user_query}'\n\n"
            f"Result: {data_str}\n\n"
            f"Brief summary + choose viz (bar_chart/line_chart/table/text) + config "
            f"with Tremor color names. JSON only."
        )
        response2 = client.models.generate_content(model=model, contents=summary_prompt)
        parsed2 = _parse_llm_json(response2.text)
        explanation = parsed2.get("explanation", explanation)
        viz_type = parsed2.get("visualization_type", viz_type)
        config = parsed2.get("config", config)

    # If pipeline returned NO data, force text mode with honest message
    if not data and pipeline:
        explanation = (
            f"I couldn't find any transactions matching that criteria. "
            f"Our data covers August 2025 through March 2026. "
            f"Try asking about a different time period, department, or category."
        )
        viz_type = "text"
        config = {}

    # If a pipeline ran and returned data but the LLM chose "text",
    # coerce to table so the user always sees the numbers.
    if data and viz_type == "text":
        viz_type = "table"
        if data:
            keys = list(data[0].keys())
            if keys:
                x_key = keys[0]
                numeric_keys = [k for k in keys[1:] if isinstance(data[0].get(k), (int, float))]
                y_keys = numeric_keys if numeric_keys else keys[1:3]
                config = {"x_key": x_key, "y_keys": y_keys, "colors": ["blue", "emerald", "amber"]}

    result = {
        "explanation": explanation,
        "visualization_type": viz_type,
        "config": config,
        "data": data,
    }

    # Persist conversation history
    _conversations.setdefault(conversation_id, [])
    _conversations[conversation_id].append({"role": "user", "text": user_query})
    if explanation:
        _conversations[conversation_id].append({"role": "assistant", "text": explanation})

    new_messages = list(messages)
    new_messages.append({"role": "assistant", "content": result})

    return {
        "messages": new_messages,
        "conversation_id": conversation_id,
    }


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "No prior conversation."
    parts = []
    for msg in history[-10:]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        parts.append(f"{role}: {msg.get('text', '')}")
    return "\n".join(parts)


def _get_gemini_client():
    if genai is None:
        raise ImportError("google-genai package is required")
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_llm_json(text: str) -> dict:
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass
    return {
        "pipeline": [],
        "explanation": text.strip(),
        "visualization_type": "text",
        "config": {},
    }
