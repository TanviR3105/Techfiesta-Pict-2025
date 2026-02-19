import React from "react";

const icons = {
  total:   "💳",
  blocked: "🚫",
  otp:     "⚠️",
  allowed: "✅",
  fraud:   "📊",
  risk:    "⚡",
};

export default function StatsBar({ stats }) {
  if (!stats) return null;

  const cards = [
    { label: "Total Transactions", value: stats.total?.toLocaleString() || "0",       icon: icons.total,   color: "var(--blue)"   },
    { label: "Blocked (High Risk)", value: stats.blocked?.toLocaleString() || "0",    icon: icons.blocked, color: "var(--red)"    },
    { label: "OTP Verification",    value: stats.otp?.toLocaleString() || "0",        icon: icons.otp,     color: "var(--yellow)" },
    { label: "Approved",            value: stats.allowed?.toLocaleString() || "0",    icon: icons.allowed, color: "var(--green)"  },
    { label: "Fraud Rate",          value: `${stats.fraud_rate || 0}%`,               icon: icons.fraud,   color: "var(--red)"    },
    { label: "Avg Risk Score",      value: `${stats.avg_risk || 0}/100`,              icon: icons.risk,    color: "var(--purple)" },
  ];

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(6, 1fr)",
      gap: "12px",
      marginBottom: "20px",
    }}>
      {cards.map((c, i) => (
        <div key={i} className="card animate-fade-in" style={{
          padding: "16px",
          borderLeft: `3px solid ${c.color}`,
          position: "relative",
          overflow: "hidden",
        }}>
          <div style={{ fontSize: "20px", marginBottom: "6px" }}>{c.icon}</div>
          <div style={{
            fontSize: "22px",
            fontWeight: "800",
            color: c.color,
            fontFamily: "JetBrains Mono, monospace",
          }}>
            {c.value}
          </div>
          <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "2px" }}>
            {c.label}
          </div>
          {/* subtle bg glow */}
          <div style={{
            position: "absolute", bottom: "-20px", right: "-10px",
            fontSize: "50px", opacity: 0.05,
          }}>{c.icon}</div>
        </div>
      ))}
    </div>
  );
}