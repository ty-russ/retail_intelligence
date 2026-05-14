import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import date

API_BASE = "http://localhost:8000"

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Order Cancellation Intelligence | Retail Insight",
    page_icon="📦", layout="wide", initial_sidebar_state="expanded"
)

RI_BLUE  = "#1B3A6B"
RI_TEAL  = "#00A8E0"
RI_RED   = "#E63946"
RI_AMBER = "#F4A261"
RI_GREEN = "#2A9D8F"

# Custom CSS — Inter font, larger base sizes, better tabs and cards
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

  /* Base typography */
  html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
  }
  [data-testid="stAppViewContainer"] { background: #F7F9FC; font-size: 16px; }
  [data-testid="stMain"] .stMarkdown p { font-size: 0.95rem; line-height: 1.6; color: #2C3E50; }
  [data-testid="stMain"] h1 {
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
    font-size: 2.1rem !important; font-weight: 800; letter-spacing: -0.02em;
    margin-bottom: 4px; color: #1B3A6B;
  }
  [data-testid="stMain"] h2, [data-testid="stMain"] h3 {
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
    letter-spacing: -0.01em; color: #1B3A6B;
  }

  /* Sidebar — kept collapsible (use the chevron in the top-right of the sidebar) */
  [data-testid="stSidebar"] { background: #1B3A6B; }
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3,
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
  [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #FFFFFF !important;
  }
  [data-testid="stSidebar"] label { font-size: 0.92rem !important; font-weight: 500; }
  [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea {
    color: #1B3A6B !important; background-color: #FFFFFF !important;
    caret-color: #1B3A6B !important; font-size: 0.95rem !important;
  }
  [data-testid="stSidebar"] input::placeholder { color: #8A9BB4 !important; opacity: 1; }
  [data-testid="stSidebar"] [data-baseweb="input"],
  [data-testid="stSidebar"] [data-baseweb="select"] > div:first-child {
    background-color: #FFFFFF !important; border-radius: 8px !important;
    border: 1px solid #C8D8E8 !important;
  }
  [data-testid="stSidebar"] [data-baseweb="input"] svg,
  [data-testid="stSidebar"] [data-baseweb="select"] svg {
    fill: #1B3A6B !important; color: #1B3A6B !important;
  }
  [data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #00A8E0 !important; border-color: #00A8E0 !important;
  }
  [data-testid="stSidebar"] [data-baseweb="tag"] * { color: #FFFFFF !important; }
  [data-testid="stSidebar"] [data-baseweb="select"] input,
  [data-testid="stSidebar"] [data-baseweb="select"] div[role="combobox"] { color: #1B3A6B !important; }
  /* Make the sidebar collapse arrow more visible */
  [data-testid="stSidebarCollapseButton"] button { color: white !important; }

  /* Calendar popover */
  div[data-baseweb="calendar"], div[data-baseweb="calendar"] * {
    color: #1B3A6B !important; background-color: #FFFFFF;
  }
  div[data-baseweb="calendar"] [aria-selected="true"] {
    background-color: #1B3A6B !important; color: #FFFFFF !important;
  }

  /* Tabs */
  [data-testid="stTabs"] [role="tablist"] {
    gap: 4px; border-bottom: 1px solid #E2EAF4; margin-bottom: 12px;
  }
  [data-testid="stTabs"] [role="tab"] {
    font-size: 0.98rem !important; font-weight: 600 !important; padding: 12px 20px !important;
    color: #6C7B8B !important; background: transparent !important; border-radius: 8px 8px 0 0;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #1B3A6B !important; background: white !important;
    box-shadow: inset 0 -3px 0 #00A8E0;
  }
  [data-testid="stTabs"] [role="tab"]:hover { background: #EEF6FB !important; }

  /* Section headers — bigger and stronger */
  .section-header {
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
    font-size: 1.45rem; font-weight: 700; color: #1B3A6B;
    margin: 28px 0 14px; letter-spacing: -0.01em;
    border-bottom: 2px solid #00A8E0; padding-bottom: 8px;
  }

  /* KPI cards */
  .metric-card {
    background: white; border-radius: 14px; padding: 22px 26px;
    border-left: 5px solid #00A8E0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.06);
  }
  .metric-value {
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
    font-size: 2.2rem; font-weight: 700; color: #1B3A6B; line-height: 1.1;
    letter-spacing: -0.02em;
  }
  .metric-label { font-size: 0.88rem; color: #6C7B8B; margin-top: 4px; font-weight: 500; }

  /* Insight + warning boxes — more padding, bigger text */
  .insight-box {
    background: #EEF6FB; border-left: 4px solid #00A8E0;
    border-radius: 10px; padding: 16px 20px; margin: 12px 0;
    font-size: 0.95rem; color: #1B3A6B; line-height: 1.6;
  }
  .warning-box {
    background: #FFF3F3; border-left: 4px solid #E63946;
    border-radius: 10px; padding: 16px 20px; margin: 12px 0;
    font-size: 0.95rem; color: #7A1A1A; line-height: 1.6;
  }

  /* Buttons */
  .stButton > button {
    font-family: 'Inter', sans-serif !important;
    font-weight: 500; border-radius: 8px;
    border: 1px solid #C8D8E8; padding: 8px 16px;
    font-size: 0.92rem; transition: all 0.12s ease;
  }
  .stButton > button:hover {
    border-color: #00A8E0; background: #F0F8FC; color: #1B3A6B;
  }
  .stFormSubmitButton > button {
    background: #1B3A6B !important; color: white !important;
    border-color: #1B3A6B !important; font-weight: 600;
  }
  .stFormSubmitButton > button:hover {
    background: #00A8E0 !important; border-color: #00A8E0 !important;
  }

  /* Main chat input field */
  [data-testid="stMain"] .stTextInput input, [data-testid="stMain"] .stTextArea textarea {
    font-size: 0.96rem !important; padding: 12px 14px !important; border-radius: 10px !important;
  }

  /* Dataframe + table styling */
  [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }

  /* Model badge + judge box (kept) */
  .model-badge {
    display: inline-block; padding: 3px 10px; border-radius: 12px;
    font-size: 0.8rem; font-weight: 600; margin: 2px;
  }
  .judge-box {
    background: linear-gradient(135deg, #1B3A6B08, #00A8E015);
    border: 1px solid #00A8E0; border-radius: 12px; padding: 18px 22px; margin: 12px 0;
  }
  .ai-response {
    background: white; border-radius: 12px; padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-left: 4px solid #1B3A6B;
    line-height: 1.7; font-size: 0.95rem;
  }
</style>
""", unsafe_allow_html=True)


# API helper functions
#
# Streamlit reruns the whole script on every interaction (button click, sidebar
# change, etc.) — without caching that means ~17 backend round-trips per click,
# including LLM-backed endpoints (suggestions / recommendations / narrator),
# which makes pure-UI actions like "populate the chat input from a suggestion"
# feel laggy. Wrapping the GET helper in ``@st.cache_data`` short-circuits all
# unchanged-filter reads to a memory cache. Cache key = (path, sorted params),
# TTL=120s. POSTs are not cached — they mutate session state and must always run.

@st.cache_data(ttl=120, show_spinner=False)
def _api_get_cached(path: str, params_kv: tuple):
    """Cached inner — raises on error so failures aren't memoised."""
    r = requests.get(f"{API_BASE}{path}", params=dict(params_kv), timeout=30)
    r.raise_for_status()
    return r.json()


def api_get(path: str, params: dict | None = None) -> dict | list | None:
    params = params or {}
    # Stable, hashable cache key — sort items, drop None values
    kv = tuple(sorted((k, v) for k, v in params.items() if v is not None))
    try:
        return _api_get_cached(path, kv)
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, body: dict) -> dict | None:
    """POST is intentionally NOT cached — chat queries must always run live."""
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def kpi_card(label, value, sub=None):
    label_str = f"{label} &nbsp;·&nbsp; {sub}" if sub else label
    label_html = f'<div class="metric-label">{label_str}</div>' if label_str else ""
    return f'<div class="metric-card"><div class="metric-value">{value}</div>{label_html}</div>'


# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Cancellation Intelligence")
    st.markdown("---")

    filter_opts = api_get("/api/analytics/filters") or {}
    stores_list = filter_opts.get("stores", [])
    reasons_list = filter_opts.get("reasons", [])
    date_range = filter_opts.get("date_range", {})

    all_store_nums = [s["STORE_NUM"] for s in stores_list]
    sel_stores = st.multiselect(
        "Stores", all_store_nums, default=all_store_nums,
        format_func=lambda x: f"Store {x} ({next((s['CITY'] for s in stores_list if s['STORE_NUM']==x), '')})"
    )

    all_regions = sorted(set(s["REGION"] for s in stores_list))
    sel_regions = st.multiselect("Region", all_regions, default=all_regions)

    # State filter — backend ships {STATE, store_count}; fall back to deriving
    # from the stores payload if an older backend is running.
    states_meta = filter_opts.get("states") or []
    if states_meta:
        all_states = [s["STATE"] for s in states_meta]
        state_label = lambda x: f"{x} ({next((s['store_count'] for s in states_meta if s['STATE']==x), 0)} stores)"
    else:
        all_states = sorted({s["STATE"] for s in stores_list if s.get("STATE")})
        state_label = lambda x: x
    sel_states = st.multiselect("State", all_states, default=all_states, format_func=state_label)

    # d_from = st.text_input("From (YYYY-MM-DD)", value=date_range.get("from","2024-02-01"))
    # d_to   = st.text_input("To (YYYY-MM-DD)",   value=date_range.get("to","2024-06-23"))
    # date picker
    d_from = st.date_input("From", value=date(2024, 2, 1))
    d_to   = st.date_input("To",   value=date(2024, 6, 23))

    # Convert to string if your downstream code expects "YYYY-MM-DD"
    d_from = d_from.strftime("%Y-%m-%d")
    d_to   = d_to.strftime("%Y-%m-%d")

    sel_reasons = st.multiselect("Cancel Reason", reasons_list, default=reasons_list)
    st.markdown("---")
    st.caption("Backend API on :8000")


# Build query params
qp = {
    "stores":    ",".join(str(s) for s in sel_stores) if sel_stores else "",
    "regions":   ",".join(str(r) for r in sel_regions) if sel_regions else "",
    "states":    ",".join(sel_states) if sel_states else "",
    "date_from": d_from, "date_to": d_to,
    "reasons":   "|".join(sel_reasons) if sel_reasons else "",
}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='color:{RI_BLUE};margin:0'>Order Cancellation Intelligence</h1>"
    "<p style='color:#888;margin:0'>Retail Insight  |  Feb – Jun 2024 </p>",
    unsafe_allow_html=True
)
st.markdown("---")

tabs = st.tabs(["📊 Overview","📍 Where","🔍 Why","🛒 Products","📦 Inventory","🧪 Data Quality","🤖 AI Insights"])


# ══════════════════════════════════════════════════════════════════════════════
# OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    kpis = api_get("/api/analytics/overview", qp) or {}
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(kpi_card("Orders Placed", f"{kpis.get('total_order_units',0):,.0f}"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("Units Cancelled", f"{kpis.get('total_cancel_units',0):,.0f}"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("Cancel Rate", f"{kpis.get('cancel_rate_units',0):.1f}%", "by units"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("Revenue at Risk", f"${kpis.get('total_cancel_revenue',0):,.0f}"), unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("Cancel Rate $", f"{kpis.get('cancel_rate_revenue',0):.1f}%", "by revenue"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_r = st.columns([3,2])

    with col_l:
        st.markdown('<div class="section-header">Weekly Trend</div>', unsafe_allow_html=True)
        weekly = api_get("/api/analytics/trends/weekly", qp) or []
        if weekly:
            wdf = pd.DataFrame(weekly)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=wdf["order_week"], y=wdf["cancel_qty"], name="Units", marker_color=RI_TEAL, opacity=0.85), secondary_y=False)
            fig.add_trace(go.Scatter(x=wdf["order_week"], y=wdf["cancel_amt"], name="Revenue $", mode="lines+markers", line=dict(color=RI_RED, width=2.5)), secondary_y=True)
            fig.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white",
                              title="Weekly Cancellation Trend — Units & Revenue at Risk",
                              margin=dict(l=10,r=10,t=50,b=60), legend=dict(orientation="h",y=1.1),
                              xaxis=dict(tickangle=45, tickfont=dict(size=8)))
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Cancel Reasons</div>', unsafe_allow_html=True)
        reasons = api_get("/api/analytics/reasons", qp) or []
        if reasons:
            rdf = pd.DataFrame(reasons).head(8)
            fig2 = px.bar(rdf, x="cancel_qty", y="reason", orientation="h",
                          color_discrete_sequence=[RI_BLUE],
                          labels={"cancel_qty":"Units","reason":"Reason"},
                          title="Top Cancel Reasons by Volume")
            fig2.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white",
                               yaxis=dict(autorange="reversed"), margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig2, use_container_width=True)

    dow = api_get("/api/analytics/trends/dow", {k:v for k,v in qp.items() if k!="reasons"}) or []
    if dow:
        ddf = pd.DataFrame(dow)
        fig3 = px.bar(ddf, x="day", y="cancel_qty", color="cancel_qty",
                      color_continuous_scale=[[0,"#EEF6FB"],[1,RI_BLUE]],
                      labels={"cancel_qty":"Units","day":"Day of Week"},
                      title="Cancellations by Day of Week")
        fig3.update_layout(height=400, plot_bgcolor="white", paper_bgcolor="white",
                           showlegend=False, coloraxis_showscale=False, margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# WHERE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-header">Geographic Distribution</div>', unsafe_allow_html=True)
    state_data = api_get("/api/analytics/states", qp) or []
    if state_data:
        st_df = pd.DataFrame(state_data)
        max_rate = float(st_df["cancel_rate"].max()) if len(st_df) else 1.0
        fig_map = px.choropleth(
            st_df, locations="STATE", locationmode="USA-states", scope="usa",
            title="Cancel Rate by State",
            color="cancel_rate",
            color_continuous_scale=[[0, RI_GREEN], [0.5, RI_AMBER], [1, RI_RED]],
            range_color=[0, max(max_rate, 1)],
            hover_data={"cancel_qty": ":,", "order_qty": ":,", "stores": True,
                        "cancel_rate": ":.2f"},
            labels={"cancel_rate": "Cancel Rate %"},
        )
        fig_map.update_layout(height=380, geo=dict(bgcolor="#F7F9FC"),
                               margin=dict(l=10, r=10, t=20, b=10),
                               paper_bgcolor="#F7F9FC",
                               coloraxis_colorbar=dict(title="Rate %"))
        st.plotly_chart(fig_map, use_container_width=True)

    st.markdown('<div class="section-header">Store Cancel Rates</div>', unsafe_allow_html=True)
    stores_data = api_get("/api/analytics/stores", qp) or []
    if stores_data:
        sdf = pd.DataFrame(stores_data)
        # Prefer backend-supplied composite label; fall back to local concat.
        if "store_label" in sdf.columns:
            sdf["label"] = sdf["store_label"].fillna(
                "Store " + sdf["STORE_NUM"].astype(str) + " " + sdf["CITY"].fillna("")
            )
        else:
            sdf["label"] = "Store " + sdf["STORE_NUM"].astype(str) + " " + sdf["CITY"].fillna("")
        avg_rate = sdf["cancel_qty"].sum() / sdf["order_qty"].sum() * 100

        col_l, col_r = st.columns([3,2])
        with col_l:
            fig_s = px.bar(sdf.sort_values("cancel_rate",ascending=False),
                           x="label", y="cancel_rate", color="cancel_rate",
                           title="Store Cancel Rate (sorted, with network-average line)",
                           color_continuous_scale=[[0,RI_GREEN],[0.4,RI_AMBER],[1,RI_RED]],
                           text=sdf.sort_values("cancel_rate",ascending=False)["cancel_rate"].apply(lambda x:f"{x:.1f}%"),
                           labels={"cancel_rate":"Cancel Rate %","label":"Store"})
            fig_s.add_hline(y=avg_rate, line_dash="dot", line_color=RI_BLUE,
                            annotation_text=f"Avg {avg_rate:.1f}%")
            fig_s.update_traces(textposition="outside")
            fig_s.update_layout(height=360, plot_bgcolor="white", paper_bgcolor="white",
                                 coloraxis_showscale=False, margin=dict(l=10,r=10,t=20,b=80),
                                 xaxis_tickangle=40)
            st.plotly_chart(fig_s, use_container_width=True)

        with col_r:
            disp = sdf[["label","order_qty","cancel_qty","cancel_rate","cancel_amt"]].copy()
            disp.columns = ["Store","Orders","Cancels","Rate %","Rev at Risk"]
            disp["Rate %"] = disp["Rate %"].apply(lambda x:f"{x:.1f}%")
            disp["Rev at Risk"] = disp["Rev at Risk"].apply(lambda x:f"${x:,.0f}")
            st.dataframe(disp, hide_index=True, use_container_width=True, height=360)
        # Headline insight derived in the backend from the filtered data.
        insights = api_get("/api/analytics/insights", qp) or {}
        top = insights.get("top_store")
        if top:
            cls = {"high": "warning-box", "medium": "warning-box",
                   "info": "insight-box"}.get(top.get("severity"), "insight-box")
            st.markdown(
                f'<div class="{cls}">{top.get("icon","")} {top.get("text","")}</div>',
                unsafe_allow_html=True,
            )

    # st.markdown('<div class="section-header">Region Cancel Rates</div>', unsafe_allow_html=True)
    # regions_data = api_get("/api/analytics/regions", qp) or []
    # if regions_data:
    #     rdf = pd.DataFrame(regions_data)
    #     fig_r = px.bar(rdf, x="REGION", y="cancel_rate", color="cancel_rate",
    #                    color_continuous_scale=[[0,RI_GREEN],[1,RI_RED]],
    #                    text=rdf["cancel_rate"].apply(lambda x:f"{x:.1f}%"),
    #                    labels={"cancel_rate":"Cancel Rate %","REGION":"Region"},
    #                    title="Cancel Rate by Region")
    #     fig_r.update_traces(textposition="outside")
    #     fig_r.update_layout(height=240, plot_bgcolor="white", paper_bgcolor="white",
    #                          coloraxis_showscale=False, margin=dict(l=10,r=10,t=20,b=10))
    #     st.plotly_chart(fig_r, use_container_width=True)

    # ── Store × Department concentration heatmap ─────────────────────────────
    # The headline store rate (e.g. "Store 1426 is at 8.2%") doesn't tell you
    # whether that's one department or every department. This heatmap answers
    # that question — a single hot row = SKU-level intervention; a hot column
    # across many stores = systemic catalog/supply issue.
    st.markdown(
        '<div class="section-header">Store × Department Concentration</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Where in each store is the cancellation rate elevated? A single hot cell suggests a SKU "
        "or category intervention; a hot row across departments suggests a store-level operational fix. "
        "Greyed cells = no orders in that store × department slice."
    )
    sd = api_get("/api/analytics/heatmap/store-dept", qp) or {}
    sd_rows = sd.get("rows", [])
    sd_stores = sd.get("stores", [])
    sd_depts = sd.get("departments", [])

    if sd_rows and sd_stores and sd_depts:
        df_sd = pd.DataFrame(sd_rows)
        store_labels = [s["store_label"] for s in sd_stores]
        store_nums   = [s["STORE_NUM"]   for s in sd_stores]

        rate_pivot = (df_sd.pivot_table(index="STORE_NUM", columns="DEPARTMENT",
                                         values="cancel_rate", aggfunc="first")
                            .reindex(index=store_nums, columns=sd_depts))
        qty_pivot  = (df_sd.pivot_table(index="STORE_NUM", columns="DEPARTMENT",
                                         values="cancel_qty", aggfunc="first")
                            .reindex(index=store_nums, columns=sd_depts).fillna(0))
        ord_pivot  = (df_sd.pivot_table(index="STORE_NUM", columns="DEPARTMENT",
                                         values="order_qty", aggfunc="first")
                            .reindex(index=store_nums, columns=sd_depts).fillna(0))

        hover = [[
            (f"<b>{store_labels[i]}</b><br>Department: {sd_depts[j]}<br>"
             f"Cancel rate: {rate_pivot.iat[i, j]:.1f}%<br>"
             f"Cancels: {qty_pivot.iat[i, j]:.0f} units<br>"
             f"Orders:  {ord_pivot.iat[i, j]:.0f} units")
            if pd.notna(rate_pivot.iat[i, j])
            else f"<b>{store_labels[i]}</b><br>Department: {sd_depts[j]}<br>No orders in this slice"
            for j in range(len(sd_depts))
        ] for i in range(len(store_nums))]

        # Cap the colour scale at the 95th percentile so a single outlier cell
        # doesn't compress every other cell into a flat colour.
        flat_rates = rate_pivot.values.flatten()
        flat_rates = flat_rates[~pd.isna(flat_rates)]
        zmax = float(pd.Series(flat_rates).quantile(0.95)) if len(flat_rates) else 10.0
        zmax = max(zmax, 5.0)  # floor

        fig_sd = go.Figure(data=go.Heatmap(
            z=rate_pivot.values,
            x=sd_depts, y=store_labels,
            text=hover, hoverinfo="text",
            colorscale=[[0, RI_GREEN], [0.4, RI_AMBER], [1, RI_RED]],
            zmin=0, zmax=zmax,
            colorbar=dict(title=dict(text="Cancel %", side="right"),
                          thickness=14, len=0.85),
            xgap=2, ygap=2,
        ))
        fig_sd.update_layout(
            title="Cancel Rate by Store × Department (top 15 stores by volume)",
            height=max(380, 26 * len(store_nums) + 160),
            margin=dict(l=10, r=10, t=60, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(side="top", tickangle=-30),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_sd, use_container_width=True)
    else:
        st.info("No store × department data under the current filter set.")


# ══════════════════════════════════════════════════════════════════════════════
# WHY
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('<div class="section-header">Sub-Reasons</div>', unsafe_allow_html=True)
        sub = api_get("/api/analytics/reasons/sub", qp) or []
        if sub:
            sdf = pd.DataFrame(sub)
            # bars are coloured by parent reason and hover shows the joined label.
            has_parent = "reason" in sdf.columns and "reason_full" in sdf.columns
            fig_sub = px.bar(
                sdf, x="cancel_qty", y="sub_reason", orientation="h",
                title="Sub-Reasons by Parent Category (top 20)",
                color="reason" if has_parent else None,
                color_discrete_sequence=[RI_BLUE, RI_TEAL, RI_AMBER, RI_RED, RI_GREEN, "#9C7AC6", "#6C757D"],
                hover_data=({"reason_full": True, "reason": False,
                             "sub_reason": False, "cancel_qty": ":,"} if has_parent else None),
                labels={"cancel_qty": "Units", "sub_reason": "Sub-Reason", "reason": "Parent Reason"},
            )
            fig_sub.update_layout(
                height=500, plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", y=1.12, x=0, font=dict(size=10)),
            )
            st.plotly_chart(fig_sub, use_container_width=True)

    with col_b:
        st.markdown('<div class="section-header">Time to Cancellation (days)</div>', unsafe_allow_html=True)
        lag = api_get("/api/analytics/cancels/lag", qp) or []
        if lag:
            ldf = pd.DataFrame(lag)
            fig_lag = px.bar(ldf, x="lag_days", y="cancel_qty",
                             color_discrete_sequence=[RI_BLUE],
                             labels={"lag_days":"Days Order to Cancel","cancel_qty":"Units"},
                             title="Time-to-Cancel Distribution (days from order)")
            fig_lag.update_layout(height=360, plot_bgcolor="white", paper_bgcolor="white",
                                   margin=dict(l=10,r=10,t=20,b=10))
            st.plotly_chart(fig_lag, use_container_width=True)
            
            
   
    # Lag-distribution headline is derived from the backend's /insights endpoint —
    # severity drives the styling (info → blue, medium/high → amber/red).
    why_insights = api_get("/api/analytics/insights", qp) or {}
    same_day = why_insights.get("same_day_share")
    if same_day:
        cls = {"high": "warning-box", "medium": "warning-box",
               "info": "insight-box"}.get(same_day.get("severity"), "insight-box")
        st.markdown(
            f'<div class="{cls}">{same_day.get("icon","")} {same_day.get("text","")}</div>',
            unsafe_allow_html=True,
        )
    
    st.markdown('<div class="section-header">Reason × Day-of-Week Heatmap</div>', unsafe_allow_html=True)
    # st.caption("Top reasons crossed with order day-of-week — surfaces patterns the marginal totals hide.")
    hm = api_get("/api/analytics/heatmap/reason-dow", qp) or {}
    if hm.get("rows"):
        hdf = pd.DataFrame(hm["rows"])
        reasons = hm.get("reasons", [])[:10]
        days = hm.get("days", [])
        hdf = hdf[hdf["reason"].isin(reasons)]
        if not hdf.empty:
            pivot = (hdf.pivot(index="reason", columns="day", values="cancel_qty")
                        .reindex(index=reasons, columns=days)
                        .fillna(0).astype(int))
            fig_hm = px.imshow(
                pivot.values,
                x=pivot.columns.tolist(), y=pivot.index.tolist(),
                title="Top Cancel Reason crossed with Order Day Heatmap",
                color_continuous_scale=[[0, "#F7F9FC"], [1, RI_BLUE]],
                aspect="auto", text_auto=True,
                labels={"x": "Order Day-of-Week", "y": "Cancel Reason", "color": "Units"},
            )
            fig_hm.update_layout(height=420, plot_bgcolor="white", paper_bgcolor="white",
                                  margin=dict(l=10, r=10, t=40, b=10),
                                  coloraxis_showscale=False)
            st.plotly_chart(fig_hm, use_container_width=True)



# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    rank_by = st.radio(
        "Rank top products by", ["Cancelled units", "Revenue at risk"],
        horizontal=True, key="prod_rank",
        help="Volume rankings privilege cheap items; revenue rankings reveal where the dollars are leaking.",
    )
    sort_by = "amt" if rank_by == "Revenue at risk" else "qty"
    products = api_get("/api/analytics/products", {**qp, "top_n": 20, "sort_by": sort_by}) or []
    categories = api_get("/api/analytics/categories", qp) or []

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if products:
            pdf = pd.DataFrame(products)
            pdf["short"] = pdf["PRODUCT_NAME"].apply(lambda x: str(x)[:45]+"..." if isinstance(x,str) and len(str(x))>45 else str(x))
            # Bars are sized by the *chosen* metric (units OR revenue) so the
            # axis matches the radio at the top. Hover always shows BOTH so the
            # alternate metric is one cursor-move away.
            pdf["cancel_amt_disp"] = pdf["cancel_amt"].fillna(0)
            value_col   = "cancel_amt_disp" if sort_by == "amt" else "cancel_qty"
            value_label = "Revenue at Risk ($)" if sort_by == "amt" else "Cancelled Units"
            title       = ("Top 20 Products by Revenue at Risk"
                           if sort_by == "amt" else "Top 20 Products by Cancelled Units")
            fig_p = px.bar(
                pdf, x=value_col, y="short", orientation="h", color="CATEGORY",
                color_discrete_sequence=[RI_BLUE, RI_TEAL, RI_AMBER, RI_RED],
                labels={value_col: value_label, "short": "Product"},
                title=title,
                custom_data=["PRODUCT_NAME", "CATEGORY", "DEPARTMENT",
                              "cancel_qty", "cancel_amt_disp"],
            )
            fig_p.update_traces(
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[2]} · %{customdata[1]}<br>"
                    "Cancelled units: %{customdata[3]:,.0f}<br>"
                    "Revenue at risk: $%{customdata[4]:,.0f}"
                    "<extra></extra>"
                ),
            )
            fig_p.update_layout(
                height=700, plot_bgcolor="white", paper_bgcolor="white",
                yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=80, b=10),
                legend=dict(orientation="h", y=1.08),
                xaxis=dict(tickprefix="$" if sort_by == "amt" else None,
                            separatethousands=True),
            )
            st.plotly_chart(fig_p, use_container_width=True)

    with col_p2:
        if categories:
            cdf = pd.DataFrame(categories)
            fig_tree = px.treemap(cdf, path=["DEPARTMENT","CATEGORY"], values="cancel_qty",
                                  color="cancel_qty",
                                  color_continuous_scale=[[0,"#EEF6FB"],[1,RI_BLUE]],
                                  title="Cancellations by Dept and Category")
            fig_tree.update_layout(height=700, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_tree, use_container_width=True)
            
    st.markdown('<div class="section-header">Product Lifecycle: Discontinued vs Active</div>', unsafe_allow_html=True)
    status_payload = api_get("/api/analytics/products/status", qp) or {}
    summary = status_payload.get("summary", [])
    if summary:
        bucket_labels = {"discontinued": "Discontinued",
                         "new_launch":   f"New launch (≤ {status_payload.get('new_launch_window_days', 30)}d)",
                         "established":  "Established active",
                         "unknown":      "Unknown (not in catalogue)"}
        bucket_colors = {"discontinued": RI_RED, "new_launch": RI_AMBER,
                         "established":  RI_GREEN, "unknown": "#888888"}
        col_a, col_b = st.columns([3, 2])
        with col_a:
            sdf = pd.DataFrame(summary)
            sdf["label"] = sdf["bucket"].map(bucket_labels).fillna(sdf["bucket"])
            fig_st = px.bar(
                sdf, x="label", y="cancel_qty", color="bucket",
                color_discrete_map=bucket_colors,
                text=sdf["share_pct"].apply(lambda x: f"{x:.1f}%"),
                labels={"cancel_qty": "Cancelled Units", "label": "Lifecycle Bucket"},
                title="Cancels by Product Lifecycle Status",
            )
            fig_st.update_traces(textposition="outside")
            fig_st.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                                  showlegend=False, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_st, use_container_width=True)
            note = status_payload.get("_note")
            if note:
                st.caption(f"Note: {note}")
        with col_b:
            top_disc = status_payload.get("top_discontinued", [])
            if top_disc:
                st.markdown("**Top SKUs cancelled despite being discontinued**")
                ddf = pd.DataFrame(top_disc).head(8)
                if "PRODUCT_NAME" not in ddf.columns: ddf["PRODUCT_NAME"] = ""
                if "CATEGORY"     not in ddf.columns: ddf["CATEGORY"] = ""
                ddf = ddf[["PRODUCT_NAME", "CATEGORY", "cancel_qty", "cancel_amt"]].copy()
                ddf.columns = ["Product", "Category", "Units", "Revenue at Risk"]
                ddf["Revenue at Risk"] = ddf["Revenue at Risk"].apply(lambda x: f"${x:,.0f}")
                ddf["Product"] = ddf["Product"].fillna("(no name)").astype(str).str.slice(0, 50)
                st.dataframe(ddf, hide_index=True, use_container_width=True)

    # Product-level insight is now derived in the backend with severity-driven styling.
    prod_insights = api_get("/api/analytics/insights", qp) or {}
    prod_conc = prod_insights.get("product_concentration")
    if prod_conc:
        cls = {"high": "warning-box", "medium": "warning-box",
               "info": "insight-box"}.get(prod_conc.get("severity"), "insight-box")
        st.markdown(
            f'<div class="{cls}">{prod_conc.get("icon","")} {prod_conc.get("text","")}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    inv_data = api_get("/api/analytics/inventory", qp) or {}
    col_i1, col_i2 = st.columns(2)

    with col_i1:
        buckets = inv_data.get("bucket_distribution", [])
        if buckets:
            bdf = pd.DataFrame(buckets)
            COLOR_MAP = {
                "Zero": "#E63946", "Negative (data error)": "#9B1D20",
                "Low (1-10)": "#F4A261", "Medium (11-50)": "#00A8E0",
                "High (50+)": "#2A9D8F", "No snapshot": "#CCCCCC",
                # Back-compat with older bucket labels
                "Negative": "#9B1D20", "Unknown": "#CCCCCC",
            }
            fig_b = px.bar(bdf, x="bucket", y="cancel_qty", color="bucket",
                           color_discrete_map=COLOR_MAP,
                           labels={"cancel_qty":"Units","bucket":"Inventory Level"},
                           title="Cancels by Inventory Level on Order Date")
            fig_b.update_layout(height=600, plot_bgcolor="white", paper_bgcolor="white",
                                 showlegend=False, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig_b, use_container_width=True)
            st.caption(
                "Inventory data has daily granularity only — the bucket reflects on-hand at the "
                "day snapshot, not at the moment of order. Same-day stockouts may still "
                "fall into a non-zero bucket here."
            )

    with col_i2:
        # New payload prefers `stockout_by_store` (per-store stockout RATE).
        # Older clients still ship `zero_stock_by_store` as a back-compat alias.
        stockout_rows = inv_data.get("stockout_by_store") or inv_data.get("zero_stock_by_store") or []
        if stockout_rows:
            zdf = pd.DataFrame(stockout_rows)
            if "store_label" in zdf.columns:
                zdf["label"] = zdf["store_label"].fillna(
                    "Store " + zdf["STORE_NUM"].astype(str) + " " + zdf["CITY"].fillna("")
                )
            else:
                zdf["label"] = "Store " + zdf["STORE_NUM"].astype(str) + " " + zdf["CITY"].fillna("")

            # Prefer the new rate field. Fall back to the legacy day-count if a
            # pre-fix backend is still running.
            if "zero_rate_pct" in zdf.columns:
                y_col, y_label, hover = "zero_rate_pct", "% of snapshots at zero", {
                    "zero_events": ":,", "total_snapshots": ":,", "zero_rate_pct": ":.2f",
                    "STORE_NUM": False, "label": False,
                }
                title = "Stockout Rate by Store (% of inventory snapshots showing zero on-hand)"
            else:
                y_col, y_label, hover = "zero_inv_days", "Days at Zero", None
                title = "Zero Inventory Frequency by Store (legacy)"

            fig_z = px.bar(zdf.sort_values(y_col, ascending=False).head(10),
                           x="label", y=y_col,
                           color=y_col,
                           color_continuous_scale=[[0,"#2A9D8F"],[0.5,"#F4A261"],[1,RI_RED]],
                           hover_data=hover,
                           labels={y_col: y_label, "label": "Store"},
                           title=title)
            fig_z.update_layout(height=600, plot_bgcolor="white", paper_bgcolor="white",
                                 xaxis_tickangle=40, margin=dict(l=10,r=10,t=40,b=80),
                                 coloraxis_showscale=False)
            st.plotly_chart(fig_z, use_container_width=True)
    
    
    # OOS data-quality insight is now derived in the backend with severity-driven styling.
    oos_dq = why_insights.get("oos_data_quality")
    if oos_dq:
        cls = {"high": "warning-box", "medium": "warning-box",
               "info": "insight-box"}.get(oos_dq.get("severity"), "warning-box")
        st.markdown(
            f'<div class="{cls}">{oos_dq.get("icon","")} {oos_dq.get("text","")}</div>',
            unsafe_allow_html=True,
        )
    # Negative-inventory insight derived in the backend; severity scales with the
    # absolute count, text is LLM-refined via the narrator. Falls back gracefully
    # if /api/analytics/insights hasn't produced the insight (e.g. zero records).
    inv_insights = api_get("/api/analytics/insights", qp) or {}
    neg_insight = inv_insights.get("negative_inventory")
    if neg_insight:
        cls = {"high": "warning-box", "medium": "warning-box",
               "info": "insight-box"}.get(neg_insight.get("severity"), "warning-box")
        st.markdown(
            f'<div class="{cls}">{neg_insight.get("icon","")} {neg_insight.get("text","")}</div>',
            unsafe_allow_html=True,
        )

    # ── Save-rate proxy: quantified substitution opportunity ────────────────
    # The OOS DQ paradox tells us cancels are happening on items that LOOK
    # in-stock at the day grain. This panel pivots from "the data is messy"
    # to "here's what could have been saved" — for every OOS cancel where a
    # same-category in-stock alternate existed at the same store on the same
    # day, a substitution flow could have plausibly recovered the revenue.
    st.markdown(
        '<div class="section-header">Substitution Opportunity</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "For each OOS-flagged cancellation, the backend checks whether ANOTHER SKU in the same "
        "CATEGORY was in stock at the same store on the same day."
    )
    save = api_get("/api/analytics/save-rate", qp) or {}
    sr_total = save.get("total_oos_cancels", 0)
    if sr_total:
        share_pct = save.get("savable_share_pct", 0.0)
        savable_n = save.get("savable_count", 0)
        savable_rev = save.get("savable_revenue", 0.0)
        savable_units = save.get("savable_units", 0)
        oos_rev = save.get("total_oos_revenue", 0.0)
        sev = save.get("severity", "info")
        rate_color = (
            RI_RED if sev == "high" else RI_AMBER if sev == "medium" else RI_TEAL
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'<div class="metric-card" style="border-left:5px solid {rate_color};">'
                f'<div class="metric-value" style="color:{rate_color};">{share_pct:.0f}%</div>'
                f'<div class="metric-label">Save-able share &nbsp;·&nbsp; of OOS cancels</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                kpi_card("Recoverable Revenue", f"${savable_rev:,.0f}",
                         f"of ${oos_rev:,.0f} OOS revenue"),
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                kpi_card("Recoverable Units", f"{savable_units:,.0f}",
                         f"{savable_n:,} cancel events"),
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                kpi_card("OOS Cancels in Scope", f"{sr_total:,.0f}",
                         "denominator"),
                unsafe_allow_html=True,
            )

        # Top savable opportunities — what to ask the substitution flow to handle
        # first. Keep it short (5 rows) and demo-friendly: store + category +
        # original SKU + example alternate.
        examples = save.get("examples", [])
        if examples:
            st.markdown(
                '<div style="margin-top:14px;font-weight:600;color:'
                f'{RI_BLUE};">Top recoverable opportunities under the current filter</div>',
                unsafe_allow_html=True,
            )
            edf = pd.DataFrame(examples)
            edf_display = pd.DataFrame({
                "Store":              edf["store_label"],
                "Date":               edf["date"],
                "Category":           edf["category"],
                "Cancelled SKU":      edf["cancelled_sku"].str.slice(0, 60),
                "In-stock alternate": edf["example_alternative"].str.slice(0, 60),
                "Alts available":     edf["alternative_count"],
                "Units":              edf["units_cancelled"],
                "Revenue at risk":    edf["revenue_at_risk"].apply(lambda x: f"${x:,.0f}"),
            })
            st.dataframe(edf_display, hide_index=True, use_container_width=True)
            st.caption(
                f"Caveats: {save.get('_note','')}"
            )
    else:
        st.info(
            "No OOS-flagged cancellations under the current filter set — pick a wider "
            "filter scope or include Out Of Stock in the Cancel Reason filter."
        )


# ══════════════════════════════════════════════════════════════════════════════
# AI INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    # ── DATA QUALITY TAB ──────────────────────────────────────────────────
    st.markdown('<div class="section-header">Data Quality Scorecard</div>', unsafe_allow_html=True)
    st.caption("Integrity signals across all source tables. Severity scales by share of records, "
               "not absolute count — so issues are surfaced even on small filter slices.")

    dq = api_get("/api/analytics/data-quality", qp) or {}
    checks = dq.get("checks", [])
    overall = dq.get("overall_severity", "info")

    if checks:
        sev_color = {"high": RI_RED, "medium": RI_AMBER, "info": RI_TEAL}
        sev_icon  = {"high": "🚨",   "medium": "⚠️",     "info": "ℹ️"}
        sev_bg    = {"high": "#FFF3F3","medium": "#FFF8EE","info": "#EEF6FB"}
        banner_cls = "warning-box" if overall in ("high","medium") else "insight-box"
        st.markdown(
            f'<div class="{banner_cls}">{sev_icon[overall]} <strong>Overall data integrity: {overall.upper()}</strong> — {len(checks)} checks evaluated. Cards below show each finding.</div>',
            unsafe_allow_html=True,
        )

        cols_per_row = 3
        for row_start in range(0, len(checks), cols_per_row):
            row_checks = checks[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, c in zip(cols, row_checks):
                sev = c.get("severity", "info")
                color = sev_color.get(sev, RI_TEAL)
                bg    = sev_bg.get(sev, "#EEF6FB")
                html = (
                    f'<div style="background:{bg};border-left:4px solid {color};border-radius:10px;padding:14px 18px;height:100%;">'
                    f'<div style="font-size:0.78rem;color:#666;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{sev}</div>'
                    f'<div style="font-weight:700;color:#1B3A6B;margin-bottom:8px;font-size:0.92rem;">{c["name"]}</div>'
                    f'<div style="font-size:1.5rem;font-weight:700;color:{color};">{c["value"]:,}<span style="font-size:0.8rem;color:#888;font-weight:500;"> / {c["total"]:,}</span></div>'
                    f'<div style="font-size:0.82rem;color:{color};font-weight:600;margin-bottom:8px;">{c["share_pct"]}% of records</div>'
                    f'<div style="font-size:0.8rem;color:#444;line-height:1.4;">{c["description"]}</div>'
                    f'</div>'
                )
                with col:
                    st.markdown(html, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No data-quality findings to report under the current filter set.")


with tabs[6]:
    # st.markdown('<div class="section-header">AI-Powered Investigation</div>', unsafe_allow_html=True)

    # ── Recommendations panel — fact-grounded next actions ─────────────
    st.markdown('<div class="section-header">Recommended Next Actions</div>', unsafe_allow_html=True)
    st.caption('Prioritised actions inferred from the current filter set. Numbers and identities are code-derived; phrasing and prioritisation are LLM-synthesised (with deterministic fallback when no key is configured).')
    recs_payload = api_get('/api/insights/recommendations', qp) or {}
    recs = recs_payload.get('recommendations', [])
    llm_used_recs = recs_payload.get('_llm_used', False)

    if recs:
        rec_sev_color = {'high': RI_RED, 'medium': RI_AMBER, 'info': RI_TEAL}
        rec_effort_color = {'quick_win': RI_GREEN, 'medium': RI_AMBER, 'strategic': RI_BLUE}
        rec_effort_label = {'quick_win': '⚡ Quick win', 'medium': '🛠 Medium', 'strategic': '🎯 Strategic'}
        cat_icon = {'operational': '🏪', 'catalogue': '📦', 'data-quality': '🧪',
                    'strategic': '🎯', 'process': '⚙️'}

        for i, r in enumerate(recs):
            sev   = r.get('severity', 'info')
            eff   = r.get('effort',   'medium')
            cat   = r.get('category', 'operational')
            scol  = rec_sev_color.get(sev, RI_TEAL)
            ecol  = rec_effort_color.get(eff, RI_AMBER)
            sf    = r.get('supporting_facts', [])
            sf_chips = ' '.join(
                f'<span style="background:#EEF6FB;color:#1B3A6B;padding:2px 8px;border-radius:10px;font-size:0.72rem;margin-right:4px;">{k}</span>'
                for k in sf
            )
            html = (
                f'<div style="background:white;border-left:5px solid {scol};border-radius:10px;padding:16px 20px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                f'<span style="background:{scol}20;color:{scol};padding:3px 10px;border-radius:10px;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;">{sev}</span>'
                f'<span style="background:{ecol}20;color:{ecol};padding:3px 10px;border-radius:10px;font-size:0.72rem;font-weight:600;">{rec_effort_label.get(eff, eff)}</span>'
                f'<span style="color:#666;font-size:0.78rem;">{cat_icon.get(cat, "•")} {cat}</span>'
                f'<span style="margin-left:auto;color:#AAA;font-size:0.72rem;">#{i+1}</span>'
                f'</div>'
                f'<div style="font-weight:700;color:#1B3A6B;font-size:1.0rem;margin-bottom:6px;">{r.get("action", "")}</div>'
                f'<div style="font-size:0.85rem;color:#444;font-style:italic;margin-bottom:8px;">{r.get("rationale", "")}</div>'
                f'<div style="font-size:0.82rem;color:#555;border-top:1px solid #EEE;padding-top:8px;margin-bottom:6px;"><strong>Expected impact:</strong> {r.get("expected_impact", "")}</div>'
                f'<div style="font-size:0.72rem;color:#888;">Supports: {sf_chips}</div>'
                f'</div>'
            )
            st.markdown(html, unsafe_allow_html=True)

        provenance = ('LLM-synthesised' if llm_used_recs else 'Deterministic fallback')
        st.caption(f'Source: {provenance}. {len(recs)} recommendation(s) for the current filter set.')
    else:
        st.info('No recommendations to surface under the current filter set.')

    st.markdown('---')
    st.markdown('<div class="section-header">Investigation Chat</div>', unsafe_allow_html=True)


    model_info = api_get("/api/insights/models") or {}
    available_models = [m["id"] for m in model_info.get("models",[])]
    MODEL_LABELS = {"claude":"Claude (Anthropic)","openai":"GPT-4o (OpenAI)","gemini":"Gemini 1.5 Pro"}
    MODEL_COLORS = {"claude":"#D4620A","openai":"#10A37F","gemini":"#4285F4"}

    # ── AI Config Panel ───────────────────────────────────────────────────────
    with st.expander("⚙️ AI Configuration", expanded=True):
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)

        with col_cfg1:
            ai_mode = st.radio("Mode", ["Single Model","Multi-Model"], horizontal=True)

        with col_cfg2:
            if ai_mode == "Single Model":
                single_model = st.selectbox("Model", available_models or ["claude"],
                                             format_func=lambda x: MODEL_LABELS.get(x,x))
                multi_models = [single_model]
            else:
                multi_models = st.multiselect(
                    "Models to Query",
                    available_models or ["claude","openai","gemini"],
                    default=["claude"],
                    format_func=lambda x: MODEL_LABELS.get(x,x)
                )
                single_model = multi_models[0] if multi_models else "claude"

        with col_cfg3:
            if ai_mode == "Multi-Model":
                enable_judge = st.toggle("Enable Judge", value=False,
                                          help="Run a second AI to validate and synthesize all responses")
                if enable_judge:
                    judge_model = st.selectbox(
                        "Judge Model",
                        available_models or ["claude"],
                        format_func=lambda x: MODEL_LABELS.get(x,x)
                    )
                else:
                    judge_model = "claude"
            else:
                enable_judge = False
                judge_model = "claude"

    # ── BYO-key panel — for the live portfolio deployment ────────────────────
    # The hosted demo ships without preset API keys to keep cost bounded.
    # Visitors paste their own keys here; keys live in this user's session only
    # and ride along on each /query POST request via ai_config.api_keys. No key
    # storage, no logging — keys never leave this browser session or the
    # request body.
    with st.expander("🔑 Bring your own API key (optional)", expanded=False):
        st.caption(
            "Paste any key to enable that model's live responses. Keys are "
            "kept in this session only and are sent per-request to the LLM "
            "provider. Without a key, the corresponding model surfaces an "
            "error in the chat; the rest of the app continues with "
            "deterministic templates."
        )
        if "byo_keys" not in st.session_state:
            st.session_state.byo_keys = {"claude": "", "openai": "", "gemini": ""}
        k1, k2, k3 = st.columns(3)
        with k1:
            st.session_state.byo_keys["claude"] = st.text_input(
                "Anthropic key", type="password",
                value=st.session_state.byo_keys.get("claude", ""),
                placeholder="sk-ant-...",
            )
        with k2:
            st.session_state.byo_keys["openai"] = st.text_input(
                "OpenAI key", type="password",
                value=st.session_state.byo_keys.get("openai", ""),
                placeholder="sk-...",
            )
        with k3:
            st.session_state.byo_keys["gemini"] = st.text_input(
                "Google key", type="password",
                value=st.session_state.byo_keys.get("gemini", ""),
                placeholder="AIza...",
            )
        provided = [k for k, v in st.session_state.byo_keys.items() if v.strip()]
        if provided:
            st.success(f"Keys provided for: {', '.join(MODEL_LABELS.get(p, p) for p in provided)}")

    # Build AI config payload
    ai_config = {
        "mode":         "single" if ai_mode == "Single Model" else "multi",
        "model":        single_model,
        "models":       multi_models if multi_models else ["claude"],
        "enable_judge": enable_judge,
        "judge_model":  judge_model,
        "api_keys":     {k: v for k, v in st.session_state.get("byo_keys", {}).items() if v.strip()},
    }

    # ── Chat ──────────────────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"**👤 You:** {msg['content']}")
        else:
            # Show model badges
            for resp in msg.get("model_responses", []):
                color = MODEL_COLORS.get(resp["model"], "#666")
                badge = f'<span class="model-badge" style="background:{color}20;color:{color};border:1px solid {color}">{MODEL_LABELS.get(resp["model"],resp["model"])}</span>'
                st.markdown(badge, unsafe_allow_html=True)

            # Judge panel
            judge = msg.get("judge_result")
            if judge:
                conf_color = {"high":RI_GREEN,"medium":RI_AMBER,"low":RI_RED}.get(judge.get("confidence","medium"), RI_AMBER)
                st.markdown(f"""
                <div class="judge-box">
                  <strong style="color:{RI_BLUE}">⚖️ Judge Evaluation</strong>
                  <span style="float:right;background:{conf_color}20;color:{conf_color};padding:2px 10px;border-radius:10px;font-size:0.8rem;font-weight:600">
                    {judge.get('confidence','').upper()} CONFIDENCE
                  </span><br><br>
                  <em>{judge.get('synthesis','')}</em>
                </div>""", unsafe_allow_html=True)

            st.markdown(f'<div class="ai-response">{msg["content"]}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
    # Suggested questions — dynamically generated from the current filter set.
    sugg_payload = api_get("/api/insights/suggestions", qp) or {}
    sugg_questions = sugg_payload.get("questions", [])
    sugg_llm_used  = sugg_payload.get("_llm_used", False)

    cat_meta = {
        "drill_down":     ("🔍",  RI_BLUE,   "Drill down"),
        "cause":          ("🧭",  RI_AMBER,  "Cause"),
        "comparison":     ("⚖️",  RI_TEAL,   "Compare"),
        "action":         ("🎯",  RI_GREEN,  "Action"),
        "data_quality":   ("🧪",  RI_RED,    "Data quality"),
        "counterfactual": ("💡",  "#9C7AC6", "What-if"),
    }

    header_suffix = "LLM-generated" if sugg_llm_used else "templated from current facts"
    st.markdown(
        f'<div style="font-weight:600;color:{RI_BLUE};margin-bottom:6px;">💡 Suggested investigations '
        f'<span style="font-weight:400;color:#888;font-size:0.78rem;">({header_suffix})</span></div>',
        unsafe_allow_html=True,
    )

    if sugg_questions:
        for row_start in range(0, len(sugg_questions), 2):
            row = sugg_questions[row_start:row_start + 2]
            cols = st.columns(2)
            for col_offset, (col, q) in enumerate(zip(cols, row)):
                idx = row_start + col_offset
                cat = q.get("category", "drill_down")
                icon, chip_color, label = cat_meta.get(cat, ("•", RI_TEAL, cat))
                with col:
                    chip = (
                        f'<span style="display:inline-block;background:{chip_color}20;'
                        f'color:{chip_color};padding:2px 8px;border-radius:10px;'
                        f'font-size:0.72rem;font-weight:600;margin-bottom:4px;">'
                        f'{icon} {label}</span>'
                    )
                    st.markdown(chip, unsafe_allow_html=True)
                    if st.button(q["text"], key=f"sugg_btn_{idx}", use_container_width=True):
                        st.session_state.pending_input = q["text"]
                        st.rerun()
    else:
        for i, q in enumerate([
            "What patterns should we investigate first?",
            "Where should we focus operational attention?",
        ]):
            if st.button(q, key=f"sgeneric_{i}", use_container_width=True):
                st.session_state.pending_input = q
                st.rerun()

    if "pending_input" in st.session_state:
        st.session_state["chat_input"] = st.session_state.pop("pending_input")

    user_input = None

    with st.form("chat", clear_on_submit=True):
        typed = st.text_input("Ask anything about the cancellation data...", key="chat_input")
        submitted = st.form_submit_button("Ask", use_container_width=True)
        if submitted and typed:
            user_input = typed

    if user_input:
        st.session_state.messages.append({"role":"user","content":user_input})

        history_for_api = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
            if m["role"] in ("user","assistant")
        ]

        with st.spinner("Querying AI models..."):
            result = api_post("/api/insights/query", {
                "question": user_input,
                "history":  history_for_api,
                "ai_config": ai_config,
                "filters": {}
            })

        if result:
            st.session_state.messages.append({
                "role":            "assistant",
                "content":         result.get("final_answer",""),
                "model_responses": result.get("model_responses",[]),
                "judge_result":    result.get("judge_result"),
            })
            st.rerun()

    if st.session_state.messages:
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.rerun()

    st.markdown("""
    <div class="insight-box">ℹ️ <strong>AI Usage:</strong> Single mode queries one model directly.
    Multi-model mode sends the same question to all selected models in parallel.
    Enabling the Judge runs a separate AI call to evaluate, compare, and synthesize the responses.
    </div>""", unsafe_allow_html=True)
