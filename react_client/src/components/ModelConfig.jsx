import { useEffect, useState } from "react";
import { api } from "../api/client";

const RI_BLUE  = "#1B3A6B";
const RI_TEAL  = "#00A8E0";
const RI_RED   = "#E63946";
const RI_AMBER = "#F4A261";
const RI_GREEN = "#2A9D8F";

const MODEL_LABELS = {
  claude: "Claude (Anthropic)",
  openai: "GPT-4o (OpenAI)",
  gemini: "Gemini 1.5 Pro",
};

const MODEL_COLORS = {
  claude: "#D4620A",
  openai: "#10A37F",
  gemini: "#4285F4",
};

/* ------------------------------------------------------------------ */
/* ModelConfig — sets mode + selected models + judge toggle           */
/* ------------------------------------------------------------------ */

export function ModelConfig({ config, onChange }) {
  const [available, setAvailable] = useState(["claude", "openai", "gemini"]);

  useEffect(() => {
    api.getModels()
       .then((r) => setAvailable((r.models || []).map((m) => m.id)))
       .catch(() => {});
  }, []);

  const update = (patch) => onChange({ ...config, ...patch });
  const toggleModel = (id) => {
    const next = config.models.includes(id)
      ? config.models.filter((m) => m !== id)
      : [...config.models, id];
    update({ models: next.length ? next : [id] });
  };

  return (
    <div style={{
      background: "white", borderRadius: 12, padding: "18px 22px",
      boxShadow: "0 2px 8px rgba(0,0,0,0.06)", marginBottom: 16,
      borderLeft: `4px solid ${RI_TEAL}`,
    }}>
      <div style={{ fontWeight: 700, color: RI_BLUE, marginBottom: 12 }}>
        ⚙️ AI Configuration
      </div>

      {/* Mode toggle */}
      <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
        {[
          { id: "single", label: "Single Model" },
          { id: "multi",  label: "Multi-Model"  },
        ].map((m) => (
          <button key={m.id} onClick={() => update({ mode: m.id })}
            style={{
              padding: "6px 14px", borderRadius: 16,
              border: `1px solid ${config.mode === m.id ? RI_BLUE : "#C8D8E8"}`,
              background: config.mode === m.id ? RI_BLUE : "white",
              color:      config.mode === m.id ? "white"  : "#444",
              cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
            }}>
            {m.label}
          </button>
        ))}
      </div>

      {/* Single-model picker */}
      {config.mode === "single" && (
        <div>
          <div style={{ fontSize: "0.78rem", color: "#666", marginBottom: 6 }}>Model</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {available.map((m) => (
              <button key={m} onClick={() => update({ model: m, models: [m] })}
                style={{
                  padding: "6px 14px", borderRadius: 16,
                  border: `1px solid ${config.model === m ? MODEL_COLORS[m] : "#C8D8E8"}`,
                  background: config.model === m ? `${MODEL_COLORS[m]}15` : "white",
                  color:      config.model === m ? MODEL_COLORS[m] : "#444",
                  cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
                }}>
                {MODEL_LABELS[m] || m}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Multi-model picker + judge */}
      {config.mode === "multi" && (
        <>
          <div style={{ fontSize: "0.78rem", color: "#666", marginBottom: 6 }}>Models to query</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {available.map((m) => {
              const on = config.models.includes(m);
              return (
                <button key={m} onClick={() => toggleModel(m)}
                  style={{
                    padding: "6px 14px", borderRadius: 16,
                    border: `1px solid ${on ? MODEL_COLORS[m] : "#C8D8E8"}`,
                    background: on ? `${MODEL_COLORS[m]}15` : "white",
                    color:      on ? MODEL_COLORS[m] : "#444",
                    cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
                  }}>
                  {on ? "✓ " : ""}{MODEL_LABELS[m] || m}
                </button>
              );
            })}
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "#444" }}>
            <input type="checkbox" checked={config.enableJudge}
                   onChange={(e) => update({ enableJudge: e.target.checked })} />
            Enable judge
            <span style={{ color: "#999", fontSize: "0.75rem", marginLeft: 6 }}>
              (second model evaluates and synthesises all responses)
            </span>
          </label>

          {config.enableJudge && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: "0.78rem", color: "#666", marginBottom: 6 }}>Judge model</div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {available.map((m) => (
                  <button key={m} onClick={() => update({ judgeModel: m })}
                    style={{
                      padding: "5px 12px", borderRadius: 14,
                      border: `1px solid ${config.judgeModel === m ? MODEL_COLORS[m] : "#C8D8E8"}`,
                      background: config.judgeModel === m ? `${MODEL_COLORS[m]}15` : "white",
                      color:      config.judgeModel === m ? MODEL_COLORS[m] : "#444",
                      cursor: "pointer", fontSize: "0.78rem", fontWeight: 600,
                    }}>
                    {MODEL_LABELS[m] || m}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}


/* ------------------------------------------------------------------ */
/* ModelBadge — small chip showing which model produced a response    */
/* ------------------------------------------------------------------ */

export function ModelBadge({ model }) {
  const color = MODEL_COLORS[model] || "#666";
  return (
    <span style={{
      display: "inline-block", padding: "2px 10px", borderRadius: 12,
      background: `${color}20`, color, border: `1px solid ${color}`,
      fontSize: "0.75rem", fontWeight: 600, marginRight: 6,
    }}>
      {MODEL_LABELS[model] || model}
    </span>
  );
}


/* ------------------------------------------------------------------ */
/* JudgePanel — collapsible synthesis + agreements/disagreements      */
/* ------------------------------------------------------------------ */

export function JudgePanel({ judgeResult }) {
  const [open, setOpen] = useState(false);
  if (!judgeResult) return null;

  const conf = (judgeResult.confidence || "medium").toLowerCase();
  const confColor = conf === "high" ? RI_GREEN : conf === "low" ? RI_RED : RI_AMBER;

  return (
    <div style={{
      background: `linear-gradient(135deg, ${RI_BLUE}08, ${RI_TEAL}15)`,
      border: `1px solid ${RI_TEAL}`, borderRadius: 10,
      padding: "12px 16px", margin: "8px 0",
    }}>
      <div onClick={() => setOpen((o) => !o)}
           style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
        <strong style={{ color: RI_BLUE }}>⚖️ Judge Evaluation</strong>
        <span style={{
          padding: "2px 10px", borderRadius: 10,
          background: `${confColor}20`, color: confColor,
          fontSize: "0.75rem", fontWeight: 600,
        }}>
          {conf.toUpperCase()} CONFIDENCE
        </span>
        <span style={{ marginLeft: "auto", color: "#888", fontSize: "0.78rem" }}>
          {open ? "▲ hide" : "▼ details"}
        </span>
      </div>

      <div style={{ marginTop: 8, fontStyle: "italic", color: "#444", fontSize: "0.85rem" }}>
        {judgeResult.synthesis}
      </div>

      {open && (
        <div style={{ marginTop: 10, fontSize: "0.83rem", color: "#333" }}>
          {judgeResult.key_agreements?.length > 0 && (
            <>
              <div style={{ fontWeight: 600, color: RI_GREEN, marginTop: 6 }}>Agreements</div>
              <ul style={{ margin: "4px 0 8px 18px" }}>
                {judgeResult.key_agreements.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </>
          )}
          {judgeResult.key_disagreements?.length > 0 && (
            <>
              <div style={{ fontWeight: 600, color: RI_RED }}>Disagreements</div>
              <ul style={{ margin: "4px 0 8px 18px" }}>
                {judgeResult.key_disagreements.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            </>
          )}
          {judgeResult.model_assessments && Object.keys(judgeResult.model_assessments).length > 0 && (
            <>
              <div style={{ fontWeight: 600, color: RI_BLUE }}>Per-model scoring</div>
              <ul style={{ margin: "4px 0 8px 18px" }}>
                {Object.entries(judgeResult.model_assessments).map(([m, a]) => (
                  <li key={m}>
                    <strong style={{ color: MODEL_COLORS[m] || "#444" }}>{MODEL_LABELS[m] || m}</strong>
                    {" — "}score {a.score ?? "?"}/10
                    {a.strengths   && <> · strengths: {a.strengths}</>}
                    {a.weaknesses  && <> · weaknesses: {a.weaknesses}</>}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
