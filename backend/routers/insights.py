"""POST /api/insights/query — multi-LLM AI insights endpoint."""
from __future__ import annotations

import os

from fastapi import APIRouter

from ..ai.orchestrator import run_insight_pipeline
from ..models.schemas import InsightRequest, InsightResponse

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/models")
def list_models():
    """Tell the frontend which providers have a key configured.

    In BYO-key deployments (e.g. portfolio Hugging Face Space) ``configured``
    will be False for everything — visitors paste their own keys in the
    sidebar to override per-request. We still surface every model so the UI
    can let users pick any of them.
    """
    available = [
        {"id": "claude", "label": "Claude (Anthropic)",
         "configured": bool(os.environ.get("ANTHROPIC_API_KEY"))},
        {"id": "openai", "label": "GPT-4o (OpenAI)",
         "configured": bool(os.environ.get("OPENAI_API_KEY"))},
        {"id": "gemini", "label": "Gemini 1.5 Pro",
         "configured": bool(os.environ.get("GOOGLE_API_KEY"))},
    ]
    return {"models": available}


@router.post("/query", response_model=InsightResponse)
async def query(request: InsightRequest) -> InsightResponse:
    return await run_insight_pipeline(request)


@router.get("/narrative")
async def narrative_insights(stores: str = "", regions: str = "", date_from: str = "",
                             date_to: str = "", reasons: str = "", states: str = ""):
    """LLM-narrated, code-grounded insights — re-words derived_insights with
    strict no-invention rules. Falls back to raw structured insights when no
    API key is configured."""
    from ..ai.narrator import narrate_insights
    from ..routers.analytics import _parse
    return await narrate_insights(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/recommendations")
async def recommendations_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                                   date_to: str = "", reasons: str = "", states: str = ""):
    """Prioritised, fact-grounded next actions. LLM-synthesised when available,
    falls back to a deterministic template-based recommender otherwise."""
    from ..ai.narrator import recommend_actions
    from ..routers.analytics import _parse
    return await recommend_actions(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/suggestions")
async def suggestions_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                               date_to: str = "", reasons: str = "", states: str = ""):
    """Investigation question suggestions derived from the current filter set."""
    from ..ai.narrator import suggest_questions
    from ..routers.analytics import _parse
    return await suggest_questions(**_parse(stores, regions, date_from, date_to, reasons, states))
