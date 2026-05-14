// Shared design tokens. Keep in sync with the Streamlit CSS so both surfaces
// look like the same product.
export const RI = {
  blue:  "#1B3A6B",
  teal:  "#00A8E0",
  red:   "#E63946",
  amber: "#F4A261",
  green: "#2A9D8F",
  bg:    "#F7F9FC",
  ink:   "#2C3E50",
  muted: "#6C7B8B",
  border:"#E2EAF4",
};

export const SEVERITY = {
  high:   { color: RI.red,   bg: "#FFF3F3", icon: "🚨", label: "HIGH"   },
  medium: { color: RI.amber, bg: "#FFF8EE", icon: "⚠️", label: "MEDIUM" },
  info:   { color: RI.teal,  bg: "#EEF6FB", icon: "ℹ️", label: "INFO"   },
};

export const EFFORT = {
  quick_win:  { color: RI.green, label: "⚡ Quick win" },
  medium:     { color: RI.amber, label: "🛠 Medium"    },
  strategic:  { color: RI.blue,  label: "🎯 Strategic" },
};

export const CATEGORY_ICON = {
  operational:    "🏪",
  catalogue:      "📦",
  "data-quality": "🧪",
  strategic:      "🎯",
  process:        "⚙️",
};

export const SUGGESTION_CATEGORIES = {
  drill_down:     { icon: "🔍", color: RI.blue,    label: "Drill down"   },
  cause:          { icon: "🧭", color: RI.amber,   label: "Cause"        },
  comparison:     { icon: "⚖️", color: RI.teal,    label: "Compare"      },
  action:         { icon: "🎯", color: RI.green,   label: "Action"       },
  data_quality:   { icon: "🧪", color: RI.red,     label: "Data quality" },
  counterfactual: { icon: "💡", color: "#9C7AC6",  label: "What-if"      },
};
