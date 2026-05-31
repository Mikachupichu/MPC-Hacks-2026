from typing import Any

from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class VisualizationConfig(BaseModel):
    x_key: str = ""
    y_keys: list[str] = []
    colors: list[str] = []

    @field_validator("x_key", mode="before")
    @classmethod
    def coerce_x_key(cls, v: Any) -> str:
        return v if isinstance(v, str) else ""

    @field_validator("y_keys", mode="before")
    @classmethod
    def coerce_y_keys(cls, v: Any) -> list[str]:
        return v if isinstance(v, list) else []

    @field_validator("colors", mode="before")
    @classmethod
    def coerce_colors(cls, v: Any) -> list[str]:
        return v if isinstance(v, list) else []


class ChatResponse(BaseModel):
    explanation: str
    visualization_type: str = "text"
    config: VisualizationConfig = VisualizationConfig()
    data: list[dict[str, Any]] = []
    conversation_id: str | None = None
