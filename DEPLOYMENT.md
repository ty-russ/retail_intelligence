# Deploying Retail Insight to Hugging Face Spaces

A 10-minute walkthrough for the portfolio deployment. The hosted demo uses **BYO-key** — no preset API keys, visitors paste their own to exercise the AI features. The deterministic surfaces (KPIs, charts, narrator template, recommender template, suggester template) all work without any key.

## TL;DR

1. Make the repo public on GitHub.
2. Create an HF Space → Docker SDK → CPU basic (free).
3. Set the Space's git remote to your GitHub repo (or push the repo to the Space directly).
4. The included `Dockerfile`, `start.sh`, and `.dockerignore` do everything else.
5. After build, browse the public URL HF gives you.

No Space secrets are required.

---

## Step 1 — Prepare the repo

The deployment artefacts are already in `retail_insight/`:
- `Dockerfile` — Python 3.11-slim, runs both FastAPI and Streamlit in one container.
- `start.sh` — boots uvicorn on `127.0.0.1:8000`, then Streamlit on `0.0.0.0:7860` (HF's public port).
- `.dockerignore` — keeps the image lean (drops React client, notebooks, docs).

Make sure the data file is committed:
```
data/data.xlsx                              # required
data/processed/*.parquet                    # optional — speeds up cold start
```

The ingestion notebook is one-shot; pre-run it locally and commit the parquet files. The loader falls back to the raw Excel if parquet is missing.

## Step 2 — Add HF Spaces front-matter to README.md

HF Spaces parses YAML at the very top of `README.md`. Add (or replace) the existing top of `retail_insight/README.md` with:

```yaml
---
title: Order Cancellation Intelligence
emoji: 📦
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Analytical interface over a retail cancellation workbook, with multi-LLM investigation chat
---
```

Then continue with the existing README body. The `app_port: 7860` line is what tells HF which port to expose.

## Step 3 — Create the Space

1. Go to https://huggingface.co/new-space.
2. Owner = your username. Space name = `retail-insight` (or whatever).
3. SDK = **Docker**. License = MIT (or your preference).
4. Visibility = Public.
5. Hardware = **CPU basic — Free** (works fine for this workload).
6. Click Create.

## Step 4 — Push the repo

Two options.

**Option A — GitHub mirror.** In the Space settings, link the GitHub repo as the source. Every commit auto-rebuilds the Space.

**Option B — Direct push.** From the project root:

```bash
git remote add hf https://huggingface.co/spaces/<your-username>/retail-insight
git push hf main
```

Either way, the Space's Docker build kicks off automatically. First build takes ~4–6 minutes (pulls Python image, installs pandas / pyarrow / streamlit / plotly / openai / anthropic / google-generativeai). Subsequent builds use Docker layer caching, so dep changes are the only slow part.

## Step 5 — Visit the live URL

`https://huggingface.co/spaces/<your-username>/retail-insight` redirects to the running Streamlit app once the build is green.

The first cold start after deploy or after a period of inactivity takes ~15–25 seconds while the container wakes up.

## Cost guardrails — why BYO-key

The deployed Space ships with **no** Anthropic / OpenAI / Google keys. This means:

- **No ongoing cost to you.** If the Space gets shared on Twitter, you're not paying for strangers' LLM calls.
- **The AI chat is still demoable** — visitors who actually want to try the judge / multi-model flow paste their own keys in the sidebar.
- **The deterministic story stands.** Narrator / recommender / suggester all fall back to template responses, so the KPIs, charts, insights, and recommendations all render — just without LLM phrasing. That's actually a useful demo of the failsafe design.

If you want to enable AI features for casual visitors (no key required), you can add secrets in **Settings → Variables and secrets** of the Space:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`

Set a hard monthly cap on whichever provider you enable. Anthropic, OpenAI, and Google all support spending limits in their billing dashboards. With Claude Haiku at the default chat model, $10/month buys roughly 4,000 chat turns.

## What the visitor experience looks like

1. Visitor lands on the Space, sees the Overview tab loaded with deterministic KPIs.
2. They explore Where / Why / Products / Inventory / Data Quality — all fully functional. No AI calls.
3. On AI Insights:
   - Recommendations panel renders from the template recommender (still fact-grounded — narrator-style, just no LLM phrasing).
   - Suggestion chips render from the template suggester.
   - Chat input is visible. If they click Ask without a key, they get a clear error: *"No Anthropic API key configured. Paste your key in the sidebar to enable Claude."*
4. They expand the **🔑 Bring your own API key** section, paste a key (or three), and now the chat works live with their own quota.

## Troubleshooting

**Build fails with "No matching distribution found for pyarrow"** — HF's free CPU is amd64; if you're on Apple Silicon and built locally with arm64 wheels, force `--platform=linux/amd64` in `docker build`.

**Space starts but the page is blank** — usually `app_port` mismatch. Confirm the YAML in README.md has `app_port: 7860` and that `start.sh` runs Streamlit with `--server.port 7860 --server.address 0.0.0.0`.

**Chat returns the BYO-key error even though I pasted a key** — the key is per-session; if you refreshed the page, paste it again. (No localStorage by design — that would be a security regression.)

**Cold start feels slow** — HF free tier sleeps inactive Spaces. First hit after sleep takes 15–25s. You can keep it warm with an external uptime monitor pinging every 10 minutes, but that defeats the free tier.

**Image too large** — `.dockerignore` already excludes the React client, notebooks, and demo docs. If you want it smaller, switch the base image to `python:3.11-alpine` (will need extra build deps for pandas; not worth the savings for a portfolio piece).

## Portfolio link copy

For your portfolio page or LinkedIn:

> **Order Cancellation Intelligence** — An analytical interface over a retail cancellation workbook, with multi-LLM investigation chat (Claude / GPT-4o / Gemini in parallel, judge-model arbitration), fact-grounded recommendations, and full filter propagation across 23 endpoints. FastAPI + Streamlit + React. Validation discipline: numbers stay deterministic, only language is LLM-refined.
>
> [Live demo](https://huggingface.co/spaces/<your-username>/retail-insight) · [GitHub](https://github.com/<your-username>/retail-insight) · [Demo walkthrough](DEMO_SCRIPT.md)
