"""GET /api/analytics/* — KPI and analytics endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..pipeline import metrics
from ..pipeline.loader import get_ingestion_status

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _parse(stores: str, regions: str, date_from: str, date_to: str,
           reasons: str, states: str = "") -> dict:
    """Translate query strings into kwargs for metrics functions."""
    return {
        "stores":    [int(x) for x in stores.split(",") if x.strip().isdigit()] if stores else [],
        "regions":   [r.strip() for r in regions.split(",") if r.strip()] if regions else [],
        "states":    [s.strip() for s in states.split(",") if s.strip()] if states else [],
        "date_from": date_from or None,
        "date_to":   date_to or None,
        "reasons":   [r.strip() for r in reasons.split("|") if r.strip()] if reasons else [],
    }


@router.get("/filters")
def filters():
    return metrics.get_filter_options()


@router.get("/overview")
def overview(stores: str = "", regions: str = "", date_from: str = "",
             date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.overview_kpis(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/trends/weekly")
def trends_weekly(stores: str = "", regions: str = "", date_from: str = "",
                  date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.weekly_trend(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/trends/dow")
def trends_dow(stores: str = "", regions: str = "", date_from: str = "",
               date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.dow_trend(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/stores")
def stores_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                    date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.store_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/regions")
def regions_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                     date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.region_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/reasons")
def reasons_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                     date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.reason_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/reasons/sub")
def reasons_sub(stores: str = "", regions: str = "", date_from: str = "",
                date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.sub_reason_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/cancels/lag")
def cancel_lag(stores: str = "", regions: str = "", date_from: str = "",
               date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.cancel_lag_distribution(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/products")
def products_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                      date_to: str = "", reasons: str = "", states: str = "",
                      top_n: int = Query(20, ge=1, le=100),
                      sort_by: str = Query("qty", regex="^(qty|amt)$")):
    """Top products by cancelled units (default) or by cancelled revenue (sort_by=amt)."""
    return metrics.product_breakdown(
        top_n=top_n, sort_by=sort_by,
        **_parse(stores, regions, date_from, date_to, reasons, states),
    )


@router.get("/categories")
def categories_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                        date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.category_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/inventory")
def inventory_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                       date_to: str = "", reasons: str = "", states: str = ""):
    return metrics.inventory_diagnostics(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/save-rate")
def save_rate_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                        date_to: str = "", reasons: str = "", states: str = ""):
    """Save-rate proxy: of OOS-flagged cancellations, what fraction had at
    least one alternate SKU in the same category at the same store with
    positive inventory on the same day? Quantifies the revenue a substitution
    flow could plausibly have recovered."""
    return metrics.save_rate_proxy(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/ingestion")
def ingestion_status():
    return get_ingestion_status()


@router.get("/insights")
async def insights_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                            date_to: str = "", reasons: str = "", states: str = ""):
    """Headline narrative insights derived from the current filter set."""
    from ..ai.narrator import narrate_dict
    return await narrate_dict(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/products/status")
def product_status(stores: str = "", regions: str = "", date_from: str = "",
                   date_to: str = "", reasons: str = "", states: str = "",
                   window_days: int = Query(30, ge=1, le=365)):
    """Cancels classified by product lifecycle (discontinued / new launch / established)."""
    return metrics.product_status_breakdown(
        new_launch_window_days=window_days,
        **_parse(stores, regions, date_from, date_to, reasons, states),
    )


@router.get("/states")
def states_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                    date_to: str = "", reasons: str = "", states: str = ""):
    """Per-state cancel rate for the US choropleth."""
    return metrics.state_breakdown(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/heatmap/reason-dow")
def reason_dow_heatmap(stores: str = "", regions: str = "", date_from: str = "",
                       date_to: str = "", reasons: str = "", states: str = ""):
    """Cancel volume by parent reason x order day-of-week."""
    return metrics.reason_dow_heatmap(**_parse(stores, regions, date_from, date_to, reasons, states))


@router.get("/heatmap/store-dept")
def store_dept_heatmap_endpoint(stores: str = "", regions: str = "", date_from: str = "",
                                date_to: str = "", reasons: str = "", states: str = "",
                                top_stores: int = Query(15, ge=1, le=50)):
    """Store x Department cancel-rate heatmap — surfaces whether a high-rate
    store's problem is concentrated in one department or systemic."""
    return metrics.store_dept_heatmap(
        top_stores=top_stores,
        **_parse(stores, regions, date_from, date_to, reasons, states),
    )


@router.get("/data-quality")
def data_quality(stores: str = "", regions: str = "", date_from: str = "",
                 date_to: str = "", reasons: str = "", states: str = ""):
    """Centralised data-integrity checks across all source tables."""
    return metrics.data_quality_report(**_parse(stores, regions, date_from, date_to, reasons, states))
