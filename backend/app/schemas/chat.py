from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class VisualizationConfig(BaseModel):
    x_key: str = ""
    y_keys: list[str] = []
    colors: list[str] = []


class ChatResponse(BaseModel):
    explanation: str
    visualization_type: str = "text"
    config: VisualizationConfig = VisualizationConfig()
    data: list[dict[str, Any]] = []
