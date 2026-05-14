"""LLM agent functions with BYO-key support.

Each agent accepts an optional ``api_key`` parameter. Resolution order:
  1. Per-request key (passed by orchestrator from the request body)
  2. Environment variable

This pattern lets the public portfolio deployment ship with no preset API keys
yet still let visitors paste their own keys via the Streamlit sidebar to
exercise the AI surfaces.
"""
import asyncio
import time
import os
from dotenv import load_dotenv
from typing import Optional
from ..models.schemas import ModelResponse


load_dotenv()


def _as_msg(m) -> dict:
    """Normalise a history entry — accept either a Pydantic ChatMessage or a plain dict."""
    if isinstance(m, dict):
        return {"role": m.get("role", "user"), "content": m.get("content", "")}
    return {"role": getattr(m, "role", "user"), "content": getattr(m, "content", "")}


def _resolve_key(provider: str, override: Optional[str]) -> str:
    """Resolve an API key. Per-request override beats env."""
    if override and override.strip():
        return override.strip()
    env_var = {
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }[provider]
    return os.environ.get(env_var, "")


async def call_claude(question: str, context: str, history: list,
                      api_key: Optional[str] = None) -> ModelResponse:
    t0 = time.time()
    try:
        import anthropic
        key = _resolve_key("claude", api_key)
        if not key:
            raise RuntimeError("No Anthropic API key configured. "
                               "Paste your key in the sidebar to enable Claude.")
        client = anthropic.AsyncAnthropic(api_key=key)
        messages = [
            _as_msg(m) for m in history
            if _as_msg(m)["role"] in ("user", "assistant")
        ]
        messages.append({"role": "user", "content": question})

        response = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=context,
            messages=messages
        )
        return ModelResponse(
            model="claude",
            response=response.content[0].text,
            latency_ms=round((time.time() - t0) * 1000, 1)
        )
    except Exception as e:
        return ModelResponse(
            model="claude", response="", error=str(e),
            latency_ms=round((time.time() - t0) * 1000, 1)
        )


async def call_openai(question: str, context: str, history: list,
                      api_key: Optional[str] = None) -> ModelResponse:
    t0 = time.time()
    try:
        from openai import AsyncOpenAI
        key = _resolve_key("openai", api_key)
        if not key:
            raise RuntimeError("No OpenAI API key configured. "
                               "Paste your key in the sidebar to enable GPT-4o.")
        client = AsyncOpenAI(api_key=key)
        messages = [{"role": "system", "content": context}]
        for m in history:
            d = _as_msg(m)
            if d["role"] in ("user", "assistant", "system"):
                messages.append(d)
        messages.append({"role": "user", "content": question})

        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=800,
            messages=messages
        )
        return ModelResponse(
            model="openai",
            response=response.choices[0].message.content,
            latency_ms=round((time.time() - t0) * 1000, 1)
        )
    except Exception as e:
        return ModelResponse(
            model="openai", response="", error=str(e),
            latency_ms=round((time.time() - t0) * 1000, 1)
        )


async def call_gemini(question: str, context: str, history: list,
                      api_key: Optional[str] = None) -> ModelResponse:
    t0 = time.time()
    try:
        import google.generativeai as genai
        key = _resolve_key("gemini", api_key)
        if not key:
            raise RuntimeError("No Google API key configured. "
                               "Paste your key in the sidebar to enable Gemini.")
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            system_instruction=context
        )
        gemini_history = []
        for m in history:
            d = _as_msg(m)
            role = "user" if d["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [d["content"]]})

        chat = model.start_chat(history=gemini_history)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat.send_message, question)
        return ModelResponse(
            model="gemini",
            response=response.text,
            latency_ms=round((time.time() - t0) * 1000, 1)
        )
    except Exception as e:
        return ModelResponse(
            model="gemini", response="", error=str(e),
            latency_ms=round((time.time() - t0) * 1000, 1)
        )


AGENT_MAP = {
    "claude": call_claude,
    "openai": call_openai,
    "gemini": call_gemini,
}


async def call_models_parallel(
    models: list,
    question: str,
    context: str,
    history: list,
    api_keys: Optional[dict] = None,
) -> list[ModelResponse]:
    keys = api_keys or {}
    tasks = [
        AGENT_MAP[m](question, context, history, api_key=keys.get(m))
        for m in models if m in AGENT_MAP
    ]
    return await asyncio.gather(*tasks)
