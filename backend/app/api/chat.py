import json
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.database import get_collection
from app.graph.nodes.conversational_analyst import conversational_analyst_node
from app.graph.state import GraphState
from app.schemas.chat import ChatRequest, ChatResponse, VisualizationConfig

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Feature 1: Talk to Your Data - conversational text-to-MQL + charting."""
    try:
        state = GraphState(
            messages=[{"role": "user", "content": request.message}],
            current_transactions=[],
            compliance_results={},
            report_payload={},
            pending_approval=None,
            user_query=request.message,
            error=None,
        )

        result = await conversational_analyst_node(state)
        messages = result.get("messages", [])
        last_msg = messages[-1] if messages else {}
        content = last_msg.get("content", {})

        if isinstance(content, str):
            return ChatResponse(
                explanation=content,
                visualization_type="text",
                config=VisualizationConfig(),
                data=[],
            )

        return ChatResponse(
            explanation=content.get("explanation", ""),
            visualization_type=content.get("visualization_type", "text"),
            config=VisualizationConfig(**content.get("config", {})),
            data=content.get("data", []),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming version of chat - returns chunks as they arrive."""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        try:
            state = GraphState(
                messages=[{"role": "user", "content": request.message}],
                current_transactions=[],
                compliance_results={},
                report_payload={},
                pending_approval=None,
                user_query=request.message,
                error=None,
            )

            result = await conversational_analyst_node(state)
            messages = result.get("messages", [])
            last_msg = messages[-1] if messages else {}
            content = last_msg.get("content", {})

            if isinstance(content, str):
                yield f"data: {json.dumps({'type': 'text', 'content': content})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'result', **content, '_default_str': str})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
