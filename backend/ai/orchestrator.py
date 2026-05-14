from ..models.schemas import AIConfig, InsightRequest, InsightResponse, ModelResponse
from ..pipeline.metrics import build_data_context_summary
from .agents import call_models_parallel, AGENT_MAP
from .judge import run_judge


async def run_insight_pipeline(request: InsightRequest) -> InsightResponse:
    context = build_data_context_summary()
    config  = request.ai_config
    history = request.history
    question = request.question
    api_keys = config.api_keys or {}  # BYO-key support: visitor-supplied keys

    # ── Single model mode ─────────────────────────────────────────────────────
    if config.mode == "single":
        model_name = config.model.value
        if model_name not in AGENT_MAP:
            return InsightResponse(
                question=question,
                mode="single",
                model_responses=[ModelResponse(model=model_name, response="",
                                               error=f"Unknown model: {model_name}")],
                final_answer=f"Model '{model_name}' is not configured."
            )
        agent = AGENT_MAP[model_name]
        result = await agent(question, context, history, api_key=api_keys.get(model_name))
        return InsightResponse(
            question=question,
            mode="single",
            model_responses=[result],
            final_answer=result.response if not result.error else f"Error: {result.error}"
        )

    # ── Multi model mode ──────────────────────────────────────────────────────
    model_names = [m.value for m in config.models]
    if not model_names:
        model_names = ["claude"]

    responses = await call_models_parallel(
        model_names, question, context, history, api_keys=api_keys,
    )

    judge_result = None
    final_answer = ""

    if config.enable_judge:
        judge_result = await run_judge(
            question=question,
            data_context=context,
            model_responses=responses,
            judge_model=config.judge_model.value,
            api_key=api_keys.get(config.judge_model.value),
        )
        final_answer = judge_result.recommended_answer
    else:
        # No judge: return first successful response
        final_answer = next(
            (r.response for r in responses if r.response and not r.error),
            "No successful response from any model."
        )

    return InsightResponse(
        question=question,
        mode="multi",
        model_responses=responses,
        judge_result=judge_result,
        final_answer=final_answer
    )
