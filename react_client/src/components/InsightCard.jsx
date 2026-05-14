import { RI, SEVERITY } from "../theme";

/**
 * Severity-driven insight render. Pass either:
 *   <InsightCard insight={insightObj} />     — the {severity, icon, text} payload
 *   <InsightCard severity="high" icon="🚨" text="..." />
 *
 * The frontend never invents numbers — `text` should come from the
 * `/api/analytics/insights` endpoint (which is itself fact-grounded).
 */
export function InsightCard({ insight, severity, icon, text, compact = false }) {
  const sev = insight?.severity ?? severity ?? "info";
  const meta = SEVERITY[sev] ?? SEVERITY.info;
  const _icon = insight?.icon ?? icon ?? meta.icon;
  const _text = insight?.text ?? text ?? "";

  if (!_text) return null;

  return (
    <div style={{
      background: meta.bg, borderLeft: `4px solid ${meta.color}`,
      borderRadius: 10, padding: compact ? "10px 14px" : "14px 18px",
      margin: "10px 0", color: sev === "info" ? RI.blue : "#5a1a1a",
      fontSize: compact ? "0.85rem" : "0.92rem", lineHeight: 1.55,
    }}>
      <span style={{ marginRight: 8 }}>{_icon}</span>
      {_text}
    </div>
  );
}
