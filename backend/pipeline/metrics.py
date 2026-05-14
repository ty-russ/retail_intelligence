"""KPI and analytics functions plus the LLM data-context summarizer.

All functions accept a parsed-filter dict (stores, regions, states, date_from,
date_to, reasons) and return plain Python data ready to be JSON-serialised by
FastAPI.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .loader import get_data


# ──────────────────────────────────────────────────────────────────────────────
# Column helpers
# ──────────────────────────────────────────────────────────────────────────────

def _first_col(df: pd.DataFrame, *candidates: str, default: float = 0.0) -> pd.Series:
    for c in candidates:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").fillna(0)
    return pd.Series(default, index=df.index)


def _ensure_amounts(df: pd.DataFrame, qty_col: str) -> pd.Series:
    for c in ("CNCL_AMT", "CANCEL_AMT", "ORDER_AMT", "EXTENDED_AMT"):
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").fillna(0)
    qty = _first_col(df, qty_col)
    cost = _first_col(df, "UNIT_COST", "PRICE", "RETAIL_PRICE", default=1.0)
    return qty * cost


def _make_store_label(row) -> str:
    """Format ``"Store {STORE_NUM}, {CITY}, {STATE}, Region {REGION}"``."""
    parts = []
    sn = row.get("STORE_NUM")
    if pd.notna(sn):
        try:
            parts.append(f"Store {int(sn)}")
        except (ValueError, TypeError):
            parts.append(f"Store {sn}")
    for col in ("CITY", "STATE"):
        v = row.get(col)
        if pd.notna(v) and str(v).strip():
            parts.append(str(v).strip())
    r = row.get("REGION")
    if pd.notna(r):
        try:
            parts.append(f"Region {int(r)}")
        except (ValueError, TypeError):
            parts.append(f"Region {r}")
    return ", ".join(parts) if parts else ""


# ──────────────────────────────────────────────────────────────────────────────
# Filter application
# ──────────────────────────────────────────────────────────────────────────────

def _apply_filters(
    cancels: pd.DataFrame,
    orders: pd.DataFrame,
    *,
    stores: list[int] | None = None,
    regions: list[str] | None = None,
    states: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    reasons: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    canc = cancels.copy()
    ord = orders.copy()

    if stores:
        canc = canc[canc["STORE_NUM"].isin(stores)]
        ord = ord[ord["STORE_NUM"].isin(stores)]
    if regions and "REGION" in canc.columns:
        regions_int = [int(r) for r in regions]
        canc = canc[canc["REGION"].isin(regions_int)]
        ord = ord[ord["REGION"].isin(regions_int)] if "REGION" in ord.columns else ord
    if states:
        states_upper = [s.strip().upper() for s in states if s and str(s).strip()]
        if states_upper and "STATE" in canc.columns:
            canc = canc[canc["STATE"].str.upper().isin(states_upper)]
        if states_upper and "STATE" in ord.columns:
            ord = ord[ord["STATE"].str.upper().isin(states_upper)]
    if date_from:
        df_ = pd.Timestamp(date_from)
        canc = canc[canc["ORDER_DT"] >= df_]
        ord = ord[ord["ORDER_DT"] >= df_]
    if date_to:
        dt_ = pd.Timestamp(date_to)
        canc = canc[canc["ORDER_DT"] <= dt_]
        ord = ord[ord["ORDER_DT"] <= dt_]
    if reasons:
        reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in canc.columns else "CNCL_RSN_DESC"
        canc = canc[canc[reason_col].isin(reasons)]

    return canc, ord


def _resolve_active_stores(
    store_dim: pd.DataFrame,
    *,
    stores: list[int] | None = None,
    regions: list[str] | None = None,
    states: list[str] | None = None,
    **_unused,
) -> list[int]:
    """Resolve which STORE_NUMs survive the store-dim filters (stores/regions/
    states). Used to filter store-keyed feeds (inventory) that don't carry
    STATE/REGION columns themselves.
    """
    if store_dim is None or store_dim.empty:
        return []
    df = store_dim
    if stores:
        df = df[df["STORE_NUM"].isin(stores)]
    if regions and "REGION" in df.columns:
        df = df[df["REGION"].isin([int(r) for r in regions])]
    if states and "STATE" in df.columns:
        states_upper = [s.strip().upper() for s in states if s and str(s).strip()]
        df = df[df["STATE"].astype(str).str.upper().isin(states_upper)]
    return df["STORE_NUM"].dropna().astype(int).unique().tolist()


def _filter_inventory(
    inv: pd.DataFrame,
    store_dim: pd.DataFrame,
    **filters,
) -> pd.DataFrame:
    """Filter the inventory feed by store-dim filters (stores/regions/states)
    and by date (against ``GREGORIAN_DATE``). When no store-dim filter is
    active, the store intersection is a no-op so semantics are preserved.
    """
    if inv is None or inv.empty:
        return inv

    has_store_dim_filter = any(filters.get(k) for k in ("stores", "regions", "states"))
    out = inv
    if has_store_dim_filter:
        active = _resolve_active_stores(store_dim, **filters)
        if active:
            out = out[out["STORE_NUM"].isin(active)]
        else:
            # User asked for stores/states/regions that match nothing — return empty.
            out = out.iloc[0:0]

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if (date_from or date_to) and "GREGORIAN_DATE" in out.columns:
        gd = pd.to_datetime(out["GREGORIAN_DATE"])
        if date_from:
            out = out[gd >= pd.Timestamp(date_from)]
            gd = pd.to_datetime(out["GREGORIAN_DATE"])
        if date_to:
            out = out[gd <= pd.Timestamp(date_to)]

    return out


# ──────────────────────────────────────────────────────────────────────────────
# Filter options
# ──────────────────────────────────────────────────────────────────────────────

def get_filter_options() -> dict[str, Any]:
    data = get_data()
    store = data["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    cancels = data["cancels"]
    reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in cancels.columns else "CNCL_RSN_DESC"
    reasons = sorted(cancels[reason_col].dropna().unique().tolist())

    dt_min = pd.to_datetime(cancels["ORDER_DT"]).min()
    dt_max = pd.to_datetime(cancels["ORDER_DT"]).max()

    state_counts = (
        store.dropna(subset=["STATE"])
             .groupby("STATE", as_index=False)
             .agg(store_count=("STORE_NUM", "nunique"))
             .sort_values("STATE")
    )
    states = state_counts.to_dict("records")

    return {
        "stores": store.to_dict("records"),
        "states": states,
        "regions": sorted({int(r) for r in store["REGION"].dropna().unique()}),
        "reasons": reasons,
        "date_range": {
            "from": dt_min.strftime("%Y-%m-%d") if pd.notna(dt_min) else None,
            "to":   dt_max.strftime("%Y-%m-%d") if pd.notna(dt_max) else None,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Headline KPIs
# ──────────────────────────────────────────────────────────────────────────────

def overview_kpis(**filters) -> dict[str, Any]:
    d = get_data()
    c, o = _apply_filters(d["cancels"], d["orders"], **filters)
    cancel_qty = _first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY")
    order_qty  = _first_col(o, "ORDER_QTY", "QTY", "PLCD_QTY")
    cancel_amt = _ensure_amounts(c, "CNCL_QTY")
    order_amt  = _ensure_amounts(o, "PLCD_QTY")

    total_cancel_units = float(cancel_qty.sum())
    total_order_units  = float(order_qty.sum())
    total_cancel_rev   = float(cancel_amt.sum())
    total_order_rev    = float(order_amt.sum())

    return {
        "total_order_units":   round(total_order_units, 0),
        "total_cancel_units":  round(total_cancel_units, 0),
        "cancel_rate_units":   round(total_cancel_units / total_order_units * 100, 2) if total_order_units else 0.0,
        "total_order_revenue": round(total_order_rev, 2),
        "total_cancel_revenue":round(total_cancel_rev, 2),
        "cancel_rate_revenue": round(total_cancel_rev / total_order_rev * 100, 2) if total_order_rev else 0.0,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Trends
# ──────────────────────────────────────────────────────────────────────────────

def weekly_trend(**filters) -> list[dict[str, Any]]:
    data = get_data()
    canc, _ = _apply_filters(data["cancels"], data["orders"], **filters)
    if canc.empty:
        return []
    canc = canc.assign(
        cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"),
        cancel_amt=_ensure_amounts(canc, "CNCL_QTY"),
    )
    g = (canc.groupby("order_week", as_index=False)
          .agg(cancel_qty=("cancel_qty", "sum"), cancel_amt=("cancel_amt", "sum"))
          .sort_values("order_week"))
    return g.assign(
        cancel_qty=lambda x: x["cancel_qty"].round(0),
        cancel_amt=lambda x: x["cancel_amt"].round(2),
    ).to_dict("records")


def dow_trend(**filters) -> list[dict[str, Any]]:
    data = get_data()
    canc, _ = _apply_filters(data["cancels"], data["orders"], **filters)
    if canc.empty:
        return []
    order_dow = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    canc = canc.assign(cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    g = (canc.groupby("order_dow", as_index=False)
          .agg(cancel_qty=("cancel_qty", "sum"))
          .rename(columns={"order_dow": "day"}))
    g["day"] = pd.Categorical(g["day"], categories=order_dow, ordered=True)
    return g.sort_values("day").assign(day=lambda x: x["day"].astype(str)).to_dict("records")


# ──────────────────────────────────────────────────────────────────────────────
# Stores & regions
# ──────────────────────────────────────────────────────────────────────────────

def store_breakdown(**filters) -> list[dict[str, Any]]:
    data = get_data()
    canc, ord = _apply_filters(data["cancels"], data["orders"], **filters)
    if canc.empty:
        return []

    canc = canc.assign(
        cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"),
        cancel_amt=_ensure_amounts(canc, "CNCL_QTY"),
    )
    ord = ord.assign(order_qty=_first_col(ord, "ORDER_QTY", "QTY", "PLCD_QTY"))

    cg = canc.groupby("STORE_NUM", as_index=False).agg(cancel_qty=("cancel_qty", "sum"),
                                                       cancel_amt=("cancel_amt", "sum"))
    og = ord.groupby("STORE_NUM", as_index=False).agg(order_qty=("order_qty", "sum"))

    merged = cg.merge(og, on="STORE_NUM", how="outer").fillna(0)
    store_dim = data["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    merged = merged.merge(store_dim, on="STORE_NUM", how="left")
    merged["store_label"] = merged.apply(_make_store_label, axis=1)
    merged["cancel_rate"] = np.where(
        merged["order_qty"] > 0,
        merged["cancel_qty"] / merged["order_qty"] * 100,
        0
    ).round(2)
    return merged.sort_values("cancel_rate", ascending=False).to_dict("records")


def region_breakdown(**filters) -> list[dict[str, Any]]:
    rows = store_breakdown(**filters)
    if not rows:
        return []
    df = pd.DataFrame(rows)
    g = (df.groupby("REGION", as_index=False)
           .agg(order_qty=("order_qty", "sum"),
                cancel_qty=("cancel_qty", "sum"),
                cancel_amt=("cancel_amt", "sum")))
    g["cancel_rate"] = np.where(g["order_qty"] > 0,
                                g["cancel_qty"] / g["order_qty"] * 100, 0).round(2)
    return g.sort_values("cancel_rate", ascending=False).to_dict("records")


# ──────────────────────────────────────────────────────────────────────────────
# Reasons
# ──────────────────────────────────────────────────────────────────────────────

def reason_breakdown(**filters) -> list[dict[str, Any]]:
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if c.empty:
        return []
    reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in c.columns else "CNCL_RSN_DESC"
    c = c.assign(cancel_qty=_first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    g = (c.groupby(reason_col, as_index=False)
          .agg(cancel_qty=("cancel_qty", "sum"))
          .rename(columns={reason_col: "reason"})
          .sort_values("cancel_qty", ascending=False))
    return g.to_dict("records")


def sub_reason_breakdown(**filters) -> list[dict[str, Any]]:
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if c.empty:
        return []
    reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in c.columns else "CNCL_RSN_DESC"
    if reason_col not in c.columns:
        return []
    sub_col = next((k for k in ("CNCL_RSN_SUB_DESC", "CNCL_SUB_RSN_DESC",
                                "CNCL_SUB_RSN", "SUB_REASON")
                    if k in c.columns), None)
    if sub_col is None:
        return []
    c = c.assign(cancel_qty=_first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    g = (c.groupby([reason_col, sub_col], as_index=False)
          .agg(cancel_qty=("cancel_qty", "sum"))
          .rename(columns={reason_col: "reason", sub_col: "sub_reason"})
          .sort_values("cancel_qty", ascending=False)
          .head(20))
    g["reason"]      = g["reason"].fillna("(unknown)").astype(str)
    g["sub_reason"]  = g["sub_reason"].fillna("(unknown)").astype(str)
    g["reason_full"] = g["reason"] + " — " + g["sub_reason"]
    return g[["reason", "sub_reason", "reason_full", "cancel_qty"]].to_dict("records")


def cancel_lag_distribution(**filters) -> list[dict[str, Any]]:
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if c.empty or "lag_days" not in c.columns:
        return []
    c = c.assign(cancel_qty=_first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    bins = (c.groupby("lag_days", as_index=False)
              .agg(cancel_qty=("cancel_qty", "sum"))
              .sort_values("lag_days")
              .head(30))
    bins["lag_days"]   = bins["lag_days"].astype(int)
    bins["cancel_qty"] = bins["cancel_qty"].astype(int)
    return bins.to_dict("records")


def product_breakdown(top_n: int = 20, sort_by: str = "qty", **filters) -> list[dict[str, Any]]:
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if c.empty:
        return []
    c = c.assign(
        cancel_qty=_first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY"),
        cancel_amt=_ensure_amounts(c, "CNCL_QTY"),
    )
    group_cols = [col for col in ("ITEM_ID", "PRODUCT_NAME", "DEPARTMENT", "CATEGORY")
                  if col in c.columns]
    if not group_cols:
        return []
    g = (c.groupby(group_cols, as_index=False, dropna=False)
          .agg(cancel_qty=("cancel_qty", "sum"), cancel_amt=("cancel_amt", "sum"))
          .sort_values("cancel_amt" if sort_by == "amt" else "cancel_qty", ascending=False)
          .head(top_n))
    return g.assign(cancel_amt=lambda x: x["cancel_amt"].round(2)).to_dict("records")


def category_breakdown(**filters) -> list[dict[str, Any]]:
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if c.empty:
        return []
    cols = [col for col in ("DEPARTMENT", "CATEGORY") if col in c.columns]
    if not cols:
        return []
    c = c.assign(cancel_qty=_first_col(c, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    g = (c.groupby(cols, as_index=False, dropna=False)
          .agg(cancel_qty=("cancel_qty", "sum"))
          .sort_values("cancel_qty", ascending=False))
    return g.to_dict("records")


# ──────────────────────────────────────────────────────────────────────────────
# Inventory correlation
# ──────────────────────────────────────────────────────────────────────────────

def inventory_diagnostics(**filters) -> dict[str, Any]:
    """Inventory cross-reference and data-quality diagnostics.

    The inventory feed does not carry STATE/REGION columns, so we resolve the
    active store set from the store dimension via _filter_inventory(),
    ensuring every bucket count and per-store stockout rate respects the
    sidebar's state/region/store/date filters.
    """
    d = get_data()
    c, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    store = d["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    inv = _filter_inventory(d["inventory"], store, **filters)
    if inv is None or inv.empty:
        return {
            "oos_paradox": {"matched_to_inventory": 0, "positive_at_snapshot": 0,
                            "positive_at_cancel": 0},
            "bucket_distribution": [],
            "stockout_by_store": [],
            "zero_stock_by_store": [],
            "negative_inv_records": 0,
            "_granularity": "date",
        }

    on_hand_col = next((k for k in ("ON_HAND_QTY", "ON_HAND", "INVENTORY_QTY", "QTY_ON_HAND")
                        if k in inv.columns), None)
    if on_hand_col is None:
        on_hand_col = "ON_HAND_QTY"
        inv[on_hand_col] = 0

    has_cancels = (not c.empty) and ("ORDER_DT" in c.columns)
    bucket_dist: list[dict] = []
    matched = positive_at_snapshot = 0

    if has_cancels:
        c2 = c.copy()
        c2["__date"] = pd.to_datetime(c2["ORDER_DT"]).dt.normalize()
        inv2 = inv.copy()
        inv2["__date"] = pd.to_datetime(inv2["GREGORIAN_DATE"]).dt.normalize()
        merged = c2.merge(
            inv2[["STORE_NUM", "ITEM_ID", "__date", on_hand_col]],
            on=["STORE_NUM", "ITEM_ID", "__date"], how="left"
        )

        def bucket(v: float) -> str:
            if pd.isna(v):
                return "Unknown"
            if v < 0:
                return "Negative"
            if v == 0:
                return "Zero"
            if v <= 10:
                return "Low (1-10)"
            if v <= 50:
                return "Medium (11-50)"
            return "High (50+)"

        merged["bucket"] = merged[on_hand_col].apply(bucket)
        merged["cancel_qty"] = _first_col(merged, "CNCL_QTY", "CANCEL_QTY", "QTY")
        bucket_dist = (merged.groupby("bucket", as_index=False)
                              .agg(cancel_qty=("cancel_qty", "sum"))
                              .to_dict("records"))

        oos_reasons = ["Out Of Stock", "Out Of Stock Cancellation"]
        rsn_series = merged.get("CNCL_RSN_DESC", pd.Series([], dtype=str))
        oos_rows = merged[rsn_series.isin(oos_reasons)]
        matched = int(oos_rows[on_hand_col].notna().sum())
        positive_at_snapshot = int((oos_rows[on_hand_col] > 0).sum())

    inv_clean = inv.dropna(subset=[on_hand_col])
    is_zero  = inv_clean[on_hand_col] == 0
    per_store = (inv_clean.assign(_zero=is_zero.astype(int))
                          .groupby("STORE_NUM", as_index=False)
                          .agg(zero_events=("_zero", "sum"),
                               total_snapshots=("_zero", "count")))
    per_store["zero_rate_pct"] = np.where(
        per_store["total_snapshots"] > 0,
        per_store["zero_events"] / per_store["total_snapshots"] * 100,
        0.0,
    ).round(2)
    per_store["zero_events"]     = per_store["zero_events"].astype(int)
    per_store["total_snapshots"] = per_store["total_snapshots"].astype(int)
    stockout_df = (per_store.merge(store, on="STORE_NUM", how="left")
                              .sort_values("zero_rate_pct", ascending=False)
                              .head(20))
    stockout_df["store_label"] = stockout_df.apply(_make_store_label, axis=1)
    stockout_by_store = stockout_df.to_dict("records")

    neg_records = int((inv[on_hand_col] < 0).sum())

    return {
        "oos_paradox": {
            "matched_to_inventory": matched,
            "positive_at_snapshot": positive_at_snapshot,
            "positive_at_cancel":   positive_at_snapshot,
        },
        "bucket_distribution": bucket_dist,
        "stockout_by_store":   stockout_by_store,
        "zero_stock_by_store": stockout_by_store,
        "negative_inv_records": neg_records,
        "_granularity": "date",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Save-rate proxy — of OOS-flagged cancels, what fraction had at least one
# alternate SKU in the same category at the same store with positive inventory
# on the same day? Quantifies the "we could have offered a swap" opportunity.
# ──────────────────────────────────────────────────────────────────────────────

def save_rate_proxy(**filters) -> dict[str, Any]:
    """Estimate the share of OOS cancellations that could plausibly have been
    saved by offering a substitute.

    Criterion for "savable": the cancelled OOS line has at least one OTHER
    SKU in the same CATEGORY at the same STORE_NUM on the same ORDER_DT
    snapshot with ON_HAND > 0. If yes, a substitution flow could have
    intervened in principle.

    Returns:
      total_oos_cancels:    count of OOS-flagged cancel rows in scope
      savable_count:        of those, count with an in-stock category mate
      savable_share_pct:    savable_count / total_oos_cancels * 100
      savable_units:        sum of cancel_qty for the savable subset
      savable_revenue:      sum of cancel_amt for the savable subset
      total_oos_units / total_oos_revenue: denominators for context
      examples:             top 5 high-revenue savable rows for the demo
      severity:             info / medium / high based on share
      _note:                caveats (granularity, parity, category criterion)

    Caveats (returned in ``_note`` for UI surfacing):
      - Inventory is a daily snapshot — a SKU positive at start-of-day may
        have been depleted by the cancel moment.
      - Substitution credibility requires same CATEGORY, not just same
        DEPARTMENT. Same-product would be tautological.
      - Price / size / pack-count parity is not enforced; this is a
        directional proxy, not a fulfilment-grade match.
    """
    d = get_data()
    canc, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    store_dim = d["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    inv = _filter_inventory(d["inventory"], store_dim, **filters)

    empty = {
        "total_oos_cancels": 0, "savable_count": 0, "savable_share_pct": 0.0,
        "savable_units": 0, "savable_revenue": 0.0,
        "total_oos_units": 0, "total_oos_revenue": 0.0,
        "examples": [], "severity": "info",
        "_note": ("Save-rate proxy requires a same-category, in-stock alternate "
                  "SKU at the same store on the same day."),
    }
    if canc.empty or inv is None or inv.empty:
        return empty
    if "CATEGORY" not in canc.columns or "CNCL_RSN_DESC" not in canc.columns:
        return empty

    oos_reasons = ["Out Of Stock", "Out Of Stock Cancellation"]
    oos = canc[canc["CNCL_RSN_DESC"].isin(oos_reasons)].copy()
    if oos.empty:
        return empty

    oos = oos.assign(
        cancel_qty=_first_col(oos, "CNCL_QTY", "CANCEL_QTY", "QTY"),
        cancel_amt=_ensure_amounts(oos, "CNCL_QTY"),
    )
    oos["__date"] = pd.to_datetime(oos["ORDER_DT"]).dt.normalize()

    on_hand_col = next((k for k in ("ON_HAND_QTY", "ON_HAND", "INVENTORY_QTY", "QTY_ON_HAND")
                        if k in inv.columns), None)
    if on_hand_col is None:
        return empty

    # Join CATEGORY onto the inventory feed (it doesn't ship with one)
    product = d["product"][["ITEM_ID", "CATEGORY", "PRODUCT_NAME"]].drop_duplicates("ITEM_ID")
    inv_cat = inv[["STORE_NUM", "ITEM_ID", "GREGORIAN_DATE", on_hand_col]].copy()
    inv_cat = inv_cat.merge(product[["ITEM_ID", "CATEGORY"]], on="ITEM_ID", how="left")
    inv_cat["__date"] = pd.to_datetime(inv_cat["GREGORIAN_DATE"]).dt.normalize()

    in_stock = inv_cat[inv_cat[on_hand_col] > 0]
    # {(store, date, category): set of item_ids with stock}
    key_to_items: dict[tuple, set] = (
        in_stock.groupby(["STORE_NUM", "__date", "CATEGORY"])["ITEM_ID"]
                .apply(lambda s: set(s.dropna()))
                .to_dict()
    )

    def alts_for(row):
        items = key_to_items.get((row["STORE_NUM"], row["__date"], row["CATEGORY"]))
        if not items:
            return set()
        return items - {row["ITEM_ID"]}

    oos["__alts"] = oos.apply(alts_for, axis=1)
    oos["has_substitute"] = oos["__alts"].apply(len) > 0

    total_oos     = int(len(oos))
    savable_count = int(oos["has_substitute"].sum())
    savable_share = (savable_count / total_oos * 100) if total_oos > 0 else 0.0
    savable_units = int(oos.loc[oos["has_substitute"], "cancel_qty"].sum())
    savable_rev   = float(oos.loc[oos["has_substitute"], "cancel_amt"].sum())
    total_units   = int(oos["cancel_qty"].sum())
    total_rev     = float(oos["cancel_amt"].sum())

    # Build 5 high-impact savable examples for the demo
    examples: list[dict] = []
    sample = oos[oos["has_substitute"]].nlargest(5, "cancel_amt") if savable_count else oos.iloc[0:0]
    name_lookup = product.set_index("ITEM_ID")["PRODUCT_NAME"].to_dict() if "PRODUCT_NAME" in product.columns else {}
    for _, row in sample.iterrows():
        alts = row["__alts"]
        alt_id = next(iter(alts), None) if alts else None
        examples.append({
            "store_num":         int(row["STORE_NUM"]),
            "store_label":       _make_store_label(row),
            "date":              row["__date"].strftime("%Y-%m-%d"),
            "category":          str(row.get("CATEGORY") or ""),
            "cancelled_sku":     str(row.get("PRODUCT_NAME") or ""),
            "alternative_count": int(len(alts)),
            "example_alternative": str(name_lookup.get(alt_id, "")) if alt_id is not None else "",
            "units_cancelled":   int(row["cancel_qty"]),
            "revenue_at_risk":   round(float(row["cancel_amt"]), 2),
        })

    if savable_share >= 50:
        severity, icon = "high", "💰"
    elif savable_share >= 25:
        severity, icon = "medium", "🔄"
    else:
        severity, icon = "info", "ℹ️"

    return {
        "total_oos_cancels":  total_oos,
        "savable_count":      savable_count,
        "savable_share_pct":  round(savable_share, 1),
        "savable_units":      savable_units,
        "savable_revenue":    round(savable_rev, 2),
        "total_oos_units":    total_units,
        "total_oos_revenue":  round(total_rev, 2),
        "examples":           examples,
        "severity":           severity,
        "icon":               icon,
        "_note": ("Same-day inventory granularity; same-CATEGORY substitution "
                  "criterion; price / size / pack-count parity not enforced."),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Product lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def product_status_breakdown(new_launch_window_days: int = 30, **filters) -> dict[str, Any]:
    d = get_data()
    canc, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    empty = {"summary": [], "top_discontinued": [], "top_new_launch": [],
             "new_launch_window_days": new_launch_window_days,
             "_note": "ACTIVE_STATUS is a snapshot at extract time/day, not a historical reading."}
    if canc.empty:
        return empty

    product = d["product"]
    if product is None or product.empty or "ACTIVE_STATUS" not in product.columns:
        empty["_note"] = "ACTIVE_STATUS column not present in product dimension."
        return empty

    canc = canc.assign(
        cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"),
        cancel_amt=_ensure_amounts(canc, "CNCL_QTY"),
    )

    prod_cols = ["ITEM_ID", "ACTIVE_STATUS"]
    if "ACTIVE_DATE" in product.columns:
        prod_cols.append("ACTIVE_DATE")
    enriched = canc.merge(product[prod_cols].drop_duplicates("ITEM_ID"),
                          on="ITEM_ID", how="left", suffixes=("", "_prod"))

    if "ACTIVE_DATE" in enriched.columns:
        enriched["ACTIVE_DATE"] = pd.to_datetime(enriched["ACTIVE_DATE"], errors="coerce")
        enriched["ORDER_DT_norm"] = pd.to_datetime(enriched["ORDER_DT"]).dt.normalize()
        enriched["days_since_activation"] = (
            enriched["ORDER_DT_norm"] - enriched["ACTIVE_DATE"]
        ).dt.days
    else:
        enriched["days_since_activation"] = np.nan

    def _bucket(row):
        status = row.get("ACTIVE_STATUS")
        if pd.isna(status):
            return "unknown"
        if status == "D":
            return "discontinued"
        days = row.get("days_since_activation")
        if pd.notna(days) and 0 <= days <= new_launch_window_days:
            return "new_launch"
        return "established"

    enriched["bucket"] = enriched.apply(_bucket, axis=1)

    summary = (enriched.groupby("bucket", as_index=False)
                       .agg(cancel_qty=("cancel_qty", "sum"),
                            cancel_amt=("cancel_amt", "sum")))
    total_qty = float(summary["cancel_qty"].sum())
    summary["share_pct"] = np.where(
        total_qty > 0, summary["cancel_qty"] / total_qty * 100, 0
    ).round(2)
    summary["cancel_qty"] = summary["cancel_qty"].astype(int)
    summary["cancel_amt"] = summary["cancel_amt"].round(2)

    def _top_in(bucket: str, n: int = 10):
        rows = enriched[enriched["bucket"] == bucket]
        if rows.empty:
            return []
        cols = ["ITEM_ID"]
        if "PRODUCT_NAME" in rows.columns: cols.append("PRODUCT_NAME")
        if "DEPARTMENT"   in rows.columns: cols.append("DEPARTMENT")
        if "CATEGORY"     in rows.columns: cols.append("CATEGORY")
        out = (rows.groupby(cols, as_index=False, dropna=False)
                   .agg(cancel_qty=("cancel_qty", "sum"),
                        cancel_amt=("cancel_amt", "sum"))
                   .sort_values("cancel_qty", ascending=False)
                   .head(n))
        out["cancel_amt"] = out["cancel_amt"].round(2)
        return out.to_dict("records")

    return {
        "summary": summary.to_dict("records"),
        "top_discontinued": _top_in("discontinued"),
        "top_new_launch":   _top_in("new_launch"),
        "new_launch_window_days": new_launch_window_days,
        "_note": "ACTIVE_STATUS is a snapshot at extract time, not a historical reading.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# State-level cancel rate for US choropleth
# ──────────────────────────────────────────────────────────────────────────────

def state_breakdown(**filters) -> list[dict[str, Any]]:
    rows = store_breakdown(**filters)
    if not rows:
        return []
    df = pd.DataFrame(rows)
    if "STATE" not in df.columns:
        return []
    g = (df.groupby("STATE", as_index=False)
           .agg(order_qty=("order_qty", "sum"),
                cancel_qty=("cancel_qty", "sum"),
                cancel_amt=("cancel_amt", "sum"),
                stores=("STORE_NUM", "nunique")))
    g["cancel_rate"] = np.where(
        g["order_qty"] > 0, g["cancel_qty"] / g["order_qty"] * 100, 0
    ).round(2)
    g["cancel_qty"] = g["cancel_qty"].astype(int)
    g["order_qty"] = g["order_qty"].astype(int)
    g["cancel_amt"] = g["cancel_amt"].round(2)
    return g.sort_values("cancel_rate", ascending=False).to_dict("records")


# ──────────────────────────────────────────────────────────────────────────────
# Store × Department heatmap — surfaces whether a high-rate store's problem
# is concentrated in one department or broad-based
# ──────────────────────────────────────────────────────────────────────────────

def store_dept_heatmap(top_stores: int = 15, **filters) -> dict[str, Any]:
    """Cancel rate by store × department, with raw unit counts for hover.

    Helps answer "is Store X's problem a single category or systemic across
    every department?" — which determines whether the right intervention is
    a SKU-level fix (buyer / catalogue) or a store-level fix (ops / staffing).

    Returns long-form rows so the frontend can pivot for either heatmap or
    tabular rendering, plus ordered axis labels:
      - rows: [{STORE_NUM, store_label, DEPARTMENT, cancel_qty, order_qty, cancel_rate}]
      - stores: [{STORE_NUM, store_label}] ordered by total cancelled units desc
      - departments: [str] ordered by total cancelled units desc

    ``cancel_rate`` is ``None`` when ``order_qty`` is zero for that cell, so
    the frontend can render an empty / muted cell instead of a misleading 0%.
    Stores are capped at ``top_stores`` (default 15) to keep the chart legible.
    """
    d = get_data()
    canc, ord = _apply_filters(d["cancels"], d["orders"], **filters)
    if canc.empty or "DEPARTMENT" not in canc.columns:
        return {"rows": [], "stores": [], "departments": []}

    canc = canc.assign(cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    ord  = ord.assign(order_qty=_first_col(ord, "ORDER_QTY", "QTY", "PLCD_QTY"))

    # Orders aren't pre-merged with the product dim, so we need to join
    # DEPARTMENT onto them ourselves.
    if "DEPARTMENT" not in ord.columns:
        product = d["product"][["ITEM_ID", "DEPARTMENT"]].drop_duplicates("ITEM_ID")
        ord = ord.merge(product, on="ITEM_ID", how="left")

    cg = (canc.groupby(["STORE_NUM", "DEPARTMENT"], as_index=False, dropna=False)
              .agg(cancel_qty=("cancel_qty", "sum")))
    og = (ord.groupby(["STORE_NUM", "DEPARTMENT"], as_index=False, dropna=False)
              .agg(order_qty=("order_qty", "sum")))

    merged = cg.merge(og, on=["STORE_NUM", "DEPARTMENT"], how="outer").fillna(0)
    merged["cancel_rate"] = np.where(
        merged["order_qty"] > 0,
        (merged["cancel_qty"] / merged["order_qty"] * 100).round(2),
        np.nan,
    )

    store_dim = d["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    merged = merged.merge(store_dim, on="STORE_NUM", how="left")
    merged["store_label"] = merged.apply(_make_store_label, axis=1)

    store_totals = (merged.groupby("STORE_NUM", as_index=False)
                          .agg(total=("cancel_qty", "sum"))
                          .sort_values("total", ascending=False)
                          .head(top_stores))
    keep = store_totals["STORE_NUM"].tolist()
    merged = merged[merged["STORE_NUM"].isin(keep)]

    store_order = (merged.groupby(["STORE_NUM", "store_label"], as_index=False, dropna=False)
                          .agg(total=("cancel_qty", "sum"))
                          .sort_values("total", ascending=False))
    dept_order = (merged.groupby("DEPARTMENT", as_index=False, dropna=False)
                          .agg(total=("cancel_qty", "sum"))
                          .sort_values("total", ascending=False))

    out_rows = merged[["STORE_NUM", "store_label", "DEPARTMENT",
                       "cancel_qty", "order_qty", "cancel_rate"]].copy()
    out_rows["cancel_qty"] = out_rows["cancel_qty"].astype(int)
    out_rows["order_qty"]  = out_rows["order_qty"].astype(int)
    out_rows["DEPARTMENT"] = out_rows["DEPARTMENT"].fillna("(unknown)").astype(str)
    out_rows["cancel_rate"] = out_rows["cancel_rate"].astype(object).where(
        out_rows["cancel_rate"].notna(), None
    )

    return {
        "rows": out_rows.to_dict("records"),
        "stores": store_order[["STORE_NUM", "store_label"]].assign(
            STORE_NUM=lambda x: x["STORE_NUM"].astype(int)
        ).to_dict("records"),
        "departments": dept_order["DEPARTMENT"].fillna("(unknown)").astype(str).tolist(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Reason × Day-of-Week heatmap
# ──────────────────────────────────────────────────────────────────────────────

def reason_dow_heatmap(**filters) -> dict[str, Any]:
    d = get_data()
    canc, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    if canc.empty:
        return {"rows": [], "reasons": [], "days": []}

    reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in canc.columns else "CNCL_RSN_DESC"
    if reason_col not in canc.columns:
        return {"rows": [], "reasons": [], "days": []}
    if "order_dow" not in canc.columns:
        canc = canc.assign(order_dow=pd.to_datetime(canc["ORDER_DT"]).dt.day_name())

    canc = canc.assign(cancel_qty=_first_col(canc, "CNCL_QTY", "CANCEL_QTY", "QTY"))
    g = (canc.groupby([reason_col, "order_dow"], as_index=False)
              .agg(cancel_qty=("cancel_qty", "sum"))
              .rename(columns={reason_col: "reason", "order_dow": "day"}))
    g["cancel_qty"] = g["cancel_qty"].astype(int)

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    reason_order = (canc.groupby(reason_col)["cancel_qty"].sum()
                          .sort_values(ascending=False).index.tolist())
    return {"rows": g.to_dict("records"), "reasons": reason_order, "days": days}


# ──────────────────────────────────────────────────────────────────────────────
# Data quality scorecard
# ──────────────────────────────────────────────────────────────────────────────

def data_quality_report(**filters) -> dict[str, Any]:
    d = get_data()
    canc, _ = _apply_filters(d["cancels"], d["orders"], **filters)
    store = d["store"][["STORE_NUM", "CITY", "STATE", "REGION"]].drop_duplicates()
    inv = _filter_inventory(d["inventory"], store, **filters)
    product = d["product"]
    checks: list[dict] = []

    def add(name, value, total, description, severity_thresholds=(0.05, 0.20)):
        total = int(total or 0)
        value = int(value or 0)
        share = (value / total * 100) if total else 0.0
        if total == 0:
            sev = "info"
        elif share >= severity_thresholds[1] * 100:
            sev = "high"
        elif share >= severity_thresholds[0] * 100:
            sev = "medium"
        else:
            sev = "info"
        checks.append({
            "name": name, "value": value, "total": total,
            "share_pct": round(share, 2), "severity": sev,
            "description": description,
        })

    on_hand_col = next((k for k in ("ON_HAND_QTY", "ON_HAND", "INVENTORY_QTY", "QTY_ON_HAND")
                        if k in inv.columns), None) if inv is not None and not inv.empty else None
    if on_hand_col and len(inv):
        add("Negative inventory records",
            int((inv[on_hand_col] < 0).sum()), len(inv),
            "Inventory rows with on-hand below zero — should not be physically possible.",
            severity_thresholds=(0.001, 0.01))

    if (not canc.empty) and inv is not None and (not inv.empty):
        inv_keys = set(zip(
            inv["STORE_NUM"], inv["ITEM_ID"],
            pd.to_datetime(inv["GREGORIAN_DATE"]).dt.normalize()
        ))
        canc_norm = pd.to_datetime(canc["ORDER_DT"]).dt.normalize()
        miss = sum(
            1 for sn, it, dt in zip(canc["STORE_NUM"], canc["ITEM_ID"], canc_norm)
            if (sn, it, dt) not in inv_keys
        )
        add("Cancels with no matching inventory snapshot",
            miss, len(canc),
            "Cancellations whose order date has no inventory row — limits OOS analysis.",
            severity_thresholds=(0.20, 0.50))

    if "CNCL_RSN_SUB_DESC" in canc.columns and len(canc):
        add("Cancels with no sub-reason",
            int(canc["CNCL_RSN_SUB_DESC"].isna().sum()), len(canc),
            "Cancels lacking a sub-reason force coarser root-cause analysis.",
            severity_thresholds=(0.20, 0.50))

    if product is not None and not product.empty:
        for col in ("PRODUCT_NAME", "BRAND", "CATEGORY", "DEPARTMENT"):
            if col in product.columns:
                add(f"Products missing {col}",
                    int(product[col].isna().sum()), len(product),
                    f"Catalogue rows lacking {col} produce labelling gaps in aggregations.",
                    severity_thresholds=(0.05, 0.20))

    if on_hand_col and len(inv):
        implausible = int((inv[on_hand_col] > 100_000).sum())
        if implausible > 0:
            add("Implausibly large inventory rows",
                implausible, len(inv),
                "On-hand quantities above 100,000 may indicate unit or feed errors.",
                severity_thresholds=(0.001, 0.01))

    overall_sev = "info"
    if any(c["severity"] == "high" for c in checks):
        overall_sev = "high"
    elif any(c["severity"] == "medium" for c in checks):
        overall_sev = "medium"

    return {"checks": checks, "overall_severity": overall_sev,
            "_granularity": "date"}


# ──────────────────────────────────────────────────────────────────────────────
# Data context summary for LLMs
# ──────────────────────────────────────────────────────────────────────────────

def build_data_context_summary() -> str:
    try:
        kpis = overview_kpis()
        stores = store_breakdown()[:5]
        regions = region_breakdown()
        reasons = reason_breakdown()[:6]
        products = product_breakdown(top_n=5)
        inv = inventory_diagnostics()

        store_lines = "\n".join(
            f"  - {s.get('store_label') or _make_store_label(s)}: rate {s['cancel_rate']}%, "
            f"{s['cancel_qty']:.0f} units, ${s['cancel_amt']:,.0f} at risk"
            for s in stores
        )
        region_lines = "\n".join(
            f"  - Region {r.get('REGION','')}: {r['cancel_rate']}% ({r['cancel_qty']:.0f} units)"
            for r in regions
        )
        reason_lines = "\n".join(
            f"  - {r['reason']}: {r['cancel_qty']:.0f} units"
            for r in reasons
        )
        product_lines = "\n".join(
            f"  - {p.get('PRODUCT_NAME','')[:60]} ({p.get('DEPARTMENT','')}/{p.get('CATEGORY','')}): "
            f"{p['cancel_qty']:.0f} units cancelled"
            for p in products
        )

        oos = inv.get("oos_paradox", {})
        return f"""You are a retail analytics assistant. Use ONLY the facts below to answer.
