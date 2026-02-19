"""
ArgusAI — Alert System
Sends dual alerts (SMS + Telegram) for fraud detection:
  - OTP verification requests (MEDIUM risk) → SMS + Telegram
  - Block alerts (HIGH risk) → Telegram + SMS
"""

import os, random, asyncio
from datetime import datetime

import httpx
from dotenv import load_dotenv
from fast2sms_service import send_otp_sms, send_alert_sms

# Load .env first
load_dotenv()

# ─── Config (set these in .env) ────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER", "").strip()

print(f"[Alert System] Config loaded:")
print(f"  - Telegram: {'✅' if TELEGRAM_TOKEN else '❌'}")
print(f"  - Alert Phone: {'✅' if ALERT_PHONE_NUMBER else '❌'}")

# In-memory OTP store: txn_id → otp
_otp_store: dict[str, str] = {}


def generate_otp(length: int = 6) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


async def _send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API."""
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[ALERT - Telegram not configured]\n{message}")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
    except Exception as e:
        print(f"[Telegram error] {e}")
        return False


async def send_otp_alert(txn: dict, result: dict) -> dict:
    """Send OTP alert for medium-risk transactions.
    
    MEDIUM risk: SMS (Fast2SMS) + Telegram
    HIGH risk:  Telegram (primary) + SMS alert
    """
    otp     = generate_otp()
    txn_id  = txn.get("transaction_id", "TXN???")
    amount  = txn.get("amount", 0)
    city    = txn.get("transaction_city", "Unknown")
    risk_score = result.get("risk_score", 0)
    reason  = result.get("shap_explanation", [{}])[0].get("label", "unusual pattern")

    _otp_store[txn_id] = otp

    # Determine risk level
    risk_level = "LOW"
    if risk_score > 70:
        risk_level = "HIGH"
    elif risk_score > 40:
        risk_level = "MEDIUM"

    # 1️⃣ Send SMS for MEDIUM+ risk (real SMS via Fast2SMS) - DISABLED
    # if (risk_level in ["MEDIUM", "HIGH"]) and ALERT_PHONE_NUMBER:
    #     sms_result = await send_otp_sms(ALERT_PHONE_NUMBER, otp, txn_id)
    #     print(f"[Alert — SMS] {sms_result}")

    # 2️⃣ Send Telegram for all risk levels
    message = (
        f"⚠️ <b>ArgusAI Security Alert</b>\n\n"
        f"🔔 <b>Suspicious Transaction Detected [{risk_level}]</b>\n"
        f"─────────────────────────\n"
        f"💳 Transaction : <code>{txn_id}</code>\n"
        f"💰 Amount      : ₹{amount:,.2f}\n"
        f"📍 Location    : {city}\n"
        f"⚡ Risk Score  : {risk_score:.0f}/100\n"
        f"🔍 Reason      : {reason}\n"
        f"─────────────────────────\n"
        f"🔐 <b>Your OTP: <code>{otp}</code></b>\n\n"
        f"Reply <b>YES</b> to approve or <b>NO</b> to block.\n"
        f"⏰ Valid for 5 minutes."
    )

    sent = await _send_telegram(message)
    print(f"[Alert — Telegram] OTP sent, Telegram: {'✅' if sent else '❌'}")
    return {"otp": otp, "sent": sent, "risk_level": risk_level, "txn_id": txn_id}


async def send_block_alert(txn: dict, result: dict) -> bool:
    """Send block notification for high-risk transactions.
    
    HIGH risk: Full Telegram + brief SMS alert
    """
    txn_id = txn.get("transaction_id", "TXN???")
    amount = txn.get("amount", 0)
    city   = txn.get("transaction_city", "Unknown")
    risk_score = result.get("risk_score", 0)

    # 1️⃣ Send SMS alert for HIGH risk (brief alert) - DISABLED
    # if ALERT_PHONE_NUMBER:
    #     sms_sent = await send_alert_sms(
    #         ALERT_PHONE_NUMBER, 
    #         "BLOCK", 
    #         txn_id, 
    #         amount, 
    #         city, 
    #         risk_score
    #     )
    #     print(f"[Alert — Block SMS] {sms_sent}")

    # 2️⃣ Build signal summary
    signals = []
    if txn.get("is_night"):          signals.append("🌙 Night-time transaction")
    if txn.get("device_mismatch"):   signals.append("📱 Unknown device")
    if txn.get("distance_from_home_km", 0) > 500:
        signals.append(f"📍 {txn['distance_from_home_km']:.0f}km from home")
    if txn.get("amount_vs_avg_ratio", 0) > 5:
        signals.append("💸 Amount far above average")

    signal_text = "\n".join(signals) if signals else "Multiple risk signals"

    # 3️⃣ Send detailed Telegram
    message = (
        f"🚫 <b>ArgusAI — Transaction BLOCKED</b>\n\n"
        f"High-risk transaction automatically blocked.\n"
        f"─────────────────────────\n"
        f"💳 Transaction : <code>{txn_id}</code>\n"
        f"💰 Amount      : ₹{amount:,.2f}\n"
        f"📍 Location    : {city}\n"
        f"⚡ Risk Score  : {risk_score:.0f}/100\n\n"
        f"<b>Risk Signals:</b>\n{signal_text}\n"
        f"─────────────────────────\n"
        f"If this was you, contact support immediately.\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

    return await _send_telegram(message)


def verify_otp(txn_id: str, user_otp: str) -> bool:
    stored = _otp_store.get(txn_id)
    if stored and stored == user_otp.strip():
        del _otp_store[txn_id]
        return True
    return False