import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/client";
import { RI, SEVERITY, SUGGESTION_CATEGORIES } from "./theme";
import { ModelConfig, ModelBadge, JudgePanel } from "./components/ModelConfig";
import { InsightCard } from "./components/InsightCard";
import { RecommendationCard } from "./components/RecommendationCard";
import { FilterBar } from "./components/FilterBar";

function KpiCard({ label, value, sub, accent = RI.teal }) {
  return (
    <div style={{
      background: "white", borderRadius: 14, padding: "20px 24px",
      borderLeft: `5px solid ${accent}`,
      boxShadow: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06)",
      flex: 1, minWidth: 160,
    }}>
      <div style={{ fontSize: "1.9rem", fontWeight: 700, color: RI.blue,
                    letterSpacing: "-0.02em", lineHeight: 1.1,
                    fontFamily: "'Plus Jakarta Sans', Inter, sans-serif" }}>{value}</div>
      <div style={{ fontSize: "0.82rem", color: RI.muted, marginTop: 4, fontWeight: 500 }}>{label}</div>
      {sub && <div style={{ fontSize: "0.75rem", color: "#999", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function SectionHeader({ children }) {
  return (
    <div style={{
      fontFamily: "'Plus Jakarta Sans', Inter, sans-serif",
      fontSize: "1.35rem", fontWeight: 700, color: RI.blue,
      margin: "26px 0 14px", letterSpacing: "-0.01em",
      borderBottom: `2px solid ${RI.teal}`, paddingBottom: 8,
    }}>{children}</div>
  );
}

function Chip({ children, color = RI.teal }) {
  return (
    <span style={{
      background: `${color}20`, color, padding: "2px 10px",
      borderRadius: 12, fontSize: "0.72rem", fontWeight: 600, marginRight: 6,
    }}>{children}</span>
  );
}

function useFetch(fetcher, deps = []) {
  const [data, setData] = useState(null);
  useEffect(() => {
    let cancelled = false;
    fetcher().then((d) => { if (!cancelled) setData(d); }).catch(console.error);
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data };
}

const TABS = [
  { id: "overview", label: "📊 Overview" },
  { id: "where", label: "📍 Where" },
  { id: "why", label: "🔍 Why" },
  { id: "products", label: "🛒 Products" },
  { id: "inventory", label: "📦 Inventory" },
  { id: "data_quality", label: "🧪 Data Quality" },
  { id: "ai", label: "🤖 AI Insights" },
];

// ─────────────────────────────────────────────────────────────────────────────
// Small chart primitives — SVG bar+line and CSS bars
// ─────────────────────────────────────────────────────────────────────────────

function WeeklyTrendChart({ data }) {
  if (!data?.length) return null;
  const W = 1000, H = 400, padL = 50, padR = 50, padT = 16, padB = 36;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const maxQty = Math.max(1, ...data.map((d) => d.cancel_qty));
  const maxAmt = Math.max(1, ...data.map((d) => d.cancel_amt));
  const barW = plotW / data.length * 0.7;
  const stepX = plotW / data.length;
  const x = (i) => padL + i * stepX + stepX / 2;
  const yQty = (v) => padT + plotH - (v / maxQty) * plotH;
  const yAmt = (v) => padT + plotH - (v / maxAmt) * plotH;
  const linePath = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yAmt(d.cancel_amt).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H + 8}
         style={{ background: "white", borderRadius: 12,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
      {/* grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <line key={t} x1={padL} x2={W - padR}
              y1={padT + plotH * (1 - t)} y2={padT + plotH * (1 - t)}
              stroke="#EEF1F5" strokeWidth="1" />
      ))}
      {/* bars (qty) */}
      {data.map((d, i) => (
        <rect key={i} x={x(i) - barW / 2} y={yQty(d.cancel_qty)}
              width={barW} height={padT + plotH - yQty(d.cancel_qty)}
              fill={RI.teal} opacity="0.85" rx="3" />
      ))}
      {/* line (revenue) */}
      <path d={linePath} fill="none" stroke={RI.red} strokeWidth="2.5" />
      {data.map((d, i) => (
        <circle key={i} cx={x(i)} cy={yAmt(d.cancel_amt)} r="3.5"
                fill={RI.red} stroke="white" strokeWidth="1.5" />
      ))}
      {/* x labels (show every Nth so they don't overlap) */}
      {data.map((d, i) => {
        const skip = Math.max(1, Math.floor(data.length / 12));
        if (i % skip !== 0) return null;
        const lbl = String(d.order_week || "").slice(0, 10);
        return (
          <text key={i} x={x(i)} y={H - 8} fontSize="9" textAnchor="middle"
                fill={RI.muted}>{lbl}</text>
        );
      })}
      {/* y axes labels */}
      <text x={padL - 8} y={padT + 4} fontSize="9" textAnchor="end" fill={RI.teal}>
        {maxQty.toLocaleString()}
      </text>
      <text x={padL - 8} y={padT + plotH} fontSize="9" textAnchor="end" fill={RI.teal}>0</text>
      <text x={W - padR + 8} y={padT + 4} fontSize="9" textAnchor="start" fill={RI.red}>
        ${maxAmt.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </text>
      {/* legend */}
      <g transform={`translate(${padL}, ${padT - 4})`}>
        <rect x="0" y="-10" width="10" height="10" fill={RI.teal} opacity="0.85" rx="2" />
        <text x="14" y="-1" fontSize="10" fill={RI.muted}>Units cancelled</text>
        <line x1="110" y1="-5" x2="125" y2="-5" stroke={RI.red} strokeWidth="2.5" />
        <text x="130" y="-1" fontSize="10" fill={RI.muted}>Revenue at risk ($)</text>
      </g>
    </svg>
  );
}

function DowBars({ data }) {
  if (!data?.length) return null;
  const max = Math.max(1, ...data.map((d) => d.cancel_qty));
  return (
    <div style={{ background: "white", borderRadius: 12, padding: 16,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
      {data.map((d) => (
        <div key={d.day} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <div style={{ width: 90, fontSize: "0.85rem", color: "#333", fontWeight: 500 }}>{d.day}</div>
          <div style={{ flex: 1, background: "#F0F4F8", borderRadius: 6, height: 22 }}>
            <div style={{ width: `${(d.cancel_qty / max * 100).toFixed(1)}%`,
                          background: RI.blue, borderRadius: 6, height: "100%" }} />
          </div>
          <div style={{ width: 80, textAlign: "right", fontSize: "0.82rem",
                        fontWeight: 700, color: RI.blue }}>
            {d.cancel_qty?.toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Risk dashboard tile — compact summary of one insight
// ─────────────────────────────────────────────────────────────────────────────

function RiskTile({ insight, label }) {
  if (!insight) return null;
  const sev = SEVERITY[insight.severity] || SEVERITY.info;
  return (
    <div style={{
      background: sev.bg, borderLeft: `4px solid ${sev.color}`,
      borderRadius: 12, padding: "14px 18px", flex: 1, minWidth: 240,
    }}>
      <div style={{ fontSize: "0.72rem", color: RI.muted, fontWeight: 600,
                    textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: "1.3rem" }}>{insight.icon}</span>
        <span style={{
          background: `${sev.color}20`, color: sev.color,
          padding: "1px 8px", borderRadius: 10,
          fontSize: "0.68rem", fontWeight: 700, textTransform: "uppercase",
        }}>{insight.severity}</span>
      </div>
      <div style={{ fontSize: "0.82rem", color: "#444", lineHeight: 1.45 }}>
        {insight.text}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Overview tab — KPIs, risk dashboard, weekly trend, DOW + reasons, full insights
// ─────────────────────────────────────────────────────────────────────────────

function OverviewTab({ filters, insights }) {
  const fkey = JSON.stringify(filters);
  const { data: overview } = useFetch(() => api.getOverview(filters), [fkey]);
  const { data: reasons }  = useFetch(() => api.getReasons(filters),  [fkey]);
  const { data: weekly }   = useFetch(() => api.getWeekly(filters),   [fkey]);
  const { data: dow }      = useFetch(() => api.getDow(filters),      [fkey]);

  if (!overview) return <div style={{ color: RI.muted }}>Loading overview…</div>;

  const insightKeys = ["top_store", "product_concentration", "same_day_share",
                       "oos_data_quality", "negative_inventory"];
  const labels = {
    top_store:             "Worst-rate store",
    product_concentration: "Top category",
    same_day_share:        "Same-day share",
    oos_data_quality:      "OOS data quality",
    negative_inventory:    "Negative inventory",
  };
  const tiles = insightKeys
    .filter((k) => insights?.[k])
    .slice(0, 4);

  return (
    <>
      <SectionHeader>Headline metrics</SectionHeader>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
        <KpiCard label="Orders Placed"   value={overview.total_order_units?.toLocaleString()} />
        <KpiCard label="Units Cancelled" value={overview.total_cancel_units?.toLocaleString()} accent={RI.red} />
        <KpiCard label="Cancel Rate"     value={`${overview.cancel_rate_units}%`} sub="by units" accent={RI.amber} />
        <KpiCard label="Revenue at Risk" value={`$${overview.total_cancel_revenue?.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} accent={RI.red} />
        <KpiCard label="Cancel Rate $"   value={`${overview.cancel_rate_revenue}%`} sub="by revenue" accent={RI.amber} />
      </div>

      {tiles.length > 0 && (
        <>
          <SectionHeader>Risk Dashboard</SectionHeader>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 8 }}>
            {tiles.map((k) => (
              <RiskTile key={k} insight={insights[k]} label={labels[k]} />
            ))}
          </div>
        </>
      )}

      <SectionHeader>Weekly Cancellation Trend</SectionHeader>
      <WeeklyTrendChart data={weekly} />
      <div style={{ fontSize: "0.78rem", color: RI.muted, marginTop: 6 }}>
        Bars = units cancelled · Line = revenue at risk ($). Both update with the active filter set.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
                    gap: 18, marginTop: 24 }}>
        <div>
          <SectionHeader>Day-of-Week Pattern</SectionHeader>
          <DowBars data={dow} />
        </div>
        <div>
          <SectionHeader>Top Cancel Reasons</SectionHeader>
          <div style={{ background: "white", borderRadius: 12, padding: 16,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            {reasons?.slice(0, 8).map((r, i) => {
              const max = reasons[0]?.cancel_qty || 1;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                  <div style={{ width: 220, fontSize: "0.85rem", color: "#333", flexShrink: 0 }}>{r.reason}</div>
                  <div style={{ flex: 1, background: "#F0F4F8", borderRadius: 6, height: 20 }}>
                    <div style={{ width: `${(r.cancel_qty / max * 100).toFixed(1)}%`,
                      background: i === 0 ? RI.teal : i < 3 ? RI.amber : "#B0C9E0",
                      borderRadius: 6, height: "100%" }} />
                  </div>
                  <div style={{ width: 70, textAlign: "right", fontSize: "0.82rem",
                                fontWeight: 700, color: RI.blue }}>
                    {r.cancel_qty?.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <SectionHeader>Headline Insights</SectionHeader>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))",
                    gap: 12 }}>
        {insightKeys.map((k) => insights?.[k] && (
          <InsightCard key={k} insight={insights[k]} />
        ))}
      </div>
    </>
  );
}

function WhereTab({ filters, insights }) {
  const { data: stores }    = useFetch(() => api.getStores(filters),    [JSON.stringify(filters)]);
  const { data: states }    = useFetch(() => api.getStates(filters),    [JSON.stringify(filters)]);
  const { data: regions }   = useFetch(() => api.getRegions(filters),   [JSON.stringify(filters)]);
  const { data: storeDept } = useFetch(() => api.getStoreDept(filters), [JSON.stringify(filters)]);
  return (
    <>
      <SectionHeader>Cancel Rate by State</SectionHeader>
      {states?.length > 0 ? (
        <div style={{ background: "white", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ background: RI.blue, color: "white" }}>
                {["State", "Cancel Rate", "Cancel Qty", "Order Qty", "Stores"].map((h) => (
                  <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {states.map((s) => {
                const c = s.cancel_rate >= 7 ? RI.red : s.cancel_rate >= 5 ? RI.amber : RI.green;
                return (
                  <tr key={s.STATE} style={{ borderBottom: "1px solid #EEE" }}>
                    <td style={{ padding: "8px 14px", fontWeight: 600 }}>{s.STATE}</td>
                    <td style={{ padding: "8px 14px", color: c, fontWeight: 700 }}>{s.cancel_rate?.toFixed(2)}%</td>
                    <td style={{ padding: "8px 14px" }}>{s.cancel_qty?.toLocaleString()}</td>
                    <td style={{ padding: "8px 14px" }}>{s.order_qty?.toLocaleString()}</td>
                    <td style={{ padding: "8px 14px", color: RI.muted }}>{s.stores}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : <div style={{ color: RI.muted }}>Loading state breakdown…</div>}
      <SectionHeader>Store Cancel Rates</SectionHeader>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 14 }}>
        {(stores || []).slice().sort((a, b) => b.cancel_rate - a.cancel_rate).map((s) => {
          const rate = s.cancel_rate || 0;
          const color = rate >= 7 ? RI.red : rate >= 5 ? RI.amber : RI.green;
          return (
            <div key={s.STORE_NUM} style={{
              background: "white", borderRadius: 12, padding: "16px 20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)", borderLeft: `4px solid ${color}`,
            }}>
              <div style={{ fontWeight: 700, color: RI.blue, marginBottom: 4 }}>
                {s.store_label || `Store ${s.STORE_NUM} — ${s.CITY}, ${s.STATE}`}
              </div>
              <div style={{ fontSize: "0.82rem", color: RI.muted, marginBottom: 10 }}>
                {s.orders?.toLocaleString() || 0} orders · {s.cancels?.toLocaleString() || 0} cancels
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div>
                  <div style={{ fontSize: "1.5rem", fontWeight: 700, color }}>{rate.toFixed(1)}%</div>
                  <div style={{ fontSize: "0.75rem", color: "#888" }}>cancel rate</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontWeight: 600 }}>{s.cancel_qty?.toLocaleString()} units</div>
                  <div style={{ fontSize: "0.75rem", color: "#888" }}>
                    ${s.cancel_amt?.toLocaleString(undefined, { maximumFractionDigits: 0 })} at risk
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {regions?.length > 0 && (
        <>
          <SectionHeader>Regional Summary</SectionHeader>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {regions.map((r) => (
              <div key={r.REGION} style={{
                background: "white", padding: "12px 18px", borderRadius: 10,
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)", minWidth: 160,
              }}>
                <div style={{ fontWeight: 700, color: RI.blue }}>Region {r.REGION}</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: RI.amber }}>{r.cancel_rate}%</div>
                <div style={{ fontSize: "0.75rem", color: RI.muted }}>{r.cancel_qty?.toLocaleString()} units</div>
              </div>
            ))}
          </div>
        </>
      )}
      {insights?.top_store && <InsightCard insight={insights.top_store} />}

      <SectionHeader>Store × Department Concentration</SectionHeader>
      <div style={{ color: RI.muted, fontSize: "0.85rem", marginBottom: 10 }}>
        A single hot cell suggests a SKU or category intervention; a hot row across many
        departments suggests a store-level operational fix.
      </div>
      <StoreDeptHeatmap data={storeDept} />
    </>
  );
}

function StoreDeptHeatmap({ data }) {
  if (!data || !data.rows?.length) {
    return <div style={{ color: RI.muted }}>Loading store × department breakdown…</div>;
  }
  const { rows, stores, departments } = data;
  if (!stores?.length || !departments?.length) {
    return <div style={{ color: RI.muted }}>No data under the current filter set.</div>;
  }

  // Index rows for O(1) cell lookup
  const lookup = {};
  for (const r of rows) lookup[`${r.STORE_NUM}|${r.DEPARTMENT}`] = r;

  // 95th-percentile cap so one outlier cell doesn't flatten everything else.
  const numericRates = rows.map((r) => r.cancel_rate).filter((v) => v != null);
  numericRates.sort((a, b) => a - b);
  const p95 = numericRates.length
    ? numericRates[Math.min(numericRates.length - 1, Math.floor(numericRates.length * 0.95))]
    : 10;
  const zmax = Math.max(p95, 5);

  // Color ramp green → amber → red, anchored at 0 and zmax.
  const colorFor = (rate) => {
    if (rate == null) return "#EEE";
    const t = Math.max(0, Math.min(1, rate / zmax));
    // Interpolate green(2A9D8F) -> amber(F4A261) at 0.4 -> red(E63946) at 1.0
    const lerp = (a, b, k) => Math.round(a + (b - a) * k);
    const stops = [
      [0.0, [42, 157, 143]],
      [0.4, [244, 162, 97]],
      [1.0, [230, 57, 70]],
    ];
    for (let i = 0; i < stops.length - 1; i++) {
      const [t0, c0] = stops[i];
      const [t1, c1] = stops[i + 1];
      if (t >= t0 && t <= t1) {
        const k = (t - t0) / (t1 - t0);
        const [r, g, b] = [0, 1, 2].map((j) => lerp(c0[j], c1[j], k));
        return `rgb(${r},${g},${b})`;
      }
    }
    return "rgb(230,57,70)";
  };

  const ROW_H = 28;
  const STORE_COL_W = 240;
  const DEPT_COL_W = Math.max(72, Math.min(140, Math.floor(900 / departments.length)));

  return (
    <div style={{ overflowX: "auto", background: "white", borderRadius: 10,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)", padding: 12 }}>
      <table style={{ borderCollapse: "separate", borderSpacing: 2 }}>
        <thead>
          <tr>
            <th style={{ width: STORE_COL_W, textAlign: "left", padding: "6px 8px",
                          fontSize: "0.78rem", color: RI.muted, fontWeight: 600 }}>
              Store
            </th>
            {departments.map((d) => (
              <th key={d} style={{
                width: DEPT_COL_W, padding: "6px 4px",
                fontSize: "0.72rem", fontWeight: 600, color: RI.blue,
                writingMode: "horizontal-tb", textAlign: "center",
                verticalAlign: "bottom", lineHeight: 1.15,
              }}>
                {d}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stores.map((s) => (
            <tr key={s.STORE_NUM}>
              <td style={{ padding: "4px 8px", fontSize: "0.8rem", fontWeight: 600,
                            whiteSpace: "nowrap" }}>
                {s.store_label}
              </td>
              {departments.map((d) => {
                const cell = lookup[`${s.STORE_NUM}|${d}`];
                const rate = cell?.cancel_rate;
                const bg = colorFor(rate);
                const textColor = rate == null ? "#999"
                  : (rate / zmax > 0.5 ? "white" : "#222");
                const tooltip = rate == null
                  ? `${s.store_label}\n${d}\nNo orders`
                  : `${s.store_label}\n${d}\nRate: ${rate.toFixed(1)}%\nCancels: ${cell.cancel_qty?.toLocaleString()}\nOrders: ${cell.order_qty?.toLocaleString()}`;
                return (
                  <td key={d} title={tooltip} style={{
                    width: DEPT_COL_W, height: ROW_H,
                    background: bg, color: textColor,
                    textAlign: "center", fontSize: "0.78rem", fontWeight: 600,
                    borderRadius: 4,
                  }}>
                    {rate != null ? `${rate.toFixed(1)}` : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12,
                     fontSize: "0.75rem", color: RI.muted }}>
        <span>0%</span>
        <div style={{ flex: 1, height: 10, borderRadius: 4,
                       background: "linear-gradient(90deg, rgb(42,157,143) 0%, rgb(244,162,97) 40%, rgb(230,57,70) 100%)" }} />
        <span>{zmax.toFixed(0)}%+</span>
      </div>
    </div>
  );
}

function WhyTab({ filters, insights }) {
  const { data: sub }     = useFetch(() => api.getSubReasons(filters), [JSON.stringify(filters)]);
  const { data: lag }     = useFetch(() => api.getLag(filters),        [JSON.stringify(filters)]);
  const { data: heatmap } = useFetch(() => api.getReasonDow(filters),  [JSON.stringify(filters)]);
  const hp = useMemo(() => {
    if (!heatmap?.rows) return null;
    const reasons = (heatmap.reasons || []).slice(0, 8);
    const days = heatmap.days || [];
    const pivot = {}; let max = 0;
    for (const r of heatmap.rows) {
      if (!reasons.includes(r.reason)) continue;
      pivot[r.reason] ??= {};
      pivot[r.reason][r.day] = r.cancel_qty;
      if (r.cancel_qty > max) max = r.cancel_qty;
    }
    return { reasons, days, pivot, max: max || 1 };
  }, [heatmap]);
  return (
    <>
      <SectionHeader>Sub-Reasons (top 20)</SectionHeader>
      <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
        {(sub || []).map((s, i) => {
          const max = sub[0]?.cancel_qty || 1;
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
              <div style={{ width: 260, fontSize: "0.82rem" }}>
                <div style={{ fontWeight: 600, color: RI.blue }}>{s.sub_reason}</div>
                <div style={{ fontSize: "0.72rem", color: RI.muted }}>{s.reason}</div>
              </div>
              <div style={{ flex: 1, background: "#F0F4F8", borderRadius: 6, height: 18 }}>
                <div style={{ width: `${(s.cancel_qty / max * 100).toFixed(1)}%`, background: RI.teal, borderRadius: 6, height: "100%" }} />
              </div>
              <div style={{ width: 60, textAlign: "right", fontSize: "0.82rem", fontWeight: 700 }}>
                {s.cancel_qty?.toLocaleString()}
              </div>
            </div>
          );
        })}
      </div>
      {hp && (
        <>
          <SectionHeader>Cancel Reason × Day-of-Week Heatmap</SectionHeader>
          <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.05)", overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", fontSize: "0.78rem", width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ padding: "6px 10px", textAlign: "left", color: RI.muted }}>Reason</th>
                  {hp.days.map((d) => <th key={d} style={{ padding: "6px 10px", color: RI.muted }}>{d.slice(0, 3)}</th>)}
                </tr>
              </thead>
              <tbody>
                {hp.reasons.map((r) => (
                  <tr key={r}>
                    <td style={{ padding: "6px 10px", fontWeight: 600, color: RI.blue }}>{r}</td>
                    {hp.days.map((d) => {
                      const v = hp.pivot[r]?.[d] || 0;
                      const intensity = v / hp.max;
                      return (
                        <td key={d} style={{
                          padding: "10px 10px", textAlign: "center", fontWeight: 600,
                          background: `rgba(27,58,107,${intensity * 0.85})`,
                          color: intensity > 0.4 ? "white" : RI.blue, minWidth: 56,
                        }}>{v.toLocaleString()}</td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <SectionHeader>Time-to-Cancel Distribution</SectionHeader>
      {lag?.length > 0 && (
        <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
          {lag.map((row) => {
            const max = Math.max(...lag.map((r) => r.cancel_qty));
            return (
              <div key={row.lag_days} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
                <div style={{ width: 60, fontSize: "0.82rem", color: RI.muted }}>{row.lag_days}d</div>
                <div style={{ flex: 1, background: "#F0F4F8", borderRadius: 6, height: 16 }}>
                  <div style={{ width: `${(row.cancel_qty / max * 100).toFixed(1)}%`, background: RI.blue, borderRadius: 6, height: "100%" }} />
                </div>
                <div style={{ width: 60, textAlign: "right", fontSize: "0.78rem", fontWeight: 600 }}>
                  {row.cancel_qty?.toLocaleString()}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {insights?.same_day_share   && <InsightCard insight={insights.same_day_share} />}
      {insights?.oos_data_quality && <InsightCard insight={insights.oos_data_quality} />}
    </>
  );
}

function ProductsTab({ filters, insights }) {
  const [sortBy, setSortBy] = useState("qty");
  const key = JSON.stringify({ filters, sortBy });
  const { data: products }   = useFetch(() => api.getProducts(filters, 20, sortBy), [key]);
  const { data: statusInfo } = useFetch(() => api.getProductStatus(filters), [JSON.stringify(filters)]);
  return (
    <>
      <SectionHeader>Top Cancelled Products</SectionHeader>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {["qty", "amt"].map((mode) => (
          <button key={mode} onClick={() => setSortBy(mode)} style={{
            padding: "6px 14px", borderRadius: 8,
            border: `1px solid ${sortBy === mode ? RI.blue : "#C8D8E8"}`,
            background: sortBy === mode ? RI.blue : "white",
            color: sortBy === mode ? "white" : "#444",
            fontWeight: 600, fontSize: "0.85rem", cursor: "pointer",
          }}>{mode === "qty" ? "By cancelled units" : "By revenue at risk"}</button>
        ))}
      </div>
      <div style={{ background: "white", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ background: RI.blue, color: "white" }}>
              {["Product", "Category", "Department", "Units", "Revenue at Risk"].map((h) => (
                <th key={h} style={{ padding: "12px 14px", textAlign: "left", fontWeight: 600 }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(products || []).map((p, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? "#F7F9FC" : "white", borderBottom: "1px solid #E2EAF4" }}>
                <td style={{ padding: "10px 14px", color: "#333", maxWidth: 320 }}>
                  {String(p.PRODUCT_NAME || "").slice(0, 60)}
                  {String(p.PRODUCT_NAME || "").length > 60 ? "…" : ""}
                </td>
                <td style={{ padding: "10px 14px", color: "#555" }}>{p.CATEGORY}</td>
                <td style={{ padding: "10px 14px" }}><Chip>{p.DEPARTMENT}</Chip></td>
                <td style={{ padding: "10px 14px", fontWeight: 700, color: RI.red }}>{p.cancel_qty?.toLocaleString()}</td>
                <td style={{ padding: "10px 14px" }}>${p.cancel_amt?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SectionHeader>Product Lifecycle — Discontinued vs Active</SectionHeader>
      {statusInfo?.summary?.length > 0 ? (
        <>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {statusInfo.summary.map((row) => {
              const colorMap = { discontinued: RI.red, new_launch: RI.amber, established: RI.green, unknown: "#888" };
              const labelMap = {
                discontinued: "Discontinued",
                new_launch:   `New launch (≤${statusInfo.new_launch_window_days}d)`,
                established:  "Established active",
                unknown:      "Unknown",
              };
              const color = colorMap[row.bucket] || RI.teal;
              return (
                <div key={row.bucket} style={{
                  background: "white", padding: "14px 18px", borderRadius: 10,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)", borderLeft: `4px solid ${color}`, minWidth: 200,
                }}>
                  <div style={{ fontSize: "0.78rem", color: RI.muted, fontWeight: 600 }}>{labelMap[row.bucket] || row.bucket}</div>
                  <div style={{ fontSize: "1.6rem", fontWeight: 700, color }}>{row.cancel_qty?.toLocaleString()}</div>
                  <div style={{ fontSize: "0.78rem", color: RI.muted }}>
                    {row.share_pct}% • ${row.cancel_amt?.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                </div>
              );
            })}
          </div>
          {statusInfo._note && (
            <div style={{ marginTop: 10, fontSize: "0.78rem", color: RI.muted }}>Note: {statusInfo._note}</div>
          )}
          {(statusInfo.top_discontinued || []).length > 0 && (
            <>
              <div style={{ marginTop: 20, fontWeight: 700, color: RI.blue }}>
                Top discontinued SKUs still being cancelled
              </div>
              <div style={{ background: "white", borderRadius: 10, overflow: "hidden", marginTop: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
                  <thead>
                    <tr style={{ background: "#F0F4F8" }}>
                      {["Product", "Category", "Units", "Revenue"].map((h) => (
                        <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: RI.muted }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {statusInfo.top_discontinued.slice(0, 8).map((p, i) => (
                      <tr key={i} style={{ borderTop: "1px solid #EEE" }}>
                        <td style={{ padding: "8px 12px" }}>{String(p.PRODUCT_NAME || "(no name)").slice(0, 60)}</td>
                        <td style={{ padding: "8px 12px", color: RI.muted }}>{p.CATEGORY}</td>
                        <td style={{ padding: "8px 12px", fontWeight: 700, color: RI.red }}>{p.cancel_qty?.toLocaleString()}</td>
                        <td style={{ padding: "8px 12px" }}>${p.cancel_amt?.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      ) : <div style={{ color: RI.muted }}>Loading lifecycle data…</div>}
      {insights?.product_concentration && <InsightCard insight={insights.product_concentration} />}
    </>
  );
}

function InventoryTab({ filters, insights }) {
  const { data: inv }  = useFetch(() => api.getInventory(filters), [JSON.stringify(filters)]);
  const { data: save } = useFetch(() => api.getSaveRate(filters), [JSON.stringify(filters)]);
  if (!inv) return <div style={{ color: RI.muted }}>Loading inventory diagnostics…</div>;
  const buckets = inv.bucket_distribution || [];
  const maxBucket = Math.max(1, ...buckets.map((b) => b.cancel_qty));
  const bucketColor = (name) => ({
    "Zero": "#E63946", "Negative (data error)": "#9B1D20", "Negative": "#9B1D20",
    "Low (1-10)": "#F4A261", "Medium (11-50)": "#00A8E0",
    "High (50+)": "#2A9D8F", "No snapshot": "#CCCCCC", "Unknown": "#CCCCCC",
  })[name] || RI.teal;
  const stockoutRows = inv.stockout_by_store || inv.zero_stock_by_store || [];
  return (
    <>
      <SectionHeader>Cancels by Inventory Level on Order Date</SectionHeader>
      <div style={{ background: "white", borderRadius: 12, padding: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
        {buckets.map((b) => (
          <div key={b.bucket} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
            <div style={{ width: 200, fontSize: "0.85rem", color: RI.blue, fontWeight: 500 }}>{b.bucket}</div>
            <div style={{ flex: 1, background: "#F0F4F8", borderRadius: 6, height: 22 }}>
              <div style={{ width: `${(b.cancel_qty / maxBucket * 100).toFixed(1)}%`, background: bucketColor(b.bucket), borderRadius: 6, height: "100%" }} />
            </div>
            <div style={{ width: 80, textAlign: "right", fontSize: "0.82rem", fontWeight: 700 }}>{b.cancel_qty?.toLocaleString()}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: "0.78rem", color: RI.muted, marginTop: 6 }}>
        Inventory has daily granularity only — the bucket reflects on-hand at the day snapshot.
      </div>
      {stockoutRows.length > 0 && (
        <>
          <SectionHeader>Stockout Rate by Store</SectionHeader>
          <div style={{ background: "white", borderRadius: 12, overflow: "hidden", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: "#F0F4F8" }}>
                  {["Store", "Zero events", "Total snapshots", "Stockout rate"].map((h) => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: RI.muted, fontWeight: 600 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {stockoutRows.slice(0, 10).map((r) => {
                  const rate = r.zero_rate_pct;
                  const color = rate >= 25 ? RI.red : rate >= 10 ? RI.amber : RI.green;
                  return (
                    <tr key={r.STORE_NUM} style={{ borderTop: "1px solid #EEE" }}>
                      <td style={{ padding: "10px 14px", fontWeight: 600 }}>{r.store_label || `Store ${r.STORE_NUM} — ${r.CITY}`}</td>
                      <td style={{ padding: "10px 14px" }}>{r.zero_events?.toLocaleString()}</td>
                      <td style={{ padding: "10px 14px", color: RI.muted }}>{r.total_snapshots?.toLocaleString()}</td>
                      <td style={{ padding: "10px 14px", color, fontWeight: 700 }}>{rate ? `${rate.toFixed(2)}%` : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
      {insights?.negative_inventory && <InsightCard insight={insights.negative_inventory} />}

      <SectionHeader>Save-Rate Proxy — Substitution Opportunity</SectionHeader>
      <div style={{ color: RI.muted, fontSize: "0.85rem", marginBottom: 10 }}>
        For each OOS-flagged cancel, is there another SKU in the same category at the same
        store with positive on-hand the same day? A high share quantifies the revenue a
        substitution flow could plausibly recover. Same-day granularity — directional, not
        fulfilment-grade.
      </div>
      <SaveRatePanel data={save} />
    </>
  );
}

function SaveRatePanel({ data }) {
  if (!data) return <div style={{ color: RI.muted }}>Computing save-rate proxy…</div>;
  if (!data.total_oos_cancels) {
    return (
      <div style={{
        background: "white", padding: "16px 20px", borderRadius: 10,
        boxShadow: "0 1px 3px rgba(0,0,0,0.05)", color: RI.muted, fontSize: "0.88rem",
      }}>
        No OOS-flagged cancellations in scope under the current filter set.
      </div>
    );
  }
  const sev = data.severity || "info";
  const rateColor = sev === "high" ? RI.red : sev === "medium" ? RI.amber : RI.teal;
  const fmt$ = (n) => `$${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  const fmt = (n) => Number(n || 0).toLocaleString();

  const TILES = [
    {
      value: `${(data.savable_share_pct || 0).toFixed(0)}%`, color: rateColor,
      label: "Save-able share", sub: "of OOS cancels",
    },
    {
      value: fmt$(data.savable_revenue), color: RI.blue,
      label: "Recoverable Revenue", sub: `of ${fmt$(data.total_oos_revenue)} OOS revenue`,
    },
    {
      value: fmt(data.savable_units), color: RI.blue,
      label: "Recoverable Units", sub: `${fmt(data.savable_count)} cancel events`,
    },
    {
      value: fmt(data.total_oos_cancels), color: RI.muted,
      label: "OOS Cancels in scope", sub: "denominator",
    },
  ];
  return (
    <>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: 12, marginBottom: 14 }}>
        {TILES.map((t) => (
          <div key={t.label} style={{
            background: "white", padding: "16px 20px", borderRadius: 12,
            boxShadow: "0 1px 3px rgba(0,0,0,0.05)", borderLeft: `5px solid ${t.color}`,
          }}>
            <div style={{ fontSize: "1.7rem", fontWeight: 700, color: t.color, lineHeight: 1.1 }}>
              {t.value}
            </div>
            <div style={{ fontSize: "0.82rem", color: RI.muted, marginTop: 6, fontWeight: 600 }}>
              {t.label}
            </div>
            <div style={{ fontSize: "0.72rem", color: "#999", marginTop: 2 }}>{t.sub}</div>
          </div>
        ))}
      </div>
      {data.examples?.length > 0 && (
        <div style={{ background: "white", borderRadius: 12,
                      boxShadow: "0 1px 3px rgba(0,0,0,0.05)", overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", fontWeight: 700, color: RI.blue,
                        borderBottom: "1px solid #EEE", fontSize: "0.9rem" }}>
            Top recoverable opportunities under the current filter
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
            <thead>
              <tr style={{ background: "#F0F4F8" }}>
                {["Store", "Date", "Category", "Cancelled SKU", "In-stock alternate",
                  "Alts", "Units", "Revenue at risk"].map((h) => (
                  <th key={h} style={{ padding: "8px 12px", textAlign: "left",
                                        color: RI.muted, fontWeight: 600, fontSize: "0.78rem" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.examples.map((ex, i) => (
                <tr key={i} style={{ borderTop: "1px solid #EEE" }}>
                  <td style={{ padding: "8px 12px", fontWeight: 600 }}>{ex.store_label}</td>
                  <td style={{ padding: "8px 12px", color: RI.muted }}>{ex.date}</td>
                  <td style={{ padding: "8px 12px" }}>{ex.category}</td>
                  <td style={{ padding: "8px 12px", maxWidth: 240, overflow: "hidden",
                                textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={ex.cancelled_sku}>{ex.cancelled_sku}</td>
                  <td style={{ padding: "8px 12px", maxWidth: 240, overflow: "hidden",
                                textOverflow: "ellipsis", whiteSpace: "nowrap", color: RI.green }}
                      title={ex.example_alternative}>{ex.example_alternative}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right" }}>{ex.alternative_count}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right" }}>{fmt(ex.units_cancelled)}</td>
                  <td style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600 }}>
                    {fmt$(ex.revenue_at_risk)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data._note && (
        <div style={{ fontSize: "0.75rem", color: RI.muted, marginTop: 8, fontStyle: "italic" }}>
          Caveats: {data._note}
        </div>
      )}
    </>
  );
}

function DataQualityTab({ filters }) {
  const { data: dq } = useFetch(() => api.getDataQuality(filters), [JSON.stringify(filters)]);
  if (!dq) return <div style={{ color: RI.muted }}>Loading data-quality checks…</div>;
  const checks = dq.checks || [];
  const overall = dq.overall_severity || "info";
  const meta = SEVERITY[overall];
  return (
    <>
      <SectionHeader>Data Quality Scorecard</SectionHeader>
      <div style={{ fontSize: "0.88rem", color: RI.muted, marginBottom: 14 }}>
        Integrity signals across all source tables. Severity scales by share of records.
      </div>
      <div style={{
        background: meta.bg, borderLeft: `4px solid ${meta.color}`,
        borderRadius: 10, padding: "14px 18px", marginBottom: 16,
        color: overall === "info" ? RI.blue : "#5a1a1a",
      }}>
        <strong>{meta.icon} Overall data integrity: {overall.toUpperCase()}</strong>
        {" — "}{checks.length} check{checks.length === 1 ? "" : "s"} evaluated.
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
        {checks.map((c, i) => {
          const m = SEVERITY[c.severity] || SEVERITY.info;
          return (
            <div key={i} style={{
              background: m.bg, borderLeft: `4px solid ${m.color}`,
              borderRadius: 10, padding: "14px 18px",
            }}>
              <div style={{ fontSize: "0.72rem", color: RI.muted, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 4 }}>{c.severity}</div>
              <div style={{ fontWeight: 700, color: RI.blue, marginBottom: 8 }}>{c.name}</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: m.color }}>
                {c.value?.toLocaleString()}
                <span style={{ fontSize: "0.78rem", color: "#888", fontWeight: 500 }}>{" / "}{c.total?.toLocaleString()}</span>
              </div>
              <div style={{ fontSize: "0.78rem", color: m.color, fontWeight: 600, marginBottom: 8 }}>{c.share_pct}% of records</div>
              <div style={{ fontSize: "0.8rem", color: "#444", lineHeight: 1.5 }}>{c.description}</div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function AiTab({ filters }) {
  const [messages, setMessages]   = useState([]);
  const [input, setInput]         = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiConfig, setAiConfig]   = useState({
    mode: "single", model: "claude", models: ["claude"],
    enableJudge: false, judgeModel: "claude",
  });
  const msgEnd = useRef(null);
  const { data: recsPayload } = useFetch(() => api.getRecommendations(filters), [JSON.stringify(filters)]);
  const { data: suggPayload } = useFetch(() => api.getSuggestions(filters),     [JSON.stringify(filters)]);
  useEffect(() => { msgEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function sendMessage(text) {
    if (!text.trim() || aiLoading) return;
    const q = text.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: q }]);
    setAiLoading(true);
    try {
      const result = await api.queryInsights({
        question: q,
        history: messages.filter((m) => m.role !== "system"),
        ai_config: {
          mode: aiConfig.mode, model: aiConfig.model,
          models: aiConfig.models, enable_judge: aiConfig.enableJudge,
          judge_model: aiConfig.judgeModel,
        },
        filters,
      });
      setMessages((m) => [...m, {
        role: "assistant", content: result.final_answer,
        model_responses: result.model_responses || [],
        judge_result: result.judge_result || null,
      }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}`, model_responses: [] }]);
    } finally {
      setAiLoading(false);
    }
  }

  const recs        = recsPayload?.recommendations || [];
  const recsLlmUsed = recsPayload?._llm_used;
  const suggestions = suggPayload?.questions || [];
  const suggLlmUsed = suggPayload?._llm_used;

  return (
    <>
      <SectionHeader>Recommended Next Actions</SectionHeader>
      <div style={{ fontSize: "0.85rem", color: RI.muted, marginBottom: 12 }}>
        Prioritised actions inferred from the current filter set. Numbers are code-derived;
        phrasing is LLM-synthesised (deterministic fallback when no key).
      </div>
      {recs.length > 0 ? recs.map((r, i) => (
        <RecommendationCard key={r.id || i} rec={r} position={i + 1} />
      )) : <div style={{ color: RI.muted }}>Loading recommendations…</div>}
      <div style={{ fontSize: "0.78rem", color: RI.muted, marginBottom: 8 }}>
        Source: {recsLlmUsed ? "LLM-synthesised" : "Deterministic fallback"} ·{" "}
        {recs.length} recommendation{recs.length === 1 ? "" : "s"}.
      </div>

      <SectionHeader>Investigation Chat</SectionHeader>
      <ModelConfig config={aiConfig} onChange={setAiConfig} />

      {/* <div style={{
        background: "white", borderRadius: 12, padding: 20,
        boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
        minHeight: 360, maxHeight: 520, overflowY: "auto", marginBottom: 12,
      }}> */}
        {messages.length === 0 && (
          <div style={{ color: "#AAA", textAlign: "center", paddingTop: 60, fontSize: "0.9rem" }}>
            Click a suggested question or type your own to start an investigation.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            {m.role === "user" ? (
              <div style={{
                background: "#EEF6FB", borderRadius: "12px 12px 4px 12px",
                padding: "10px 16px", maxWidth: "70%", marginLeft: "auto",
                fontSize: "0.88rem", color: RI.blue, fontWeight: 500,
              }}>{m.content}</div>
            ) : (
              <div>
                <div style={{ marginBottom: 6 }}>
                  {m.model_responses?.map((r) => <ModelBadge key={r.model} model={r.model} />)}
                </div>
                {m.judge_result && <JudgePanel judgeResult={m.judge_result} />}
                <div style={{
                  background: "#F7F9FC", borderRadius: "4px 12px 12px 12px",
                  padding: "12px 16px", fontSize: "0.88rem", color: "#222",
                  lineHeight: 1.7, borderLeft: `3px solid ${RI.blue}`,
                }}>{m.content}</div>
              </div>
            )}
          </div>
        ))}
        {aiLoading && (
        {aiLoading && (
          <div style={{ color: "#AAA", fontSize: "0.85rem" }}>
            ⏳ Querying {aiConfig.mode === "multi" ? `${aiConfig.models.length} models` : aiConfig.model}
            {aiConfig.enableJudge ? " + judge…" : "…"}
          </div>
        )}
        <div ref={msgEnd} />
      {/* </div> */}

      <div style={{ fontWeight: 600, color: RI.blue, marginBottom: 6 }}>
        💡 Suggested investigations{" "}
        <span style={{ fontWeight: 400, color: "#888", fontSize: "0.78rem" }}>
          ({suggLlmUsed ? "LLM-generated" : "templated from current facts"})
        </span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))", gap: 8, marginBottom: 14 }}>
        {suggestions.map((q, i) => {
          const cat = SUGGESTION_CATEGORIES[q.category] || SUGGESTION_CATEGORIES.drill_down;
          return (
            <div key={i}>
              <Chip color={cat.color}>{cat.icon} {cat.label}</Chip>
              <button onClick={() => setInput(q.text)} style={{
                width: "100%", marginTop: 4, padding: "10px 12px",
                borderRadius: 8, border: "1px solid #C8D8E8",
                background: "white", color: "#333", textAlign: "left",
                fontSize: "0.85rem", cursor: "pointer", lineHeight: 1.4,
              }}>{q.text}</button>
            </div>
          );
        })}
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
          placeholder="Ask anything — or click a suggestion above and refine it before Ask."
          style={{
            flex: 1, padding: "12px 16px", borderRadius: 10,
            border: "1px solid #C8D8E8", fontSize: "0.92rem", outline: "none",
          }}
        />
        <button onClick={() => sendMessage(input)} disabled={aiLoading || !input.trim()} style={{
          padding: "12px 24px", borderRadius: 10, border: "none",
          background: aiLoading ? "#CCC" : RI.blue, color: "white",
          cursor: aiLoading ? "not-allowed" : "pointer",
          fontWeight: 700, fontSize: "0.92rem",
        }}>Ask</button>
      </div>
    </>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("overview");
  const [filters, setFilters]     = useState({});
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const { data: insightsPayload } = useFetch(() => api.getInsights(filters), [JSON.stringify(filters)]);
  const mainPad = sidebarCollapsed ? 24 : 304;

  const content = useMemo(() => {
    switch (activeTab) {
      case "where":         return <WhereTab        filters={filters} insights={insightsPayload} />;
      case "why":           return <WhyTab          filters={filters} insights={insightsPayload} />;
      case "products":      return <ProductsTab     filters={filters} insights={insightsPayload} />;
      case "inventory":     return <InventoryTab    filters={filters} insights={insightsPayload} />;
      case "data_quality":  return <DataQualityTab  filters={filters} />;
      case "ai":            return <AiTab           filters={filters} />;
      default:              return <OverviewTab     filters={filters} insights={insightsPayload} />;
    }
  }, [activeTab, filters, insightsPayload]);

  return (
    <div style={{ minHeight: "100vh", background: RI.bg, color: RI.ink,
                  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
      <FilterBar
        filters={filters}
        onChange={setFilters}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((c) => !c)}
      />
      <div style={{ marginLeft: mainPad, transition: "margin-left 0.2s ease" }}>
        <div style={{ background: RI.blue, padding: "16px 32px", boxShadow: "0 2px 8px rgba(0,0,0,0.18)" }}>
          <div style={{ color: "white", fontWeight: 800, fontSize: "1.35rem",
                        fontFamily: "'Plus Jakarta Sans', Inter, sans-serif",
                        letterSpacing: "-0.02em" }}>📦 Order Cancellation Intelligence</div>
          <div style={{ color: RI.teal, fontSize: "0.82rem", marginTop: 2 }}>
            Retail Insight · Feb – Jun 2024 · React + FastAPI
          </div>
        </div>
        <div style={{ background: "white", borderBottom: `1px solid ${RI.border}`,
                      padding: "0 24px", display: "flex", gap: 4, overflowX: "auto" }}>
          {TABS.map((t) => (
            <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
              padding: "14px 20px", border: "none", background: "none", cursor: "pointer",
              fontWeight: 600, fontSize: "0.92rem", whiteSpace: "nowrap",
              color: activeTab === t.id ? RI.blue : RI.muted,
              borderBottom: activeTab === t.id ? `3px solid ${RI.teal}` : "3px solid transparent",
              borderRadius: "6px 6px 0 0",
            }}>{t.label}</button>
          ))}
        </div>
        <div style={{ padding: "20px 32px", width: "100%", boxSizing: "border-box" }}>{content}</div>
      </div>
    </div>
  );
}
