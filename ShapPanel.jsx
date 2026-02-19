import React from "react";

const impactColor = {
  HIGH:   "#ef4444",
  MEDIUM: "#f59e0b",
  LOW:    "#64748b",
};

export default function ShapPanel({ explanations = [] }) {
  if (!explanations || explanations.length === 0) {
    return (
      <div className="card" style={{ height: "100%", display: "flex",
        alignItems: "center", justifyContent: "center", color: "var(--muted)" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: "32px", marginBottom: "8px" }}>🔍</div>
          <div>Awaiting transaction...</div>
        </div>
      </div>
    );
  }

  // Max absolute shap value for bar scaling
  const maxVal = Math.max(...explanations.map(e => Math.abs(e.shap_val)), 0.01);

  return (
    <div className="card" style={{ height: "100%" }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        marginBottom: "16px",
      }}>
        <span style={{ fontSize: "16px" }}>🔍</span>
        <span style={{ fontWeight: "700", fontSize: "14px" }}>
          Why This Decision?
        </span>
        <span style={{
          marginLeft: "auto",
          fontSize: "11px",
          color: "var(--muted)",
          background: "var(--surface2)",
          padding: "2px 8px",
          borderRadius: "4px",
        }}>
          SHAP Explanation
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {explanations.map((e, i) => {
          const pct   = (Math.abs(e.shap_val) / maxVal) * 100;
          const color = e.shap_val > 0 ? "#ef4444" : "#10b981";
          const dir   = e.shap_val > 0 ? "▲ Increases risk" : "▼ Decreases risk";

          return (
            <div key={i} className="animate-fade-in" style={{
              animationDelay: `${i * 0.07}s`,
            }}>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: "5px",
                alignItems: "center",
              }}>
                <span style={{ fontWeight: "500", fontSize: "13px" }}>
                  {e.label}
                </span>
                <span style={{
                  fontSize: "11px",
                  color,
                  fontWeight: "600",
                }}>
                  {dir}
                </span>
              </div>

              {/* SHAP bar */}
              <div style={{
                height: "8px",
                background: "var(--border)",
                borderRadius: "4px",
                overflow: "hidden",
              }}>
                <div style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: color,
                  borderRadius: "4px",
                  boxShadow: `0 0 8px ${color}88`,
                  transition: "width 0.5s ease",
                }} />
              </div>

              <div style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "3px",
              }}>
                <span style={{
                  fontSize: "10px",
                  color: "var(--muted)",
                }}>
                  Impact: <span style={{
                    color: impactColor[e.impact],
                    fontWeight: "600",
                  }}>{e.impact}</span>
                </span>
                <span style={{
                  fontSize: "10px",
                  color: "var(--muted)",
                  fontFamily: "JetBrains Mono, monospace",
                }}>
                  {e.shap_val > 0 ? "+" : ""}{e.shap_val.toFixed(3)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{
        marginTop: "16px",
        padding: "10px",
        background: "var(--surface2)",
        borderRadius: "8px",
        fontSize: "11px",
        color: "var(--muted)",
      }}>
        🔴 Red bars increase fraud risk &nbsp;|&nbsp; 🟢 Green bars decrease fraud risk
      </div>
    </div>
  );
}