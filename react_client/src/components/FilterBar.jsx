import { useEffect, useState } from "react";
import { api } from "../api/client";
import { RI } from "../theme";

/**
 * Compact filter bar that mirrors the Streamlit sidebar. Holds the current
 * filter set in lifted state via the `onChange` callback.
 *
 * Props:
 *   filters    — current filter object {stores, regions, date_from, date_to, reasons}
 *   onChange   — called with the new filter object whenever a control changes
 *   collapsed  — bool — controls the open/close state from the parent
 *   onToggle   — fired when the user clicks the collapse chevron
 */
export function FilterBar({ filters, onChange, collapsed, onToggle }) {
  const [opts, setOpts] = useState({ stores: [], reasons: [], date_range: {} });

  useEffect(() => {
    api.getFilters().then(setOpts).catch(console.error);
  }, []);

  const update = (patch) => onChange({ ...filters, ...patch });
  const toggleArray = (key, val) => {
    const cur = filters[key] ?? [];
    update({ [key]: cur.includes(val) ? cur.filter((x) => x !== val) : [...cur, val] });
  };

  if (collapsed) {
    return (
      <button onClick={onToggle} style={{
        position: "fixed", top: 14, left: 14, zIndex: 20,
        background: RI.blue, color: "white", border: "none",
        borderRadius: 8, padding: "8px 12px", cursor: "pointer",
        fontWeight: 600, fontSize: "0.85rem",
        boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
      }}>
        ☰ Filters
      </button>
    );
  }

  const regionOptions = Array.from(new Set((opts.stores || []).map((s) => s.REGION))).sort();
  const storeOptions  = opts.stores || [];
  // Backend may ship states as [{STATE, store_count}] OR fall back to a derived
  // list from the stores payload for older backends.
  const stateOptions = (opts.states && opts.states.length)
    ? opts.states
    : Array.from(new Set((opts.stores || []).map((s) => s.STATE).filter(Boolean)))
        .sort()
        .map((s) => ({ STATE: s, store_count: (opts.stores || []).filter((x) => x.STATE === s).length }));

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, height: "100vh", width: 280,
      background: RI.blue, color: "white", padding: "20px 18px",
      overflowY: "auto", zIndex: 10, boxShadow: "2px 0 12px rgba(0,0,0,0.15)",
      fontSize: "0.88rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
        <div style={{ fontWeight: 800, fontSize: "1.1rem" }}>📦 Filters</div>
        <button onClick={onToggle} style={{
          background: "transparent", color: "white", border: "1px solid rgba(255,255,255,0.3)",
          borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: "0.78rem",
        }}>← Hide</button>
      </div>

      <FilterSection title="Date range">
        <label style={{ display: "block", marginBottom: 6, color: "#C8D8E8", fontSize: "0.75rem" }}>From</label>
        <input type="date" value={filters.date_from || ""}
          onChange={(e) => update({ date_from: e.target.value })}
          style={dateStyle} />
        <label style={{ display: "block", margin: "10px 0 6px", color: "#C8D8E8", fontSize: "0.75rem" }}>To</label>
        <input type="date" value={filters.date_to || ""}
          onChange={(e) => update({ date_to: e.target.value })}
          style={dateStyle} />
      </FilterSection>

      <FilterSection title="Stores">
        <ChipList
          items={storeOptions.map((s) => ({ value: s.STORE_NUM, label: `Store ${s.STORE_NUM} (${s.CITY})` }))}
          selected={filters.stores || []}
          onToggle={(v) => toggleArray("stores", v)}
        />
      </FilterSection>

      <FilterSection title="Regions">
        <ChipList
          items={regionOptions.map((r) => ({ value: r, label: `Region ${r}` }))}
          selected={filters.regions || []}
          onToggle={(v) => toggleArray("regions", v)}
        />
      </FilterSection>

      <FilterSection title="States">
        <ChipList
          items={stateOptions.map((s) => ({
            value: s.STATE,
            label: s.store_count ? `${s.STATE} (${s.store_count})` : s.STATE,
          }))}
          selected={filters.states || []}
          onToggle={(v) => toggleArray("states", v)}
          compact
        />
      </FilterSection>

      <FilterSection title="Cancel reasons">
        <ChipList
          items={(opts.reasons || []).map((r) => ({ value: r, label: r }))}
          selected={filters.reasons || []}
          onToggle={(v) => toggleArray("reasons", v)}
          compact
        />
      </FilterSection>

      <div style={{ marginTop: 22, display: "flex", gap: 8 }}>
        <button onClick={() => onChange({})} style={resetButtonStyle}>
          Reset all
        </button>
        <button onClick={() => api.clearCache()} style={resetButtonStyle}>
          Refresh
        </button>
      </div>

      <div style={{ marginTop: 18, color: "#A8BBD4", fontSize: "0.72rem", lineHeight: 1.5 }}>
        Filters propagate through every chart and the AI Insights tab.
      </div>
    </div>
  );
}

function FilterSection({ title, children }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontWeight: 700, marginBottom: 8, fontSize: "0.78rem",
                    textTransform: "uppercase", letterSpacing: 0.8, color: "#A8BBD4" }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function ChipList({ items, selected, onToggle, compact = false }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
      {items.map((item) => {
        const on = selected.includes(item.value);
        return (
          <button key={String(item.value)} onClick={() => onToggle(item.value)}
            style={{
              background: on ? RI.teal : "transparent",
              color: on ? "white" : "#C8D8E8",
              border: on ? `1px solid ${RI.teal}` : "1px solid rgba(255,255,255,0.25)",
              borderRadius: 14, padding: compact ? "3px 8px" : "4px 10px",
              fontSize: compact ? "0.72rem" : "0.78rem", fontWeight: 500,
              cursor: "pointer",
            }}>
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

const dateStyle = {
  width: "100%", padding: "6px 10px", borderRadius: 6,
  border: "1px solid rgba(255,255,255,0.25)", background: "white",
  color: RI.blue, fontSize: "0.85rem",
};

const resetButtonStyle = {
  flex: 1, padding: "6px 10px", borderRadius: 6, fontSize: "0.78rem",
  background: "transparent", color: "white",
  border: "1px solid rgba(255,255,255,0.3)", cursor: "pointer",
};
