import pandas as pd
import numpy as np
from pathlib import Path
from functools import lru_cache
import os
import json

from dotenv import load_dotenv

load_dotenv()  

DATA_PATH      = Path(__file__).parent.parent.parent / "data" / "data.xlsx"
PROCESSED_DIR  = Path(__file__).parent.parent.parent / "data" / "processed"
MANIFEST_PATH  = PROCESSED_DIR / "manifest.json"

PROCESSED_TABLES = ["orders","cancels","inventory","store","product","calendar"]


def _processed_files_available() -> bool:
    """Return True if all required parquet files exist from the ingestion notebook."""
    return all((PROCESSED_DIR / f"{t}.parquet").exists() for t in PROCESSED_TABLES)


def _load_from_parquet() -> dict:
    """Load pre-processed parquet files written by the ingestion notebook."""
    sheets = {}
    for name in PROCESSED_TABLES:
        path = PROCESSED_DIR / f"{name}.parquet"
        sheets[name] = pd.read_parquet(path, engine="pyarrow")
    return sheets


def _load_from_excel() -> dict:
    """Fallback: load and minimally parse the raw Excel workbook."""
    raw = pd.read_excel(DATA_PATH, sheet_name=None)
    return {k.lower(): v for k, v in raw.items()}


@lru_cache(maxsize=1)
def load_all_sheets() -> dict:
    # ── Prefer processed parquet files from ingestion notebook ───────────────
    using_processed = _processed_files_available()
    source = "parquet (processed)" if using_processed else "raw Excel"
    print(f"[loader] Loading data from: {source}")

    if using_processed:
        raw = _load_from_parquet()
        orders    = raw["orders"].copy()
        cancels   = raw["cancels"].copy()
        inventory = raw["inventory"].copy()
        store     = raw["store"].copy()
        product   = raw["product"].copy()
        calendar  = raw["calendar"].copy()

        # Ensure datetime types (parquet preserves these but guard anyway)
        orders["ORDER_DT"]          = pd.to_datetime(orders["ORDER_DT"])
        cancels["ORDER_DT"]         = pd.to_datetime(cancels["ORDER_DT"])
        cancels["CANCEL_DT"]        = pd.to_datetime(cancels["CANCEL_DT"])
        inventory["GREGORIAN_DATE"] = pd.to_datetime(inventory["GREGORIAN_DATE"])

        # Derived fields expected by metrics layer
        if "lag_days" not in cancels.columns:
            cancels["lag_days"] = cancels.get("CANCEL_LAG_DAYS",
                (cancels["CANCEL_DT"] - cancels["ORDER_DT"]).dt.days)
        else:
            cancels["lag_days"] = cancels["lag_days"]

        if "order_week" not in cancels.columns:
            cancels["order_week"]  = cancels["ORDER_DT"].dt.to_period("W").astype(str)
        if "order_dow" not in cancels.columns:
            cancels["order_dow"]   = cancels["ORDER_DT"].dt.day_name()
        if "order_month" not in cancels.columns:
            cancels["order_month"] = cancels["ORDER_DT"].dt.to_period("M").astype(str)

    else:
        # Fallback: raw Excel with minimal parsing
        raw = _load_from_excel()
        orders    = raw.get("orders",    raw.get("Orders", pd.DataFrame())).copy()
        cancels   = raw.get("cancels",   raw.get("Cancels", pd.DataFrame())).copy()
        inventory = raw.get("inventory", raw.get("Inventory", pd.DataFrame())).copy()
        store     = raw.get("store",     raw.get("Store", pd.DataFrame())).copy()
        product   = raw.get("product",   raw.get("Product", pd.DataFrame())).copy()
        calendar  = raw.get("calendar",  raw.get("Calendar", pd.DataFrame())).copy()

        orders["ORDER_DT"]          = pd.to_datetime(orders["ORDER_DT"])
        cancels["ORDER_DT"]         = pd.to_datetime(cancels["ORDER_DT"])
        cancels["CANCEL_DT"]        = pd.to_datetime(cancels["CANCEL_DT"])
        inventory["GREGORIAN_DATE"] = pd.to_datetime(inventory["GREGORIAN_DATE"])
        if "Date" in calendar.columns:
            calendar = calendar.rename(columns={"Date": "CAL_DATE"})
        elif "DATE" in calendar.columns:
            calendar = calendar.rename(columns={"DATE": "CAL_DATE"})

        cancels["lag_days"]   = (cancels["CANCEL_DT"] - cancels["ORDER_DT"]).dt.days
        cancels["order_week"] = cancels["ORDER_DT"].dt.to_period("W").astype(str)
        cancels["order_dow"]  = cancels["ORDER_DT"].dt.day_name()
        cancels["order_month"]= cancels["ORDER_DT"].dt.to_period("M").astype(str)

    # ── Build enriched views (same logic regardless of source) ────────────────
    # Use cleaned reason code if available (produced by notebook), else raw
    reason_col = "CNCL_RSN_DESC_CLEAN" if "CNCL_RSN_DESC_CLEAN" in cancels.columns else "CNCL_RSN_DESC"
    oos_reasons = ["Out Of Stock", "Out Of Stock Cancellation"]
    cancels_full = (
        cancels
        .merge(product[["ITEM_ID","PRODUCT_NAME","DEPARTMENT","CATEGORY","BRAND","UNIT_COST"]],
               on="ITEM_ID", how="left")
        .merge(store, on="STORE_NUM", how="left")
    )
    if "is_oos" not in cancels_full.columns:
        cancels_full["is_oos"] = cancels_full["CNCL_RSN_DESC"].isin(oos_reasons)

    orders_full = orders.merge(store, on="STORE_NUM", how="left")

    return {
        "orders":       orders_full,
        "cancels":      cancels_full,
        "inventory":    inventory,
        "store":        store,
        "product":      product,
        "calendar":     calendar,
        "_source":      "parquet" if using_processed else "excel",
    }


def get_data():
    return load_all_sheets()


def get_ingestion_status() -> dict:
    """Return status of the processed data files for API consumers."""
    available = _processed_files_available()
    status = {
        "processed_files_available": available,
        "data_source": "parquet" if available else "raw_excel",
        "processed_dir": str(PROCESSED_DIR),
        "tables": {}
    }
    for name in PROCESSED_TABLES:
        path = PROCESSED_DIR / f"{name}.parquet"
        status["tables"][name] = {
            "exists": path.exists(),
            "size_kb": round(path.stat().st_size / 1024, 1) if path.exists() else None
        }
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        status["generated_at"] = manifest.get("generated_at")
        status["quality_summary"] = {
            "total_checks": len(manifest.get("quality_report", [])),
            "passed": sum(1 for c in manifest.get("quality_report", []) if "PASS" in c.get("status","")),
            "failed": sum(1 for c in manifest.get("quality_report", []) if "FAIL" in c.get("status","")),
        }
    return status
