import json
import re
from typing import Any

from app.core.config import settings
from app.core.database import get_collection
from app.graph.state import GraphState

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None


SYSTEM_PROMPT = """You are an AI financial analyst for SMB expense data. You help finance managers explore their company's spending by converting natural language questions into MongoDB aggregation pipelines.

The transactions collection has this schema:
{{
  "transaction_id": str,
  "date": datetime (ISO format),
  "merchant": str,
  "amount": float,
  "currency": str ("CAD"),
  "department": str ("Engineering","Marketing","Sales","Operations","HR","Finance","Product"),
  "employee": str,
  "employee_id": str,
  "category": str ("Software","Travel","Office Supplies","Meals","Entertainment","Hardware","Services","Training","Utilities","Other"),
  "description": str,
  "items": [{{"description":str, "amount":float}}],
  "tags": [str],
  "approval_status": str ("pending","approved","denied","not_required"),
  "payment_method": str ("corporate_card","personal"),
  "is_reimbursable": bool
}}

Your job is to:
1. Generate a MongoDB aggregation pipeline (as a JSON list of stages) that answers the user's query.
2. After the pipeline runs, analyze the results and produce a structured visualization layout.

ALWAYS respond with valid JSON in this exact format:
{{
  "pipeline": [ ... MongoDB aggregation pipeline stages ... ],
  "explanation": "Brief summary of the data",
  "visualization_type": "bar_chart" | "line_chart" | "table" | "text",
  "config": {{
    "x_key": "field_for_x_axis",
    "y_keys": ["field_for_y_axis"],
    "colors": ["#color1", "#color2"]
  }}
}}

If the query is conversational (greeting, thanks, etc.), set pipeline to [] and visualization_type to "text" and explain warmly.
If no aggregation is needed, just return a text response explaining the data situation.
Use $match, $group, $sort, $project, $limit, $unwind, $dateToString as needed.
For date filtering, use ISO date strings.
For department/category comparisons, use $group with multiple keys.
"""


async def conversational_analyst_node(state: GraphState) -> dict[str, Any]:
    """Handles conversational Text-to-MQL and dynamic charting."""
    messages = state.get("messages", [])
    user_query = state.get("user_query", "")

    if not user_query and messages:
        last_msg = messages[-1]
        user_query = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)

    if not user_query:
        return {
            "messages": messages + [{"role": "assistant", "content": "How can I help you with your expense data?"}],
        }

    client = _get_gemini_client()
    model = settings.gemini_model

    # Step 1: LLM generates the pipeline + viz config
    schema_hint = _build_schema_hint()
    prompt = f"{SYSTEM_PROMPT}\n\nUser query: {user_query}\n\nTransaction schema: {schema_hint}\n\nRespond with JSON only."
    response = client.models.generate_content(model=model, contents=prompt)
    parsed = _parse_llm_json(response.text)

    pipeline = parsed.get("pipeline", [])
    explanation = parsed.get("explanation", "")
    viz_type = parsed.get("visualization_type", "text")
    config = parsed.get("config", {})

    # Step 2: Execute pipeline if one was generated
    data = []
    if pipeline:
        try:
            collection = await get_collection("transactions")
            cursor = collection.aggregate(pipeline)
            data = await cursor.to_list(length=None)
        except Exception as e:
            explanation = f"I encountered an error querying the data: {str(e)}"
            viz_type = "text"

    # Step 3: If we have data but no explanation yet, get LLM to summarize
    if data and not explanation:
        data_str = json.dumps(data[:50], default=str)
        summary_prompt = (
            f"Given this user query: '{user_query}'\n\n"
            f"And this query result: {data_str}\n\n"
            f"Provide a brief conversational summary of the findings. "
            f"Then determine the best visualization: bar_chart, line_chart, table, or text. "
            f"Respond in JSON: {{\"explanation\": \"...\", \"visualization_type\": \"...\", \"config\": {{...}}}}"
        )
        response2 = client.models.generate_content(model=model, contents=summary_prompt)
        parsed2 = _parse_llm_json(response2.text)
        explanation = parsed2.get("explanation", explanation)
        viz_type = parsed2.get("visualization_type", viz_type)
        config = parsed2.get("config", config)

    result = {
        "explanation": explanation,
        "visualization_type": viz_type,
        "config": config,
        "data": data,
    }

    new_messages = list(messages)
    new_messages.append({"role": "assistant", "content": result})

    return {
        "messages": new_messages,
    }


def _build_schema_hint() -> str:
    return """Fields: transaction_id (str), date (datetime), merchant (str), amount (float),
currency (str="CAD"), department (str), employee (str), employee_id (str),
category (str), description (str), items (array), tags (array),
approval_status (str), payment_method (str), is_reimbursable (bool)
Sample departments: Engineering, Marketing, Sales, Operations, HR, Finance, Product
Sample categories: Software, Travel, Office Supplies, Meals, Entertainment, Hardware, Services, Training, Utilities, Other"""


def _get_gemini_client():
    if genai is None:
        raise ImportError("google-genai package is required")
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_llm_json(text: str) -> dict:
    """Robust JSON parser with fallback for LLM output."""
    # Try to find JSON block with ```json ... ``` markers
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try parsing the whole text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try finding a JSON object with braces
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Fallback: return text-only response
    return {
        "pipeline": [],
        "explanation": text.strip(),
        "visualization_type": "text",
        "config": {},
    }
