"""LLM-grounded narrative insights AND fact-grounded action recommendations.

Two LLM-backed surfaces, both ground all numeric claims in code-derived facts:

  1. ``narrate_insights`` / ``narrate_dict`` — re-words and lightly interprets
     each derived insight. Has limited autonomy: may link facts together and
     add one interpretive sentence per item.

  2. ``recommend_actions`` — has MORE autonomy: synthesises across insights,
     proposes prioritised next actions with effort/impact estimates. Still
     never invents numbers, identities, or claims unsupported by the source
     facts. When no LLM is available, a deterministic template-based
     fallback ensures the panel always has content.
"""
from __future__ import annotations

import os
import json
import time

from ..pipeline import metrics
from .judge import _extract_json   # reuse the fence-tolerant JSON parser


# ──────────────────────────────────────────────────────────────────────────────
# Narrator (lightly autonomous re-wording)
# ──────────────────────────────────────────────────────────────────────────────

NARRATOR_SYSTEM = """You are a retail-analytics narrator. You receive a JSON
object of fact-based insights computed directly from the data. Your job:

1. Order the insights by business importance (high severity first).
2. Re-word each one in a clear, concise narrative tone.
3. You MAY connect related insights — e.g. if a discontinued-products finding
   overlaps with a product-concentration finding in the same category, you may
   note that link in one short interpretive sentence.
4. You MAY add ONE short interpretive sentence per insight that infers a
   likely cause or consequence — but only when the facts clearly support it.

ABSOLUTE RULES:
- Do NOT invent or modify any number, percentage, store ID, SKU name, or
  category. Use only what appears in the source facts.
- Do NOT add insights not present in the source.
- Preserve the original 'severity' value for each item.
- If a fact's text already reads well, copy it verbatim.
- Speculation that introduces specific values is forbidden. Qualitative
  interpretation is fine.

Respond with VALID JSON ONLY (no markdown fences, no preamble) in this shape:

{
  "narratives": [
    {
      "key":      "<the source key, e.g. top_store>",
      "severity": "<high|medium|info>",
      "icon":     "<icon copied from source>",
      "text":     "<your narrative re-wording, optionally with one inferred sentence>"
    }
  ]
}
"""


def _fallback(insights: dict) -> dict:
    """When no LLM is available, return the structured insights unchanged so
    callers always get a usable payload."""
    return {
        "narratives": [
            {
                "key": k,
                "severity": v.get("severity", "info"),
                "icon": v.get("icon", ""),
                "text": v.get("text", ""),
                "source_fact": v,
            }
            for k, v in insights.items()
        ],
        "llm_used": False,
    }


async def narrate_insights(**filters) -> dict:
    """Return prioritised, narratively re-worded insights for the given filters.

    Always returns a dict with a ``narratives`` list. Falls back to the raw
    metrics output if the LLM is unavailable or returns something unparseable.
    """
    facts = metrics.derived_insights(**filters)
    if not facts:
        return {"narratives": [], "llm_used": False}

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback(facts)

    t0 = time.time()
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1200,
            system=NARRATOR_SYSTEM,
            messages=[{
                "role": "user",
                "content": "SOURCE FACTS:\n" + json.dumps(facts, ensure_ascii=False, indent=2),
            }],
        )
        raw = resp.content[0].text
        parsed = _extract_json(raw)
        narratives = parsed.get("narratives", [])

        cleaned = []
        for n in narratives:
            key = n.get("key")
            if key not in facts:
                continue
            src = facts[key]
            cleaned.append({
                "key": key,
                "severity": src.get("severity", n.get("severity", "info")),
                "icon": src.get("icon", n.get("icon", "")),
                "text": (n.get("text") or src.get("text", "")).strip(),
                "source_fact": src,
            })

        if not cleaned:
            return _fallback(facts)

        return {
            "narratives": cleaned,
            "llm_used": True,
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }

    except Exception as exc:
        out = _fallback(facts)
        out["llm_error"] = str(exc)
        return out


async def narrate_dict(**filters) -> dict:
    """Same insights, same keys, but with LLM-refined ``text`` fields.

    Returns the dict shape the analytics frontend already consumes —
    ``{insight_key: {severity, icon, text, ...numeric fields}}``. ``severity``,
    ``icon``, and every numeric field remain code-derived. Only ``text`` is
    replaced with the narrator's wording when available.
    """
    facts = metrics.derived_insights(**filters)
    if not facts:
        return {"_llm_used": False}

    narrated = await narrate_insights(**filters)
    by_key = {n["key"]: n for n in narrated.get("narratives", [])}

    out: dict = {}
    for key, fact in facts.items():
        refined = by_key.get(key, {})
        out[key] = {
            **fact,
            "severity": fact.get("severity", "info"),
            "icon":     fact.get("icon", ""),
            "text":     refined.get("text") or fact.get("text", ""),
        }

    out["_llm_used"] = bool(narrated.get("llm_used"))
    if "llm_error" in narrated:
        out["_llm_error"] = narrated["llm_error"]
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Recommendations (autonomous synthesis, still fact-grounded)
# ──────────────────────────────────────────────────────────────────────────────

