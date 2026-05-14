import os
import json
import re
import time
from ..models.schemas import JudgeResult, ModelResponse
from dotenv import load_dotenv

load_dotenv()


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _extract_json(raw: str) -> dict:
    """Parse a JSON object that the model may have wrapped in markdown fences
    or surrounded with prose. Tries, in order:
      1. raw JSON
      2. fenced ```json ... ``` block
      3. balanced-brace extraction from the first '{' to its matching '}'
    Raises ValueError if nothing parses.
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty judge output")

    # 1) plain JSON
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2) fenced block
    m = _FENCE_RE.match(s)
    if m:
        inner = m.group(1).strip()
        try:
            return json.loads(inner)
        except json.JSONDecodeError:
            s = inner  # fall through with the de-fenced content

    # 3) balanced-brace extraction (handles preamble/trailing prose)
    start = s.find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(s)):
            ch = s[i]
            if esc:
                esc = False
                continue
            if ch == "\\":
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(s[start:i + 1])

    raise ValueError("no parseable JSON object in judge output")


JUDGE_SYSTEM = """You are an expert AI judge evaluating multiple AI model responses to a retail analytics question.

Your task:
1. Evaluate each model's response for accuracy, completeness, and actionability
2. Identify where models agree and where they disagree
3. Flag any factual errors against the provided data context
4. Synthesize the best possible final answer

You MUST respond with valid JSON only. No markdown fences. No preamble.

JSON schema:
{
  "synthesis": "A paragraph explaining the overall quality of responses",
  "key_agreements": ["point 1", "point 2"],
  "key_disagreements": ["disagreement 1"],
  "confidence": "high|medium|low",
  "model_assessments": {
    "model_name": {"score": 1-10, "strengths": "...", "weaknesses": "..."}
  },
  "recommended_answer": "The best synthesized answer to the original question"
}"""


async def run_judge(
    question: str,
    data_context: str,
    model_responses: list[ModelResponse],
    judge_model: str = "claude",
    api_key: str | None = None,
) -> JudgeResult:
    # BYO-key support: prefer per-request key, else env
    def _key(env_var: str) -> str:
        if api_key and api_key.strip():
            return api_key.strip()
        return os.environ.get(env_var, "")
    responses_text = "\n\n".join([
        f"=== {r.model.upper()} RESPONSE ===\n{r.response or f'ERROR: {r.error}'}"
        for r in model_responses
    ])

    judge_prompt = f"""DATA CONTEXT:
{data_context}

ORIGINAL QUESTION:
{question}

MODEL RESPONSES TO EVALUATE:
{responses_text}

Evaluate these responses and return your JSON judgment."""

    t0 = time.time()
    raw_json = ""

    try:
        if judge_model == "claude":
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=_key("ANTHROPIC_API_KEY"))
            resp = await client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1200,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": judge_prompt}]
            )
            raw_json = resp.content[0].text

        elif judge_model == "openai":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=_key("OPENAI_API_KEY"))
            resp = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1200,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": judge_prompt}
                ]
            )
            raw_json = resp.choices[0].message.content

        elif judge_model == "gemini":
            import google.generativeai as genai
            import asyncio
            genai.configure(api_key=_key("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-pro", system_instruction=JUDGE_SYSTEM)
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, model.generate_content, judge_prompt)
            raw_json = resp.text

        parsed = _extract_json(raw_json)
        return JudgeResult(
            synthesis=parsed.get("synthesis", ""),
            key_agreements=parsed.get("key_agreements", []),
            key_disagreements=parsed.get("key_disagreements", []),
            confidence=parsed.get("confidence", "medium"),
            model_assessments=parsed.get("model_assessments", {}),
            recommended_answer=parsed.get("recommended_answer", "")
        )

    except Exception as e:
        return JudgeResult(
            synthesis=f"Judge evaluation failed: {str(e)}. Raw output: {raw_json[:200]}",
            key_agreements=[],
            key_disagreements=[],
            confidence="low",
            model_assessments={},
            recommended_answer=next(
                (r.response for r in model_responses if r.response), "No response available"
            )
        )
