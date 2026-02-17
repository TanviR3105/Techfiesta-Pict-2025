import React, { useState } from "react";

const API = "http://localhost:8000";

export default function AlertBanner({ transaction, onVerified }) {
  const [otp,      setOtp]      = useState("");
  const [loading,  setLoading]  = useState(false);
  const [verified, setVerified] = useState(null);
  const [msg,      setMsg]      = useState("");

  if (!transaction) return null;

  const { action, risk_score, risk_level, transaction_id, amount,
          transaction_city, shap_explanation } = transaction;

  if (action === "ALLOW") return null;

  const isBlock  = action === "BLOCK";
  const isOTP    = action === "OTP";
  const color    = isBlock ? "var(--red)" : "var(--yellow)";
  const bg       = isBlock ? "rgba(239,68,68,0.08)" : "rgba(245,158,11,0.08)";
  const anim     = isBlock ? "pulse-red" : "pulse-yellow";

  const topSignal = shap_explanation?.[0]?.label || "unusual pattern";

  async function handleVerify() {
    if (!otp.trim()) return;
    setLoading(true);
    try {
      const res  = await fetch(`${API}/api/otp/verify`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_id, otp }),
      });
      const data = await res.json();
      setVerified(data.verified);
      setMsg(data.message);
      if (data.verified && onVerified) onVerified();
    } catch {
      setMsg("❌ Connection error");
    }
    setLoading(false);
  }

  return (
    <div style={{
      background: bg,
      border: `1px solid ${color}55`,
      borderRadius: "12px",
      padding: "20px",
      animation: `${anim} 2s ease infinite`,
      marginBottom: "16px",
    }} className="animate-slide-in">

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
        <span style={{ fontSize: "28px" }}>{isBlock ? "🚫" : "⚠️"}</span>
        <div>
          <div style={{ fontWeight: "800", fontSize: "16px", color }}>
            {isBlock ? "Transaction BLOCKED" : "Suspicious Transaction Detected"}
          </div>
          <div style={{ fontSize: "12px", color: "var(--muted)" }}>
            {isBlock
              ? "High fraud risk — transaction automatically blocked"
              : "Step-up verification required"}
          </div>
        </div>
        <div style={{
          marginLeft: "auto",
          background: `${color}22`,
          border: `1px solid ${color}44`,
          borderRadius: "8px",
          padding: "8px 14px",
          textAlign: "center",
        }}>
          <div style={{ fontSize: "22px", fontWeight: "900", color,
                        fontFamily: "JetBrains Mono, monospace" }}>
            {risk_score}
          </div>
          <div style={{ fontSize: "10px", color: "var(--muted)" }}>Risk Score</div>
        </div>
      </div>

      {/* Transaction details */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
        gap: "10px", marginBottom: "14px",
      }}>
        {[
          { label: "Transaction ID", value: transaction_id, mono: true },
          { label: "Amount",         value: `₹${Number(amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}` },
          { label: "Location",       value: transaction_city },
        ].map((item, i) => (
          <div key={i} style={{
            background: "var(--surface2)",
            padding: "10px",
            borderRadius: "8px",
          }}>
            <div style={{ fontSize: "10px", color: "var(--muted)", marginBottom: "3px" }}>
              {item.label}
            </div>
            <div style={{
              fontWeight: "600",
              fontFamily: item.mono ? "JetBrains Mono, monospace" : "inherit",
              fontSize: item.mono ? "11px" : "13px",
            }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* Top signal */}
      <div style={{
        background: "var(--surface2)",
        borderRadius: "8px",
        padding: "10px 14px",
        fontSize: "12px",
        marginBottom: "14px",
        borderLeft: `3px solid ${color}`,
      }}>
        🔍 <b>Primary Signal:</b> {topSignal}
      </div>

      {/* OTP section */}
      {isOTP && verified === null && (
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ flex: 1 }}>
            <input
              type="text"
              maxLength={6}
              placeholder="Enter 6-digit OTP from your phone"
              value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, ""))}
              onKeyDown={e => e.key === "Enter" && handleVerify()}
              style={{
                width: "100%",
                background: "var(--surface2)",
                border: `1px solid ${color}55`,
                borderRadius: "8px",
                padding: "10px 14px",
                color: "var(--text)",
                fontSize: "16px",
                fontFamily: "JetBrains Mono, monospace",
                letterSpacing: "0.2em",
                outline: "none",
              }}
            />
          </div>
          <button
            className="btn btn-success"
            onClick={handleVerify}
            disabled={loading || otp.length < 6}
          >
            {loading ? <span className="loading-spinner" /> : "✓ Verify OTP"}
          </button>
          <button
            className="btn btn-danger"
            onClick={() => { setVerified(false); setMsg("🚫 Transaction blocked by user"); }}
          >
            Block
          </button>
        </div>
      )}

      {/* Result message */}
      {msg && (
        <div style={{
          marginTop: "10px",
          padding: "10px 14px",
          background: verified ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
          border: `1px solid ${verified ? "var(--green)" : "var(--red)"}55`,
          borderRadius: "8px",
          fontWeight: "600",
          color: verified ? "var(--green)" : "var(--red)",
        }}>
          {msg}
        </div>
      )}
    </div>
  );
}