Cite specific numbers, stores, and products. Do not invent values.

OVERALL KPIs (filters: none / full period):
  - Orders placed (units):   {kpis['total_order_units']:,.0f}
  - Cancelled units:         {kpis['total_cancel_units']:,.0f}
  - Cancel rate (units):     {kpis['cancel_rate_units']}%
  - Cancel rate (revenue):   {kpis['cancel_rate_revenue']}%
  - Revenue at risk:         ${kpis['total_cancel_revenue']:,.0f}

TOP STORES BY CANCEL RATE:
{store_lines or '  (none)'}

REGIONS:
{region_lines or '  (none)'}

TOP CANCEL REASONS:
{reason_lines or '  (none)'}

TOP CANCELLED PRODUCTS:
{product_lines or '  (none)'}

INVENTORY / OOS DIAGNOSTICS:
  - OOS-flagged cancels matched to inventory rows: {oos.get('matched_to_inventory', 0)}
  - Of those, with POSITIVE on-hand at order time: {oos.get('positive_at_cancel', 0)} (data quality concern)
  - Negative inventory records overall:            {inv.get('negative_inv_records', 0)}

When asked for recommendations, prioritise actions tied to the highest-rate stores and the
products driving the most cancelled units. Flag the OOS data-quality concern when relevant.
"""
    except Exception as e:
        return f"Retail cancellation dataset is loaded but summary generation failed: {e}"


# ──────────────────────────────────────────────────────────────────────────────
# Data-derived headline insights
# ──────────────────────────────────────────────────────────────────────────────

def derived_insights(**filters) -> dict[str, Any]:
    out: dict[str, Any] = {}

    # 1) Highest-rate store vs network average
    stores = store_breakdown(**filters)
    if stores:
        total_canc = sum(s.get("cancel_qty", 0) for s in stores)
        total_ord  = sum(s.get("order_qty",  0) for s in stores)
        avg_rate = (total_canc / total_ord * 100) if total_ord else 0.0
        top = max(stores, key=lambda s: s.get("cancel_rate", 0))
        rate = float(top.get("cancel_rate", 0))
        ratio = (rate / avg_rate) if avg_rate else 0.0

        if rate > avg_rate * 1.5 and rate > 5:
            severity, icon = "high", "\U0001F6A8"
        elif rate > avg_rate * 1.2:
            severity, icon = "medium", "⚠️"
        else:
            severity, icon = "info", "ℹ️"

        comparison = (
            f"{ratio:.1f}× the network average ({avg_rate:.1f}%)"
            if avg_rate else "the highest in the dataset"
        )

        store_label = top.get("store_label") or _make_store_label(top)
        out["top_store"] = {
            "severity": severity,
            "icon": icon,
            "text": (
                f"{store_label} is at {rate:.1f}% cancel rate — {comparison}. "
                f"Immediate investigation recommended."
            ),
            "store_num": int(top["STORE_NUM"]),
            "store_label": store_label,
            "rate": round(rate, 2),
            "avg_rate": round(avg_rate, 2),
            "ratio": round(ratio, 2),
        }

    # 2) Same-day cancellation share
    lag_rows = cancel_lag_distribution(**filters)
    if lag_rows:
        total = sum(r.get("cancel_qty", 0) for r in lag_rows)
        same_day = sum(r.get("cancel_qty", 0) for r in lag_rows if r.get("lag_days", -1) == 0)
        if total > 0:
            share = same_day / total * 100
            severity = "info" if share < 50 else "medium"
            tail = (
                "This points to demand-side changes rather than fulfilment failures "
                "as the primary driver."
                if share >= 50 else
                "Most cancels arrive after the order day — investigate fulfilment "
                "and stockouts."
            )
            out["same_day_share"] = {
                "severity": severity,
                "icon": "⏱",
                "text": f"{share:.0f}% of cancellations happen same-day as the order. {tail}",
                "share": round(share, 1),
            }

    # 3) Product concentration
    cats  = category_breakdown(**filters)
    prods = product_breakdown(top_n=1, **filters)
    if cats and prods:
        total = sum(c.get("cancel_qty", 0) for c in cats)
        top_cat = max(cats, key=lambda c: c.get("cancel_qty", 0))
        cat_share = (top_cat.get("cancel_qty", 0) / total * 100) if total else 0.0
        top_sku = prods[0]
        sku_name = (top_sku.get("PRODUCT_NAME") or "").strip()
        sku_qty  = top_sku.get("cancel_qty", 0)

        severity = "high" if cat_share >= 40 else ("medium" if cat_share >= 20 else "info")
        icon = "\U0001F4A7" if "WATER" in (top_cat.get("CATEGORY") or "").upper() else "\U0001F4E6"

        out["product_concentration"] = {
            "severity": severity,
            "icon": icon,
            "text": (
                f"{top_cat.get('CATEGORY','(unknown)')} accounts for ~{cat_share:.0f}% of "
                f"all cancelled units. Top SKU '{sku_name[:60]}' alone "
                f"drove {sku_qty:,.0f} cancelled units."
            ),
            "category": top_cat.get("CATEGORY"),
            "category_share": round(cat_share, 1),
            "top_sku": sku_name,
            "top_sku_qty": int(sku_qty),
        }

    # 4) OOS data quality
    inv = inventory_diagnostics(**filters)
    oos = inv.get("oos_paradox", {}) if isinstance(inv, dict) else {}
    matched = int(oos.get("matched_to_inventory", 0) or 0)
    positive = int(oos.get("positive_at_cancel", 0) or 0)
    if matched > 0:
        share = positive / matched * 100
        if share >= 50:
            severity, icon = "high", "🔴"
        elif share >= 20:
            severity, icon = "medium", "🟠"
        else:
            severity, icon = "info", "ℹ️"
        out["oos_data_quality"] = {
            "severity": severity,
            "icon": icon,
            "text": (
                f"OOS Data Quality: {positive:,} of {matched:,} OOS-flagged cancels "
                f"({share:.0f}%) had POSITIVE inventory at order time. "
                + ("The OOS reason code cannot be trusted without data pipeline fixes."
                   if share >= 50 else
                   "Some OOS cancels look mis-coded — review the reason taxonomy.")
            ),
            "matched": matched,
            "positive": positive,
            "share": round(share, 1),
        }

    # 5) Negative inventory records
    inv_for_neg = inv if isinstance(inv, dict) else inventory_diagnostics(**filters)
    neg_records = int(inv_for_neg.get("negative_inv_records", 0) or 0)
    if neg_records > 0:
        if neg_records >= 500:
            severity, icon = "high", "🚨"
        elif neg_records >= 100:
            severity, icon = "medium", "⚠️"
        else:
            severity, icon = "info", "ℹ️"
        out["negative_inventory"] = {
            "severity": severity,
            "icon": icon,
            "text": (
                f"{neg_records:,} inventory records show negative on-hand "
                "quantities — a data-pipeline integrity issue that undermines "
                "OOS analysis reliability."
            ),
            "neg_records": neg_records,
        }

    # 6) Save-rate proxy — substitution opportunity
    save = save_rate_proxy(**filters)
    if save.get("total_oos_cancels", 0) > 0 and save.get("savable_count", 0) > 0:
        share = float(save.get("savable_share_pct", 0))
        out["save_rate_opportunity"] = {
            "severity": save.get("severity", "info"),
            "icon": save.get("icon", "💰"),
            "text": (
                f"{share:.0f}% of OOS cancels ({save['savable_count']:,} of "
                f"{save['total_oos_cancels']:,}) had an in-stock same-category "
                f"alternate SKU at the same store on the same day — a proxy for "
                f"${save['savable_revenue']:,.0f} of revenue a substitution flow "
                f"could plausibly have saved."
            ),
            "savable_share_pct": share,
            "savable_revenue": save["savable_revenue"],
            "savable_units":   save["savable_units"],
            "total_oos_cancels": save["total_oos_cancels"],
        }

    return out
