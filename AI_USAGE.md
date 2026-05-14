# AI Usage Summary

This document explains how AI tools were used to build the *Order Cancellation Intelligence* application and how AI is used at runtime. The brief asks for either a prompt log, annotated examples, or a concise written explanation — what follows is a written summary with annotated examples of the live prompts that ship in the codebase, plus a few notes on where I deliberately did *not* trust AI.

## TL;DR

AI shows up in two places: as a coding assistant during development, and as a first-class runtime component inside the app (multi-LLM chat, a judge model, a narrator that re-words insights, a recommender, and a suggestion generator). In both contexts, the principle was the same: **AI is allowed to phrase, prioritise, and synthesise — never to invent or alter numbers**. Every numeric claim, severity rating, store ID, SKU name, and category in the application is computed in deterministic Python from the workbook. The LLM tier only ever sees the structured facts and re-words them. Validation logic discards any LLM output that fails to cite a real source key, and a deterministic fallback ensures the app degrades gracefully when no API key is available.

---

## 1. Where AI is used in the runtime

The application has five LLM-backed surfaces, all behind a FastAPI backend:

**`/api/insights/query` — Multi-LLM Chat.** The "AI Insights" tab runs the user's question through one model (Claude, GPT-4o, or Gemini), or through several in parallel via `asyncio.gather`. Three providers, three SDKs, one async interface. Lives in `backend/ai/agents.py`.

**Judge model.** When multi-model mode is on with the Judge toggle enabled, all model responses are fed to a separate judge call (configurable: Claude / GPT-4o / Gemini) that returns a structured JSON evaluation with confidence level, per-model scores, agreements, disagreements, and a synthesised recommended answer. Lives in `backend/ai/judge.py`. Includes a fence-tolerant JSON extractor (`_extract_json`) because real-world models routinely return JSON wrapped in markdown code fences despite being asked not to.

**`/api/analytics/insights` — Code-derived insights with LLM-refined text.** The route calls `metrics.derived_insights()` (pure Python — computes severity, picks the top store, etc.) and pipes those facts through the *narrator* (`backend/ai/narrator.py::narrate_dict`). The dict shape is preserved so the existing frontend continues to work; only the `text` field of each insight is replaced with the LLM's wording. Numbers and severity stay code-derived.

**`/api/insights/recommendations` — Fact-grounded next actions.** The *recommender* takes the same insights and produces a prioritised list of actions with `effort` and `category` estimates. The LLM has more autonomy here — it can combine insights into a single recommendation, estimate effort, and phrase business impact — but the same no-invention rule applies, and the validation logic discards any recommendation that doesn't cite a real `supporting_facts` key.

**`/api/insights/suggestions` — Investigation-question generator.** Produces dynamic, fact-citing prompts for the chat UI ("Why is Store 1426 9.5% — is it one category or store-wide?"). The frontend clicks populate the input field rather than auto-submitting, so the user can refine before sending.

Every surface has a deterministic template fallback. If no API key is present, the recommender returns hand-written templates filled with the actual numeric facts; the suggester returns curated investigation prompts; the narrator returns the raw text. **The application works end-to-end with zero LLM calls** — the LLM tier is a quality enhancement, not a hard dependency.

---

## 2. The validation story (the part the brief is scoring)

The interesting bit is not "we used AI" — every project uses AI now — it's the validation layer that makes AI outputs trustworthy in a production setting.

### Code-derived numbers, LLM-rephrased text

The narrator's prompt is explicit:

> **ABSOLUTE RULES:**
> - Do NOT invent or modify any number, percentage, store ID, SKU name, or category. Use only what appears in the source facts.
> - Do NOT add insights not present in the source.
> - Preserve the original 'severity' value for each item.
> - If a fact's text already reads well, copy it verbatim.
> - Speculation that introduces specific values is forbidden. Qualitative interpretation is fine.

The structural defence is more interesting than the prompt rules though. In `narrate_dict`, after the LLM returns its JSON, the merge step is:

```python
out[key] = {
    **fact,                                       # all numeric + meta fields
    "severity": fact.get("severity", "info"),     # always from code
    "icon":     fact.get("icon", ""),             # always from code
    "text":     refined.get("text") or fact.get("text", ""),  # LLM-refined if present
}
```

The LLM cannot alter severity or icon even if it tries — those are overwritten from the source `fact`. The only thing the LLM is allowed to write is `text`. This is *structural* validation, not prompt-trust.

### Reference-only recommendations

The recommender's validation is similar but stricter. Every recommendation must include a `supporting_facts` list that names at least one valid insight key:

```python
valid_keys = set(facts.keys())
cleaned: list[dict] = []
for r in recs:
    sf = [k for k in (r.get("supporting_facts") or []) if k in valid_keys]
    if not sf:
        continue                # silently dropped — no valid source means it's discarded
    ...
```

If the LLM hallucinates a key like `"top_brand"` (we don't have one), the rec is filtered out. If all recs get filtered, we fall back to the deterministic template. The frontend can also display a "Source: LLM-synthesised" vs "Source: Deterministic fallback" caption so a stakeholder sees which path produced the content.

### Fence-tolerant JSON parsing

Models routinely violate "respond with JSON only" by wrapping output in ` ```json … ``` ` fences, by prepending preamble like "Sure, here is my evaluation:", or by including trailing prose. The `_extract_json` helper in `judge.py` tries three parsing strategies in order — direct `json.loads`, fenced-block extraction via regex, balanced-brace extraction (with proper string-escape handling for `{` or `}` characters inside string values). All three pieces fail clean and the surrounding code catches the exception and falls back, so a malformed model response degrades gracefully instead of crashing the chat.

### Allowlists on categorical values

Effort, category, and severity are pulled from a fixed allowlist:

```python
valid_effort = {"quick_win", "medium", "strategic"}
valid_severity = {"high", "medium", "info"}
...
"effort": r.get("effort") if r.get("effort") in valid_effort else "medium",
```

A model returning `"effort": "tomorrow"` gets coerced to `"medium"`. The frontend can rely on these values matching its colour map.

### Multi-LLM judge as a consensus check

When the user enables the Judge toggle, the same question goes to 2–3 models in parallel; the judge then evaluates each response against the data context, calls out disagreements, and synthesises a final answer. The judge prompt explicitly instructs the judge to flag any factual errors against the provided data context. This is a different kind of validation — instead of constraining a single model's output, it surfaces disagreement when models diverge on a factual claim, so the user knows when to be sceptical.

### Acknowledging the limits

A few things the validation cannot catch:

- **The LLM may still soften or sharpen tone** beyond what the facts strictly support. The "one short interpretive sentence" allowance is deliberate but unverifiable.
- **The LLM may pick a sub-optimal ordering of recommendations.** The validation only ensures every recommendation is fact-grounded — not that the top one is the most important.
- **Deterministic fallback wording is fine but vanilla.** If a stakeholder reads it, they're seeing template English. The LLM path produces noticeably better narrative tone.

These are acknowledged trade-offs, not bugs.

---

## 3. How AI helped build the project

I leaned on AI heavily during development, primarily for:

**Boilerplate generation.** FastAPI route stubs, Pydantic models, Streamlit layout scaffolding, React component skeletons. Anything that follows a known pattern — the AI is faster than I am at typing it, I'm faster at reviewing it. The validation here was simple: does the code do what I asked, do the tests pass, does the request flow through correctly?

**Plotly / Streamlit configuration help.** Picking the right `update_layout` arguments, debugging `px.choropleth` USA-states behaviour, getting a heatmap's `color_continuous_scale` to look right. These are areas where I know what I want visually but don't remember the exact API surface. The AI suggested options, I picked, I verified visually.

**React patterns I don't use daily.** Things like the session-state pre-fill pattern for populating a form input without auto-submitting (`pending_input` → effect hydrates `chat_input` before the widget renders). I had a vague memory this was tricky in Streamlit; the AI gave me the exact pattern; I verified by checking what triggered a rerun vs what didn't.

**Architectural sounding board.** When I was deciding whether to (a) hardcode insights in the frontend, (b) derive them in the backend with no LLM, or (c) derive them in the backend then narrate via LLM — I talked it through with the AI. The conclusion (option c, with structural validation gates) was mine; the AI was useful for surfacing the trade-offs I might have missed.

**Iterative prompt refinement.** The narrator system prompt went through ~4 revisions. The first version was too permissive ("re-word for clarity") and produced LLM responses that sometimes invented small numbers. The second version added the "no invention" rules but was still missing the explicit examples. The current version (in `backend/ai/narrator.py:29-61`) is the result of seeing where the model still drifted in testing and tightening the constraints. The recommender prompt went through similar refinement — the validation step in code was added *after* I noticed the model occasionally returning recommendations with no `supporting_facts` at all.

---

## 4. Where I deliberately did *not* trust AI

Equally important — the things I verified by hand rather than accepting AI output:

**Final analytical findings before presenting them.** Every number that appears in this AI_USAGE document or the brief response was cross-checked against the actual workbook. The "14.5% of cancels are for products since discontinued" finding was found by AI, but I verified it manually by joining `Cancels` to `Product` and counting before quoting it.

**Domain-specific assumptions.** When the AI suggested treating `REGION` as a string vs integer, treating `STATE` codes as ISO-3166 vs USPS, or how to interpret the `ACTIVE_STATUS` codes ('A' vs 'D'), I verified against the source data rather than accepting the inference. The "discontinued products" angle existed only because I noticed the `ACTIVE_STATUS` column directly — the AI hadn't surfaced it as worth investigating until I pointed it at the column.

**The OOS-paradox framing.** The AI initially over-claimed the OOS reason code as "definitely mis-coded." I pushed back on this once I noticed the inventory feed has date-only granularity — a same-day cancel after an inventory snapshot could legitimately be a real stockout. The OOS-paradox finding is now framed as a *feed-consistency* signal rather than proof of mis-coding, in both the prompt scaffolding and the UI captions.

**The stockout-by-store bug.** The AI's first implementation of zero-inventory frequency counted *any* day where *any* SKU at the store was at zero, which produced near-identical counts (~143 days) for every store. I caught this by looking at the actual chart and noticing all bars were the same height. The fix (normalize by total snapshots to get a true *rate*) was AI-suggested, but the bug detection was mine.

**The chart-title audit.** I asked the AI to add titles to charts; I then went chart-by-chart in the running app to confirm the titles actually displayed correctly. Two were sitting outside the visible area initially because of a Plotly margin bug.

---

## 5. Annotated prompt examples (the actual production prompts)

### Narrator (`narrator.py` — `NARRATOR_SYSTEM`)

```text
You are a retail-analytics narrator. You receive a JSON object of fact-based
insights computed directly from the data. Your job:

1. Order the insights by business importance (high severity first).
2. Re-word each one in a clear, concise narrative tone.
3. You MAY connect related insights — e.g. if a discontinued-products finding
   overlaps with a product-concentration finding in the same category, you may
   note that link in one short interpretive sentence.
4. You MAY add ONE short interpretive sentence per insight that infers a likely
   cause or consequence — but only when the facts clearly support it.

ABSOLUTE RULES:
- Do NOT invent or modify any number, percentage, store ID, SKU name, or
  category. Use only what appears in the source facts.
- Do NOT add insights not present in the source.
- Preserve the original 'severity' value for each item.
- If a fact's text already reads well, copy it verbatim.
- Speculation that introduces specific values is forbidden. Qualitative
  interpretation is fine.

Respond with VALID JSON ONLY (no markdown fences, no preamble) ...
```

Why each rule exists:
- *"Order the insights by business importance"* — gives the LLM creative latitude over what to surface first, which is genuinely a judgment call.
- *"You MAY connect related insights"* — small autonomy bump so the output reads less mechanical.
- *"You MAY add ONE short interpretive sentence per insight … but only when the facts clearly support it"* — explicitly bounds the speculation. The "but only when" qualifier is load-bearing.
- *"Do NOT invent or modify any number, percentage, store ID, SKU name, or category"* — the core no-hallucination rule. Listed specifics because abstract phrasing ("don't make stuff up") was not sufficient in early testing.
- *"Preserve the original 'severity' value"* — backstopped by the structural merge that overwrites this field anyway, but the prompt makes the contract explicit.

### Recommender (`narrator.py` — `RECOMMENDER_SYSTEM`)

The recommender gets *more* autonomy than the narrator (it can combine facts, estimate effort, propose business impact) but the same no-invention rule applies. The validation step in code is the real guarantee — every returned recommendation is filtered against `valid_keys = set(facts.keys())`. The full prompt is in `backend/ai/narrator.py:177-218`.

### Suggestion generator (`narrator.py` — `SUGGESTIONS_SYSTEM`)

```text
Goal: prompt the user to dig deeper, not summarise. Each question should:
- Reference at least one specific entity, number, or category from the facts
  (a store ID, a SKU name, a percentage, a category) — never generic.
- Open a follow-up path: drill-down, cause-effect, comparison, action,
  data-quality, or counterfactual.
- Be answerable using the available data, not require new sources.
- Be phrased as a real question, end with '?', under ~15 words.
- Span investigation modes — vary tactic, root-cause, comparison, action.
```

Why the specific constraints:
- *"Never generic"* — early versions produced "What should we do?" type questions that the chat surface already had hardcoded. The "specific entity" rule forces the LLM to anchor to a fact.
- *"Be answerable using the available data"* — prevents prompts like "What are competitor cancellation rates?" that would frustrate the user when the chat couldn't answer.
- *"Under ~15 words"* — UI constraint; longer questions wrap awkwardly in the suggestion buttons.

### Judge (`judge.py` — `JUDGE_SYSTEM`)

```text
You are an expert AI judge evaluating multiple AI model responses to a retail
analytics question.

Your task:
1. Evaluate each model's response for accuracy, completeness, and actionability
2. Identify where models agree and where they disagree
3. Flag any factual errors against the provided data context
4. Synthesize the best possible final answer
```

The judge is a separate model call rather than a code rule because it has to do something genuinely hard — *evaluate consistency* across responses. The validation here is structural: the judge's output is parsed via `_extract_json` and any malformed output falls back to "judge evaluation failed" with the most informative model response surfaced as the recommended answer.

---

## 6. What this approach is not

It's worth being explicit about what this design does *not* claim:

- **It doesn't claim the LLM is correct.** It claims the LLM cannot fabricate numbers and cannot reference non-existent insights, because those guarantees come from code, not from the model.
- **It doesn't claim the narrator's wording is always better than the deterministic template.** It claims the narrator produces nicer-reading versions of the *same facts*. The user can see which one they got via the provenance caption.
- **It doesn't replace human review.** A stakeholder reading the Recommendations panel should still ask "do these actions make sense?" — the system surfaces them, the human decides whether to act.
- **It is not a closed system.** When the LLM is genuinely smarter than the templates — better wording, better prioritisation, better cross-fact synthesis — the user benefits. When the LLM is wrong or unavailable, the templates take over. The user always gets *something*.

---

## 7. Summary

The interesting AI choice in this project wasn't *which model to use* — it was *what to let the model decide*. Numbers, identities, severity, and structural fields are computed in Python. Tone, ordering, and synthesis are delegated to the LLM. Code-level validation gates ensure the LLM cannot violate the boundary even when it tries. Deterministic fallbacks ensure the app degrades to a known-good state without external dependencies. The result is an AI-augmented application where the AI can improve the experience but cannot break the analysis.
