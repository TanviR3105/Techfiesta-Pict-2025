import React, { useState, useEffect, useRef, useCallback } from "react";
import StatsBar    from "./components/StatsBar.jsx";
import RiskGauge   from "./components/RiskGauge.jsx";
import ShapPanel   from "./components/ShapPanel.jsx";
import AlertBanner from "./components/AlertBanner.jsx";
import Dashboard   from "./components/Dashboard.jsx";

const API = "http://localhost:8000";
const WS  = "ws://localhost:8000/ws/stream";

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [selected,     setSelected]     = useState(null);
  const [stats,        setStats]        = useState(null);
  const [wsStatus,     setWsStatus]     = useState("connecting");
  const [streaming,    setStreaming]     = useState(true);
  const wsRef = useRef(null);
  const pingRef = useRef(null);

  // ── WebSocket ────────────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    const ws = new WebSocket(WS);

    ws.onopen = () => {
      setWsStatus("connected");
      // Keepalive ping every 20s
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: "ping" }));
        }
      }, 20000);
    };

    ws.onmessage = (e) => {
      try {
        const txn = JSON.parse(e.data);
        if (txn.action === "pong") return;
        setTransactions(prev => [txn, ...prev].slice(0, 100));
        setSelected(txn);   // auto-highlight latest
      } catch {}
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
      clearInterval(pingRef.current);
      // Reconnect after 2s
      setTimeout(connectWS, 2000);
    };

    ws.onerror = () => ws.close();
    wsRef.current = ws;
  }, []);

  useEffect(() => {
    connectWS();
    fetchStats();
    const statsTimer = setInterval(fetchStats, 5000);
    return () => {
      clearInterval(statsTimer);
      clearInterval(pingRef.current);
      wsRef.current?.close();
    };
  }, [connectWS]);

  // ── Stats ────────────────────────────────────────────────────────────────
  async function fetchStats() {
    try {
      const res  = await fetch(`${API}/api/stats`);
      const data = await res.json();
      setStats(data.stats);
    } catch {}
  }

  // ── Stream control ───────────────────────────────────────────────────────
  async function toggleStream() {
    const action = streaming ? "stop" : "start";
    await fetch(`${API}/api/stream/control`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ action, interval: 3.0 }),
    });
    setStreaming(!streaming);
  }

  // ── Inject fraud demo ────────────────────────────────────────────────────
  async function injectFraud() {
    await fetch(`${API}/api/transaction/fraud`, { method: "POST" });
  }

  // ── Simulate one transaction ─────────────────────────────────────────────
  async function simulateOne() {
    await fetch(`${API}/api/transaction/simulate`, { method: "POST" });
  }

  const statusColor = {
    connected:    "var(--green)",
    disconnected: "var(--red)",
    connecting:   "var(--yellow)",
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        padding: "0 24px",
        height: "60px",
        display: "flex",
        alignItems: "center",
        gap: "16px",
        flexShrink: 0,
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div style={{
            width: "36px", height: "36px",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            borderRadius: "10px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "18px", fontWeight: "900", color: "#fff",
          }}>A</div>
          <div>
            <div style={{ fontWeight: "800", fontSize: "16px", letterSpacing: "-0.02em" }}>
              ArgusAI
            </div>
            <div style={{ fontSize: "10px", color: "var(--muted)", marginTop: "-2px" }}>
              Fraud Detection & Risk Management
            </div>
          </div>
        </div>

        {/* WS status */}
        <div style={{
          display: "flex", alignItems: "center", gap: "6px",
          background: "var(--surface2)",
          padding: "4px 12px", borderRadius: "999px",
          fontSize: "11px", color: statusColor[wsStatus],
          border: `1px solid ${statusColor[wsStatus]}44`,
        }}>
          <span style={{
            width: "6px", height: "6px", borderRadius: "50%",
            background: statusColor[wsStatus],
            animation: wsStatus === "connected" ? "blink 1.5s ease infinite" : "none",
            display: "inline-block",
          }} />
          {wsStatus === "connected" ? "Live" : wsStatus}
        </div>

        <div style={{ flex: 1 }} />

        {/* Control buttons */}
        <button className="btn btn-ghost" onClick={simulateOne} title="Simulate one random transaction">
          ⚡ Simulate
        </button>
        <button className="btn btn-danger" onClick={injectFraud} title="Inject a fraud transaction">
          🚨 Inject Fraud
        </button>
        <button
          className={`btn ${streaming ? "btn-ghost" : "btn-success"}`}
          onClick={toggleStream}
        >
          {streaming ? "⏸ Pause" : "▶ Resume"} Stream
        </button>
      </header>

      {/* ── Main content ───────────────────────────────────────────────── */}
      <main style={{ flex: 1, padding: "20px 24px", display: "flex", flexDirection: "column" }}>

        {/* Stats bar */}
        <StatsBar stats={stats} />

        {/* Alert banner (shows for OTP / BLOCK) */}
        {selected && (selected.action === "OTP" || selected.action === "BLOCK") && (
          <AlertBanner
            transaction={selected}
            onVerified={() => setSelected(null)}
          />
        )}

        {/* Main 3-column layout */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "220px 1fr 280px",
          gap: "16px",
          flex: 1,
          minHeight: 0,
        }}>

          {/* LEFT — Risk Gauge */}
          <div className="card" style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "20px",
          }}>
            <div style={{ fontWeight: "700", fontSize: "13px", color: "var(--muted)" }}>
              CURRENT RISK
            </div>
            <RiskGauge
              score={selected?.risk_score || 0}
              action={selected?.action}
            />

            {/* Transaction quick-info */}
            {selected && (
              <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: "8px" }}>
                {[
                  { label: "Amount",   value: `₹${Number(selected.amount || 0).toLocaleString("en-IN")}` },
                  { label: "City",     value: selected.transaction_city || "—" },
                  { label: "Method",   value: selected.payment_type || "—" },
                  { label: "Device",   value: selected.device_type || "—" },
                  { label: "Fraud %",  value: `${selected.fraud_prob || 0}%` },
                  { label: "Anomaly",  value: selected.is_anomaly ? "⚠️ Yes" : "✅ No" },
                ].map((item, i) => (
                  <div key={i} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "5px 8px",
                    background: "var(--surface2)",
                    borderRadius: "6px",
                    fontSize: "11px",
                  }}>
                    <span style={{ color: "var(--muted)" }}>{item.label}</span>
                    <span style={{ fontWeight: "600" }}>{item.value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* CENTER — Live feed */}
          <Dashboard
            transactions={transactions}
            onSelect={setSelected}
            selected={selected}
          />

          {/* RIGHT — SHAP */}
          <ShapPanel explanations={selected?.shap_explanation} />
        </div>

        {/* ── Footer ──────────────────────────────────────────────────── */}
        <div style={{
          marginTop: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "11px",
          color: "var(--muted)",
        }}>
          <span>ArgusAI v1.0 — Hybrid XGBoost + Autoencoder Fraud Engine</span>
          <span>
            Click any row to inspect &nbsp;|&nbsp; 🚨 Inject Fraud for live demo
          </span>
        </div>
      </main>
    </div>
  );
}