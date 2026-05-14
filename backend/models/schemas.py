"""Pydantic models for the Retail Insight API."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── AI configuration ──────────────────────────────────────────────────────────

class ModelType(str, Enum):
    claude = "claude"
    openai = "openai"
    gemini = "gemini"


class AIConfig(BaseModel):
    mode: Literal["single", "multi"] = "single"
    model: ModelType = ModelType.claude
    models: list[ModelType] = Field(default_factory=lambda: [ModelType.claude])
    enable_judge: bool = False
    judge_model: ModelType = ModelType.claude
    # BYO-key support for portfolio deployment: visitors paste their own keys
    # in the sidebar; Streamlit forwards them per-request. Keys here override
    # ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY env vars for the
    # duration of this single request only.
    api_keys: dict[str, str] = Field(default_factory=dict)


# ── Chat history & request ────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class InsightRequest(BaseModel):
    question: str
    history: list[ChatMessage] = Field(default_factory=list)
    ai_config: AIConfig = Field(default_factory=AIConfig)
    filters: dict[str, Any] = Field(default_factory=dict)


# ── Model + judge responses ───────────────────────────────────────────────────

class ModelResponse(BaseModel):
    model: str
    response: str = ""
    latency_ms: float | None = None
    error: str | None = None


class JudgeResult(BaseModel):
    synthesis: str = ""
    key_agreements: list[str] = Field(default_factory=list)
    key_disagreements: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    model_assessments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recommended_answer: str = ""


class InsightResponse(BaseModel):
    question: str
    mode: Literal["single", "multi"]
    model_responses: list[ModelResponse] = Field(default_factory=list)
    judge_result: JudgeResult | None = None
    final_answer: str = ""


# ── Analytics filter envelope (shared by routers) ─────────────────────────────

class AnalyticsFilters(BaseModel):
    """Parsed query-string filters used across analytics endpoints."""
    stores: list[int] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None
    reasons: list[str] = Field(default_factory=list)