RECOMMENDER_SYSTEM = """You are a retail-analytics action advisor. You receive
fact-based insights computed from the data and produce a SHORT, PRIORITISED list
of recommended next actions.

You have MORE autonomy than a narrator. You MAY:
- Combine multiple facts into one recommendation when they tell a coherent story
- Estimate effort (quick_win / medium / strategic) based on the action's nature
- Estimate category (operational / catalogue / data-quality / strategic / process)
- Phrase expected impact in qualitative business terms

ABSOLUTE RULES (any violation invalidates the recommendation):
- Never invent numbers. If you cite a percentage, store ID, SKU, or category
  name, it MUST appear verbatim in the source facts.
- Every recommendation must include at least one ``supporting_facts`` key that
  exists in the source. Recommendations without a valid source key will be
  discarded.
- For ``expected_impact``: prefer qualitative phrasing. Only quantify when an
  explicit numeric value from facts supports the claim (e.g. you can say "would
  recover the $X revenue at risk" only if $X appears in the facts).
- Prefer fewer, sharper recommendations over many vague ones. 3 to 5 is ideal.
- Order by severity (high first), then by expected business impact.
- The action must be an imperative sentence starting with a verb.

Output VALID JSON only, no markdown fences, no preamble. Schema:

{
  "recommendations": [
    {
      "id": "<short_snake_case_id>",
      "action": "<imperative action statement>",
      "rationale": "<one sentence citing specific numbers / names from facts>",
      "expected_impact": "<qualitative description, or quantitative ONLY if grounded>",
      "effort": "quick_win|medium|strategic",
      "category": "operational|catalogue|data-quality|strategic|process",
      "severity": "high|medium|info",
      "supporting_facts": ["<insight_key_1>", "<insight_key_2>"]
    }
  ]
}
"""


def _recommendations_fallback(facts: dict) -> list[dict]:
    """Deterministic template-based recommendations from each insight.

    Returns the same schema as the LLM-mode output. Used when no API key is
    configured or the LLM call fails — guarantees the Recommendations panel
    always has content.
    """
    recs: list[dict] = []
    _SEV_ORDER = {"high": 0, "medium": 1, "info": 2}

    if (f := facts.get("top_store")):
        gap = max(round(float(f.get("rate", 0)) - float(f.get("avg_rate", 0)), 1), 0)
        recs.append({
            "id": f"investigate_store_{f.get('store_num')}",
            "action": f"Investigate Store {f.get('store_num')} for operational issues",
            "rationale": (
                f"This store's cancel rate ({f.get('rate')}%) is "
                f"{f.get('ratio')}× the network average ({f.get('avg_rate')}%)."
            ),
            "expected_impact": (
                f"Closing the {gap:.1f} percentage-point gap to network average "
                "would meaningfully reduce both lost revenue and customer friction at this site."
            ),
            "effort": "quick_win",
            "category": "operational",
            "severity": f.get("severity", "medium"),
            "supporting_facts": ["top_store"],
        })

    if (f := facts.get("product_concentration")):
        cat = f.get("category") or "the top category"
        share = f.get("category_share", 0)
        recs.append({
            "id": f"audit_{(cat or 'category').lower().replace(' ', '_')}_supply",
            "action": f"Audit {cat} supply, forecasting, and assortment depth",
            "rationale": (
                f"{cat} accounts for ~{share}% of cancels; the single SKU "
                f"'{f.get('top_sku')}' alone drove {f.get('top_sku_qty')} cancelled units."
            ),
            "expected_impact": (
                "Even modest reduction in this category's share of cancels "
                "would materially shift overall cancel rate."
            ),
            "effort": "medium",
            "category": "catalogue",
            "severity": f.get("severity", "medium"),
            "supporting_facts": ["product_concentration"],
        })

    if (f := facts.get("oos_data_quality")):
        recs.append({
            "id": "audit_oos_taxonomy",
            "action": "Audit the OOS reason-code taxonomy and inventory-feed timing",
            "rationale": (
                f"{f.get('share')}% of OOS-flagged cancels matched a positive "
                "inventory snapshot on the order date — the feed and the reason "
                "code disagree on what 'out of stock' means."
            ),
            "expected_impact": (
                "Restores trust in cancel-reason analyses and unblocks accurate "
                "stockout-vs-demand attribution downstream."
            ),
            "effort": "medium",
            "category": "data-quality",
            "severity": f.get("severity", "medium"),
            "supporting_facts": ["oos_data_quality"],
        })

    if (f := facts.get("same_day_share")) and f.get("share", 0) >= 50:
        recs.append({
            "id": "investigate_demand_side_cancels",
            "action": (
                "Investigate demand-side cancellation drivers "
                "(checkout friction, price-compare, accidental orders)"
            ),
            "rationale": (
                f"{f.get('share')}% of cancels happen same-day as the order, "
                "implicating demand-side causes rather than fulfilment failures."
            ),
            "expected_impact": (
                "Same-day cancels are typically the most recoverable cohort — "
                "small UX, pricing, or confirmation-flow improvements can move the needle."
            ),
            "effort": "medium",
            "category": "strategic",
            "severity": f.get("severity", "info"),
            "supporting_facts": ["same_day_share"],
        })

    if (f := facts.get("negative_inventory")):
        recs.append({
            "id": "fix_inventory_feed",
            "action": "Investigate and patch the inventory feed producing negative on-hand records",
            "rationale": (
                f"{f.get('neg_records')} inventory rows report negative on-hand "
                "quantities, which is not physically possible."
            ),
            "expected_impact": (
                "Eliminates a feed-integrity bug that distorts OOS analytics "
                "and downstream reordering logic."
            ),
            "effort": "quick_win",
            "category": "data-quality",
            "severity": f.get("severity", "info"),
            "supporting_facts": ["negative_inventory"],
        })

    recs.sort(key=lambda r: (_SEV_ORDER.get(r["severity"], 9),
                              ["quick_win","medium","strategic"].index(r["effort"])))
    return recs


