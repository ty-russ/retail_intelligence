# Retail Insight — Order Cancellation Intelligence

An investigative analytics tool that turns a retail cancellation workbook into a navigable, filter-aware experience with five LLM-backed AI surfaces. Built for the AI Applications Analyst presentation brief — the brief explicitly asks for an *analytical interface* over a traditional BI dashboard, with first-class use of AI tools and a clear story for how AI outputs are validated.

The stack is FastAPI + Streamlit + React. The same backend serves both frontends.

> **Quick orientation.** The headline finding from this dataset is that **14.5% of cancellations are for products that have since been discontinued** — a catalogue-hygiene problem that a standard cancellation dashboard wouldn't surface. The "Products → Lifecycle" section in either UI reveals this.

---

## What's inside

**Two analytical UIs over the same backend.** A Streamlit surface (`streamlit_app/app.py`) and a React surface (`react_client/`) both consume the FastAPI backend. Pick the one you prefer for the walkthrough; both share the same filter state semantics, the same code-derived insights, the same severity colouring.

**Seven investigation tabs**, each filterable from a sidebar:

1. **Overview** — KPIs, a risk dashboard, weekly trend (units + revenue at risk), day-of-week pattern, top cancel reasons, headline insights.
2. **Where** — US state choropleth (Streamlit) / state table (React), store-level cancel rates colour-coded by severity, regional rollup.
3. **Why** — sub-reasons grouped by parent reason, lag distribution (order → cancel), reason × day-of-week heatmap.
4. **Products** — top SKUs (toggle between cancelled units vs revenue at risk), category treemap, **product lifecycle analysis** flagging discontinued and new-launch SKUs that are still being cancelled.
5. **Inventory** — bucket distribution of on-hand levels at order day, stockout rate by store (true rate, not raw count).
6. **Data Quality** — severity-scored scorecard of integrity findings (negative-inventory records, cancels with no matching inventory snapshot, missing sub-reasons, products with missing brand/name, etc.).
7. **AI Insights** — fact-grounded recommendations, multi-LLM investigation chat with judge-model arbitration, dynamic suggestion prompts.

**Five AI-backed runtime surfaces** (all behind the same FastAPI backend):

- Multi-LLM chat (`/api/insights/query`) — Claude, GPT-4o, and Gemini in parallel via `asyncio.gather`.
- Judge (`backend/ai/judge.py`) — separate LLM call that evaluates the multi-model responses against the data context, returns confidence + per-model scores + a synthesised recommended answer.
- Narrator (`/api/insights/narrative`, embedded in `/api/analytics/insights`) — re-words code-derived insights with strict no-invention constraints. Severity, icon, and numbers are pulled from code; only the text is LLM-refined.
- Recommender (`/api/insights/recommendations`) — synthesises prioritised next actions from the insights. Validation gates discard any rec that doesn't cite a real `supporting_facts` key.
- Suggestion generator (`/api/insights/suggestions`) — produces dynamic, fact-citing investigation prompts that populate (not auto-submit) the chat input.

**Every AI surface has a deterministic template fallback**, so the application works end-to-end with zero LLM calls. See `AI_USAGE.md` for the full validation story.

---

## Architecture

```
retail_insight/
├── AI_USAGE.md              # How AI was used + validated (a brief deliverable)
├── README.md                # This file
├── requirements.txt
├── .env.example
├── data/
│   └── data.xlsx            # The source workbook
├── notebooks/
│   └── data_ingestion.ipynb # One-shot ingestion to parquet (data/processed/)
├── backend/                 # FastAPI API server
│   ├── main.py              # App entry, CORS, router registration
│   ├── pipeline/
│   │   ├── loader.py        # Cached Excel/parquet load + enrichment
│   │   └── metrics.py       # KPIs, breakdowns, derived_insights, data quality
│   ├── ai/
│   │   ├── agents.py        # Claude/OpenAI/Gemini async agents + history coercion
│   │   ├── judge.py         # Judge model + fence-tolerant JSON extractor
│   │   ├── narrator.py      # Narrator, Recommender, Suggester
│   │   └── orchestrator.py  # Routes single vs multi-model, triggers judge
│   ├── routers/
│   │   ├── analytics.py     # 17 analytics endpoints
│   │   └── insights.py      # AI query + narrative + recommendations + suggestions
│   └── models/
│       └── schemas.py       # Pydantic schemas (InsightRequest, AIConfig, etc.)
├── streamlit_app/
│   └── app.py               # 7-tab Streamlit UI with cached api_get
└── react_client/            # Vite + React 18 frontend
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx          # 7 tabs, filter bar, severity-driven rendering
        ├── theme.js         # Design tokens shared across components
        ├── api/client.js    # Cached fetch wrapper
        └── components/
            ├── FilterBar.jsx        # Collapsible filter sidebar
            ├── InsightCard.jsx      # Severity-coloured insight card
            ├── RecommendationCard.jsx
            └── ModelConfig.jsx      # AI mode/model/judge UI + badges
```

---

## Setup

### 1. Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

Or export directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export GOOGLE_API_KEY=AIza...
```

Any single key is sufficient. Models without a configured key surface an error message in the multi-model chat but don't crash. The narrator, recommender, and suggester all fall back to deterministic templates when no key is present — the app remains fully functional.

---

## Running

### Backend (required first)

```bash
cd retail_insight
uvicorn backend.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Streamlit UI

```bash
cd retail_insight
streamlit run streamlit_app/app.py
```

Opens at: http://localhost:8501

### React UI

```bash
cd retail_insight/react_client
npm install
npm run dev
```

