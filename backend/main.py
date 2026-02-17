"""
ArgusAI — FastAPI Backend
Endpoints:
  POST /api/transaction         → analyze single transaction
  POST /api/transaction/fraud   → inject a fraud transaction (demo)
  GET  /api/transactions        → recent transaction history
  GET  /api/stats               → system statistics
  GET  /api/user/{id}           → user risk profile
  POST /api/otp/verify          → verify OTP
  WS   /ws/stream               → live transaction WebSocket feed
"""

import sys, os, asyncio, json
from datetime import datetime
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ml.predict                  import predict_transaction
from backend.database            import (log_transaction, get_recent_transactions,
                                          get_stats, get_user_profile, get_risk_trend)
from backend.alert               import send_otp_alert, send_block_alert, verify_otp
from backend.transaction_stream  import generate_live_transaction

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "ArgusAI Fraud Detection API",
    description = "Real-time AI-powered fraud detection & risk management",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── WebSocket Manager ────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager        = ConnectionManager()
_streaming     = False
_stream_task   = None


# ─── Core transaction processor ───────────────────────────────────────────────
async def process_and_broadcast(txn: dict):
    result = predict_transaction(txn)
    log_transaction(txn, result)

    # Send alerts
    if result["action"] == "BLOCK":
        asyncio.create_task(send_block_alert(txn, result))
    elif result["action"] == "OTP":
        otp_data = await send_otp_alert(txn, result)
        result["otp_sent"] = otp_data.get("sent", False)
        result["otp"]      = otp_data.get("otp", "")

    payload = {**txn, **result, "processed_at": datetime.utcnow().isoformat()}
    await manager.broadcast(payload)
    return result


# ─── Background stream ────────────────────────────────────────────────────────
async def _auto_stream(interval: float):
    global _streaming
    while _streaming:
        txn = generate_live_transaction()
        await process_and_broadcast(txn)
        await asyncio.sleep(interval)


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────
class TransactionInput(BaseModel):
    transaction_id:        Optional[str]   = None
    user_id:               Optional[int]   = 1
    timestamp:             Optional[str]   = None
    amount:                float
    payment_type:          str
    merchant_category:     str
    transaction_city:      str
    distance_from_home_km: float           = 0.0
    device_type:           str             = "Mobile"
    device_mismatch:       int             = 0
    card_age_days:         int             = 365
    transaction_hour:      int             = 12
    transaction_day:       int             = 0
    is_weekend:            int             = 0
    is_night:              int             = 0
    daily_txn_count:       int             = 1
    avg_amount_7d:         float           = 1000.0
    amount_vs_avg_ratio:   float           = 1.0

class OTPVerify(BaseModel):
    transaction_id: str
    otp:            str

class StreamControl(BaseModel):
    action:   str    = "start"   # "start" | "stop"
    interval: float  = 3.0


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "ArgusAI Fraud Detection",
        "version": "1.0.0",
        "status":  "operational",
        "docs":    "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/transaction")
async def analyze_transaction(txn_input: TransactionInput):
    """Analyze a single transaction and return risk assessment."""
    txn = txn_input.dict()
    if not txn.get("transaction_id"):
        txn["transaction_id"] = f"TXN{int(datetime.utcnow().timestamp())}"
    if not txn.get("timestamp"):
        txn["timestamp"] = datetime.utcnow().isoformat()

    result = await process_and_broadcast(txn)
    return {"transaction": txn, "result": result}


@app.post("/api/transaction/fraud")
async def inject_fraud_transaction():
    """Inject a simulated fraud transaction (for live demo)."""
    txn = generate_live_transaction(force_fraud=True)
    result = await process_and_broadcast(txn)
    return {"transaction": txn, "result": result, "demo": True}


@app.post("/api/transaction/simulate")
async def simulate_transaction():
    """Generate and analyze one random transaction."""
    txn = generate_live_transaction()
    result = await process_and_broadcast(txn)
    return {"transaction": txn, "result": result}


@app.get("/api/transactions")
async def recent_transactions(limit: int = 50):
    return {"transactions": get_recent_transactions(limit)}


@app.get("/api/stats")
async def system_stats():
    stats = get_stats()
    trend = get_risk_trend(hours=24)
    return {"stats": stats, "trend": trend}


@app.get("/api/user/{user_id}")
async def user_profile(user_id: int):
    profile = get_user_profile(user_id)
    return {"user_id": user_id, "profile": profile}


@app.post("/api/otp/verify")
async def verify_otp_endpoint(body: OTPVerify):
    ok = verify_otp(body.transaction_id, body.otp)
    return {
        "verified": ok,
        "message":  "Transaction approved ✅" if ok
                    else "Invalid OTP ❌ Transaction blocked",
    }


@app.post("/api/stream/control")
async def control_stream(body: StreamControl):
    global _streaming, _stream_task
    if body.action == "start" and not _streaming:
        _streaming   = True
        _stream_task = asyncio.create_task(_auto_stream(body.interval))
        return {"status": "stream started", "interval": body.interval}
    elif body.action == "stop":
        _streaming = False
        if _stream_task:
            _stream_task.cancel()
        return {"status": "stream stopped"}
    return {"status": "no change"}


# ─── WebSocket endpoint ───────────────────────────────────────────────────────
@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive / receive control messages
            data = await websocket.receive_text()
            msg  = json.loads(data)
            if msg.get("action") == "ping":
                await websocket.send_json({"action": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    print("🚀 ArgusAI API starting up...")
    # Auto-start streaming on launch
    global _streaming, _stream_task
    _streaming   = True
    _stream_task = asyncio.create_task(_auto_stream(3.0))
    print("✅ Live transaction stream started (every 3s)")


@app.on_event("shutdown")
async def shutdown():
    global _streaming
    _streaming = False
    print("👋 ArgusAI shutting down")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)