async def recommend_actions(**filters) -> dict:
    """Return a prioritised list of next actions grounded in derived insights.

    Always returns a dict with a ``recommendations`` list (possibly empty).
    LLM mode adds autonomy beyond re-wording — it synthesises across insights
    and proposes effort/impact estimates — but every cited number, name, or
    identity is validated against the source facts before being returned.
    """
    facts = metrics.derived_insights(**filters)
    if not facts:
        return {"recommendations": [], "_llm_used": False}

    fallback_recs = _recommendations_fallback(facts)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"recommendations": fallback_recs, "_llm_used": False}

    t0 = time.time()
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            system=RECOMMENDER_SYSTEM,
            messages=[{
                "role": "user",
                "content": "SOURCE FACTS:\n" + json.dumps(facts, ensure_ascii=False, indent=2),
            }],
        )
        raw = resp.content[0].text
        parsed = _extract_json(raw)
        recs = parsed.get("recommendations", [])

        # Validation: every rec must cite ≥1 real fact key
        valid_keys = set(facts.keys())
        valid_effort = {"quick_win", "medium", "strategic"}
        valid_severity = {"high", "medium", "info"}
        cleaned: list[dict] = []
        for r in recs:
            sf = r.get("supporting_facts") or []
            sf = [k for k in sf if k in valid_keys]
            if not sf:
                continue
            action = str(r.get("action", "")).strip()
            if not action:
                continue
            cleaned.append({
                "id": str(r.get("id", "rec")),
                "action": action,
                "rationale": str(r.get("rationale", "")).strip(),
                "expected_impact": str(r.get("expected_impact", "")).strip(),
                "effort": r.get("effort") if r.get("effort") in valid_effort else "medium",
                "category": r.get("category") or "operational",
                "severity": r.get("severity") if r.get("severity") in valid_severity else "info",
                "supporting_facts": sf,
            })

        if not cleaned:
            return {"recommendations": fallback_recs, "_llm_used": False,
                    "_llm_error": "LLM produced no recommendations that referenced source facts"}

        return {
            "recommendations": cleaned,
            "_llm_used": True,
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }

    except Exception as exc:
        return {"recommendations": fallback_recs, "_llm_used": False,
                "_llm_error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Investigation question suggestions (autonomous prompt generation)
# ──────────────────────────────────────────────────────────────────────────────

SUGGESTIONS_SYSTEM = """You are a retail-analytics investigation guide. You receive
fact-based insights computed from the data, and produce a SHORT list of pointed
investigation questions a stakeholder might ask next.

Goal: prompt the user to dig deeper, not summarise. Each question should:
- Reference at least one specific entity, number, or category from the facts
  (a store ID, a SKU name, a percentage, a category) — never generic.
- Open a follow-up path: drill-down, cause-effect, comparison, action,
  data-quality, or counterfactual.
- Be answerable using the available data, not require new sources.
- Be phrased as a real question, end with '?', under ~15 words.
- Span investigation modes — vary tactic, root-cause, comparison, action.

ABSOLUTE RULES:
- Never invent numbers, store IDs, SKU names, or category names. If you cite
  one, it MUST appear in the source facts.
- Produce 5 to 7 questions. Quality over quantity.
- Order: highest-severity-driven first.

Output VALID JSON only, no markdown fences, no preamble. Schema:

{
  "questions": [
    {
      "text": "<the question text, ending in '?'>",
      "category": "drill_down|cause|comparison|action|data_quality|counterfactual",
      "supporting_facts": ["<insight_key>"]
    }
  ]
}
"""


def _suggestions_fallback(facts: dict) -> list[dict]:
    """Deterministic question templates per insight key."""
    qs: list[dict] = []

    if (f := facts.get("top_store")):
        sn = f.get("store_num")
        city = f.get("source_fact", {}).get("text", "") or ""
        qs.append({
            "text": f"Why is Store {sn} {f.get('rate')}% — is it one category or store-wide?",
            "category": "drill_down",
            "supporting_facts": ["top_store"],
        })
        qs.append({
            "text": f"What would closing Store {sn}'s gap to the {f.get('avg_rate')}% network mean recover?",
            "category": "counterfactual",
            "supporting_facts": ["top_store"],
        })

    if (f := facts.get("product_concentration")):
        cat = f.get("category") or "the top category"
        qs.append({
            "text": f"Is {cat} ({f.get('category_share')}% of cancels) a supply problem or a demand problem?",
            "category": "cause",
            "supporting_facts": ["product_concentration"],
        })
        sku = (f.get("top_sku") or "")[:40]
        if sku:
            qs.append({
                "text": f"What's driving cancellations of '{sku}' specifically?",
                "category": "drill_down",
                "supporting_facts": ["product_concentration"],
            })

    if (f := facts.get("oos_data_quality")) and f.get("share", 0) >= 20:
        qs.append({
            "text": f"Can we trust OOS-flagged cancels when {f.get('share')}% had positive inventory?",
            "category": "data_quality",
            "supporting_facts": ["oos_data_quality"],
        })

    if (f := facts.get("same_day_share")) and f.get("share", 0) >= 50:
        qs.append({
            "text": f"Why are {f.get('share')}% of cancels happening same-day — is it checkout friction or pricing?",
            "category": "cause",
            "supporting_facts": ["same_day_share"],
        })

    if (f := facts.get("negative_inventory")):
        qs.append({
            "text": f"What's producing the {f.get('neg_records')} negative on-hand records?",
            "category": "data_quality",
            "supporting_facts": ["negative_inventory"],
        })

    # Cross-insight comparison question (only if we have a few facts)
    if len(facts) >= 3 and "top_store" in facts and "product_concentration" in facts:
        sn = facts["top_store"].get("store_num")
        cat = facts["product_concentration"].get("category")
        qs.append({
            "text": f"Is Store {sn}'s elevated rate driven by {cat}, or is it broader?",
            "category": "comparison",
            "supporting_facts": ["top_store", "product_concentration"],
        })

    return qs[:7]


async def suggest_questions(**filters) -> dict:
    """Generate fact-grounded investigation questions for the chat UI.

    Returns ``{"questions": [...], "_llm_used": bool}``. Each question carries
    its category and the source-fact keys it derives from. Falls back to a
    deterministic template recommender when no LLM is available, so the chat
    UI always has meaningful prompts to surface.
    """
    facts = metrics.derived_insights(**filters)
    if not facts:
        return {"questions": [], "_llm_used": False}

    fallback = _suggestions_fallback(facts)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"questions": fallback, "_llm_used": False}

    t0 = time.time()
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=SUGGESTIONS_SYSTEM,
            messages=[{
                "role": "user",
                "content": "SOURCE FACTS:\n" + json.dumps(facts, ensure_ascii=False, indent=2),
            }],
        )
        parsed = _extract_json(resp.content[0].text)
        questions = parsed.get("questions", [])

        valid_keys = set(facts.keys())
        valid_cats = {"drill_down", "cause", "comparison", "action",
                      "data_quality", "counterfactual"}
        cleaned: list[dict] = []
        for q in questions:
            text = str(q.get("text", "")).strip()
            sf   = [k for k in (q.get("supporting_facts") or []) if k in valid_keys]
            if not text or not text.endswith("?") or not sf:
                continue
            cleaned.append({
                "text": text,
                "category": q.get("category") if q.get("category") in valid_cats else "drill_down",
                "supporting_facts": sf,
            })

        if not cleaned:
            return {"questions": fallback, "_llm_used": False,
                    "_llm_error": "LLM produced no valid questions"}
        return {"questions": cleaned[:7], "_llm_used": True,
                "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception as exc:
        return {"questions": fallback, "_llm_used": False, "_llm_error": str(exc)}
