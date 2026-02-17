import React, { useEffect, useState } from "react";

function getColor(score) {
  if (score >= 70) return "#ef4444";
  if (score >= 40) return "#f59e0b";
  return "#10b981";
}

function getLabel(score) {
  if (score >= 70) return "HIGH RISK";
  if (score >= 40) return "MEDIUM RISK";
  return "LOW RISK";
}

export default function RiskGauge({ score = 0, action }) {
  const [displayed, setDisplayed] = useState(0);

  // Animate score counting up
  useEffect(() => {
    setDisplayed(0);
    if (score === 0) return;
    const steps = 40;
    const increment = score / steps;
    let current = 0;
    const interval = setInterval(() => {
      current += increment;
      if (current >= score) {
        setDisplayed(score);
        clearInterval(interval);
      } else {
        setDisplayed(Math.round(current));
      }
    }, 20);
    return () => clearInterval(interval);
  }, [score]);

  const color   = getColor(score);
  const label   = getLabel(score);
  const radius  = 70;
  const stroke  = 10;
  const norm    = radius - stroke / 2;
  const circ    = 2 * Math.PI * norm;
  const dash    = (displayed / 100) * circ;

  const glowMap = {
    BLOCK: "pulse-red",
    OTP:   "pulse-yellow",
    ALLOW: "pulse-green",
  };

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "12px",
    }}>
      <div style={{
        position: "relative",
        width: radius * 2 + stroke,
        height: radius * 2 + stroke,
        animation: action ? `${glowMap[action] || ""} 2s ease infinite` : "none",
        borderRadius: "50%",
      }}>
        <svg
          width={radius * 2 + stroke}
          height={radius * 2 + stroke}
          style={{ transform: "rotate(-90deg)" }}
        >
          {/* Background ring */}
          <circle
            cx={radius + stroke / 2}
            cy={radius + stroke / 2}
            r={norm}
            fill="none"
            stroke="var(--border)"
            strokeWidth={stroke}
          />
          {/* Progress ring */}
          <circle
            cx={radius + stroke / 2}
            cy={radius + stroke / 2}
            r={norm}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dasharray 0.05s linear", filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>

        {/* Center text */}
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 2,
        }}>
          <span style={{
            fontSize: "32px",
            fontWeight: "900",
            color,
            fontFamily: "JetBrains Mono, monospace",
            lineHeight: 1,
          }}>
            {displayed}
          </span>
          <span style={{ fontSize: "10px", color: "var(--muted)", letterSpacing: "0.05em" }}>
            / 100
          </span>
        </div>
      </div>

      {/* Risk label */}
      <div style={{
        padding: "6px 16px",
        borderRadius: "999px",
        background: `${color}22`,
        border: `1px solid ${color}55`,
        color,
        fontSize: "12px",
        fontWeight: "700",
        letterSpacing: "0.08em",
      }}>
        {label}
      </div>

      {/* Action badge */}
      {action && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "13px",
          fontWeight: "600",
          color,
        }}>
          {action === "ALLOW" && "✅ APPROVED"}
          {action === "OTP"   && "⚠️  OTP REQUIRED"}
          {action === "BLOCK" && "🚫 BLOCKED"}
        </div>
      )}
    </div>
  );
}