Opens at: http://localhost:3000

---

## API Reference

### Analytics (GET)

| Endpoint | Description |
|----------|-------------|
| `/api/analytics/filters` | Available filter options (stores, reasons, date range) |
| `/api/analytics/overview` | Headline KPIs (orders, cancels, rates, revenue at risk) |
| `/api/analytics/trends/weekly` | Weekly cancel trend (units + revenue) |
| `/api/analytics/trends/dow` | Day-of-week pattern |
| `/api/analytics/stores` | Store-level cancel rates |
| `/api/analytics/regions` | Regional breakdown |
| `/api/analytics/states` | Per-state cancel rate (US choropleth) |
| `/api/analytics/reasons` | Cancel reason breakdown |
| `/api/analytics/reasons/sub` | Sub-reason breakdown (with parent reason joined) |
| `/api/analytics/cancels/lag` | Order-to-cancel lag distribution |
| `/api/analytics/heatmap/reason-dow` | Reason × day-of-week heatmap data |
| `/api/analytics/products` | Top cancelled products (param: `sort_by=qty\|amt`) |
| `/api/analytics/products/status` | Lifecycle breakdown: discontinued / new launch / established |
| `/api/analytics/categories` | Department × category breakdown |
| `/api/analytics/inventory` | Inventory bucket distribution + stockout-by-store |
| `/api/analytics/data-quality` | Severity-scored integrity checks |
| `/api/analytics/insights` | Code-derived insights with LLM-refined text |

All analytics endpoints accept the same query params: `stores`, `regions`, `date_from`, `date_to`, `reasons`.

### AI Insights (GET / POST)

| Endpoint | Description |
|----------|-------------|
| `/api/insights/models` | Which AI providers are configured |
| `/api/insights/narrative` | LLM-narrated insights, list-shape |
| `/api/insights/recommendations` | Fact-grounded next actions (LLM or template) |
| `/api/insights/suggestions` | Dynamic investigation question prompts |
| `POST /api/insights/query` | Multi-LLM chat with optional judge |

### `POST /api/insights/query` payload

```json
{
  "question": "Which store has the highest cancel rate?",
  "history": [],
  "ai_config": {
    "mode": "single",
    "model": "claude",
    "models": ["claude", "openai", "gemini"],
    "enable_judge": false,
    "judge_model": "claude"
  },
  "filters": {}
}
```

---

## AI orchestration modes

**Single model.** One model, lowest latency. Pick Claude / GPT-4o / Gemini.

**Multi-model (no judge).** Same question to multiple models in parallel via `asyncio.gather`. Returns the first successful response as the final answer; all model responses surface in the UI for side-by-side comparison.

**Multi-model with judge.** The question goes to N models in parallel; a separate judge call receives the original question, the data context, and all model responses; the judge returns a structured JSON evaluation with synthesis, agreements, disagreements, confidence (high/medium/low), per-model scoring, and a recommended answer. See `backend/ai/judge.py`.

---

## Filter propagation

The sidebar filter set (stores, regions, dates, reasons) is the source of truth. Every chart, every insight, every recommendation, and every suggestion re-fetches when filters change. Both UIs cache GET responses for 120 seconds keyed on `(path, sorted-params)` so a sidebar interaction doesn't trigger 17 round-trips on every rerun.

---

## Key findings from the data (Feb – Jun 2024, 15 stores, 174 products, 59k orders, 8.2k cancels)

- Overall cancel rate: **~5.7% by units**, ~6% by revenue
- **Store 1426 (Alpine, IL): 9.5%** — 1.93× the network average of 4.92%
- **Region 8 (Illinois): 6.2%** cancel rate — highest of the four regions
- **NON FLAVORED WATER: ~54%** of all cancelled units
- Single SKU **"Purified Drinking Water, 16.9 fl oz, 40 Count" drove 4,062 cancelled units** alone
- **71% of cancellations happen same-day** as the order — demand-side signal
- **OOS data-quality finding: 94% of OOS-flagged cancels matched a positive inventory snapshot** on the order date — the OOS reason code disagrees with the inventory feed
- **954 inventory rows show negative on-hand quantities** — feed-integrity bug
- **54% of cancels are missing a sub-reason code** — coarser root-cause available
- **14.5% of cancels (2,069 units) are for products since marked discontinued** — top three are all water SKUs

---

## Data limitations (acknowledged up-front)

- **Inventory has date granularity only.** Same-day cancels after a SKU sells through may still appear matched to a positive reading.
- **`ACTIVE_STATUS` is a snapshot at extract time**, not historical. "Discontinued" means "since discontinued."
- **No customer identifier** — no repeat-customer analysis.
- **`UNIT_COST` is static** — no price-history.
- **Product table has a few duplicate `ITEM_ID` rows** — handled via `drop_duplicates("ITEM_ID")` and surfaced in the Data Quality tab.

---

## AI usage

See **`AI_USAGE.md`** for the full validation story. Short version: numbers, identities, and severity stay in deterministic Python; the LLM only ever phrases, prioritises, or synthesises. Validation gates and a deterministic fallback ensure the app degrades gracefully.

---

## Deploying to Streamlit Cloud

1. Push the repo to GitHub.
2. Go to share.streamlit.io.
3. Set main file path to: `streamlit_app/app.py`.
4. Add secrets: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`.
5. Deploy the FastAPI backend separately (Railway, Render, Fly.io) and update `API_BASE` in `streamlit_app/app.py` to point at the deployed URL.

For the React client, build with `npm run build` and serve the `dist/` folder behind any static host. Set `VITE_API_BASE` to your backend URL.
