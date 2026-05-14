import { RI, SEVERITY, EFFORT, CATEGORY_ICON } from "../theme";

export function RecommendationCard({ rec, position }) {
  if (!rec) return null;
  const sev = SEVERITY[rec.severity] ?? SEVERITY.info;
  const eff = EFFORT[rec.effort] ?? EFFORT.medium;
  const catIcon = CATEGORY_ICON[rec.category] ?? "•";

  return (
    <div style={{
      background: "white", borderLeft: `5px solid ${sev.color}`,
      borderRadius: 10, padding: "16px 20px", marginBottom: 12,
      boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <span style={{
          background: `${sev.color}20`, color: sev.color,
          padding: "3px 10px", borderRadius: 10, fontSize: "0.72rem",
          fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5,
        }}>{rec.severity}</span>
        <span style={{
          background: `${eff.color}20`, color: eff.color,
          padding: "3px 10px", borderRadius: 10, fontSize: "0.72rem", fontWeight: 600,
        }}>{eff.label}</span>
        <span style={{ color: RI.muted, fontSize: "0.78rem" }}>
          {catIcon} {rec.category}
        </span>
        {typeof position === "number" && (
          <span style={{ marginLeft: "auto", color: "#AAA", fontSize: "0.72rem" }}>
            #{position}
          </span>
        )}
      </div>
      <div style={{ fontWeight: 700, color: RI.blue, fontSize: "1.0rem", marginBottom: 6 }}>
        {rec.action}
      </div>
      <div style={{ fontSize: "0.85rem", color: "#444", fontStyle: "italic", marginBottom: 8 }}>
        {rec.rationale}
      </div>
      <div style={{
        fontSize: "0.82rem", color: "#555",
        borderTop: "1px solid #EEE", paddingTop: 8, marginBottom: 6,
      }}>
        <strong>Expected impact:</strong> {rec.expected_impact}
      </div>
      <div style={{ fontSize: "0.72rem", color: "#888" }}>
        Supports:{" "}
        {(rec.supporting_facts ?? []).map((k) => (
          <span key={k} style={{
            background: "#EEF6FB", color: RI.blue,
            padding: "2px 8px", borderRadius: 10,
            fontSize: "0.72rem", marginRight: 4,
          }}>{k}</span>
        ))}
      </div>
    </div>
  );
}
