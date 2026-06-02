import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.graph.graph import get_graph
from app.graph.state import GraphState
from app.schemas.chat import ChatRequest, ChatResponse, VisualizationConfig

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Feature 1: Talk to Your Data - with conversation memory."""
    try:
        conversation_id = request.conversation_id or str(uuid4())

        state = GraphState(
            messages=[{"role": "user", "content": request.message}],
            current_transactions=[],
            compliance_results={},
            report_payload={},
            pending_approval=None,
            user_query=request.message,
            conversation_id=conversation_id,
            error=None,
            task_type="chat",
        )

        graph = get_graph()
        result = await graph.ainvoke(state)
        messages = result.get("messages", [])
        last_msg = messages[-1] if messages else {}
        content = last_msg.get("content", {})

        if isinstance(content, str):
            return ChatResponse(
                explanation=content,
                visualization_type="text",
                config=VisualizationConfig(),
                data=[],
                conversation_id=conversation_id,
            )

        return ChatResponse(
            explanation=content.get("explanation", ""),
            visualization_type=content.get("visualization_type", "text"),
            config=VisualizationConfig(**content.get("config", {})),
            data=content.get("data", []),
            conversation_id=conversation_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming version of chat - returns chunks as they arrive."""
    from fastapi.responses import StreamingResponse

    async def event_stream():
        try:
            conversation_id = request.conversation_id or str(uuid4())

            state = GraphState(
                messages=[{"role": "user", "content": request.message}],
                current_transactions=[],
                compliance_results={},
                report_payload={},
                pending_approval=None,
                user_query=request.message,
                conversation_id=conversation_id,
                error=None,
                task_type="chat",
            )

            graph = get_graph()
            result = await graph.ainvoke(state)
            messages = result.get("messages", [])
            last_msg = messages[-1] if messages else {}
            content = last_msg.get("content", {})

            if isinstance(content, str):
                yield f"data: {json.dumps({'type': 'text', 'content': content, 'conversation_id': conversation_id})}\n\n"
            else:
                payload = {
                    "type": "result",
                    "conversation_id": conversation_id,
                    **content,
                }
                payload.pop("_default_str", None)
                yield f"data: {json.dumps(payload, default=str)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
