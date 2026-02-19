"""
ArgusAI — Alert System (Telegram + Gmail)
Sends notifications for:
  - OTP verification requests (MEDIUM risk)
  - Block alerts (HIGH risk)
"""

import os, random, asyncio, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from datetime             import datetime
import httpx

# ─── Config ───────────────────────────────────────────────────────────────────
# Telegram
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# Gmail
GMAIL_USER       = os.getenv("GMAIL_USER",       "YOUR_GMAIL@gmail.com")
GMAIL_PASSWORD   = os.getenv("GMAIL_PASSWORD",   "YOUR_APP_PASSWORD_HERE")
ALERT_TO_EMAIL   = os.getenv("ALERT_TO_EMAIL",   "YOUR_GMAIL@gmail.com")

# In-memory OTP store
_otp_store: dict[str, str] = {}


def generate_otp(length: int = 6) -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(length)])


# ─── Telegram Functions ───────────────────────────────────────────────────────
async def _send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API."""
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[Telegram not configured]")
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
            print(f"✅ Telegram sent")
            return resp.status_code == 200
    except Exception as e:
        print(f"[Telegram error] {e}")
        return False


# ─── Gmail Functions ──────────────────────────────────────────────────────────
def _send_email(subject: str, html_body: str) -> bool:
    """Send HTML email via Gmail SMTP."""
    if GMAIL_USER == "YOUR_GMAIL@gmail.com":
        print(f"[Gmail not configured]")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"ArgusAI Fraud Detection <{GMAIL_USER}>"
        msg["To"]      = ALERT_TO_EMAIL
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, ALERT_TO_EMAIL, msg.as_string())
        print(f"✅ Email sent → {ALERT_TO_EMAIL}")
        return True
    except Exception as e:
        print(f"[Email error] {e}")
        return False


def _otp_email_html(txn, result, otp):
    amount   = txn.get("amount", 0)
    txn_id   = txn.get("transaction_id", "TXN???")
    city     = txn.get("transaction_city", "Unknown")
    risk     = result.get("risk_score", 0)
    reason   = result.get("shap_explanation", [{}])[0].get("label", "unusual pattern")
    time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    return f"""<div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;background:#0a0e1a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#f59e0b,#ef4444);padding:24px;text-align:center;">
        <h1 style="margin:0;font-size:24px;color:#fff;">⚠️ ArgusAI Security Alert</h1>
        <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);">Suspicious Transaction Detected</p>
      </div>
      <div style="padding:24px;">
        <div style="background:#111827;border-radius:8px;padding:16px;margin-bottom:16px;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Transaction ID</td><td style="padding:6px 0;font-family:monospace;font-size:13px;">{txn_id}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Amount</td><td style="padding:6px 0;font-weight:bold;font-size:16px;">&#8377;{amount:,.2f}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Location</td><td style="padding:6px 0;">{city}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Risk Score</td><td style="padding:6px 0;color:#f59e0b;font-weight:bold;">{risk:.0f}/100</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Reason</td><td style="padding:6px 0;">{reason}</td></tr>
          </table>
        </div>
        <div style="background:#1a2236;border:2px solid #f59e0b;border-radius:8px;padding:20px;text-align:center;margin-bottom:16px;">
          <p style="margin:0 0 8px;color:#64748b;font-size:13px;">YOUR ONE-TIME PASSWORD</p>
          <div style="font-size:36px;font-weight:900;letter-spacing:0.3em;color:#f59e0b;font-family:monospace;">{otp}</div>
          <p style="margin:8px 0 0;color:#64748b;font-size:11px;">Valid for 5 minutes</p>
        </div>
        <p style="color:#64748b;font-size:12px;text-align:center;">Enter OTP on ArgusAI dashboard to approve.<br>If this wasn't you, click Block immediately.</p>
        <p style="color:#374151;font-size:11px;text-align:center;margin-top:16px;">{time_now}</p>
      </div>
    </div>"""


def _block_email_html(txn, result):
    amount   = txn.get("amount", 0)
    txn_id   = txn.get("transaction_id", "TXN???")
    city     = txn.get("transaction_city", "Unknown")
    risk     = result.get("risk_score", 0)
    time_now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    signals  = []
    if txn.get("is_night"):                        signals.append("Night-time transaction")
    if txn.get("device_mismatch"):                 signals.append("Unknown device")
    if txn.get("distance_from_home_km", 0) > 500: signals.append(f"{txn['distance_from_home_km']:.0f}km from home")
    if txn.get("amount_vs_avg_ratio", 0) > 5:     signals.append("Amount far above average")
    rows = "".join([f"<tr><td style='padding:4px 0;'>• {s}</td></tr>" for s in signals]) or "<tr><td>Multiple risk signals</td></tr>"
    return f"""<div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;background:#0a0e1a;color:#e2e8f0;border-radius:12px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#ef4444,#7f1d1d);padding:24px;text-align:center;">
        <h1 style="margin:0;font-size:24px;color:#fff;">🚫 Transaction BLOCKED</h1>
        <p style="margin:8px 0 0;color:rgba(255,255,255,0.8);">ArgusAI blocked high-risk transaction</p>
      </div>
      <div style="padding:24px;">
        <div style="background:#111827;border-radius:8px;padding:16px;margin-bottom:16px;">
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Transaction ID</td><td style="padding:6px 0;font-family:monospace;font-size:13px;">{txn_id}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Amount</td><td style="padding:6px 0;font-weight:bold;color:#ef4444;font-size:16px;">&#8377;{amount:,.2f}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Location</td><td style="padding:6px 0;">{city}</td></tr>
            <tr><td style="padding:6px 0;color:#64748b;font-size:13px;">Risk Score</td><td style="padding:6px 0;color:#ef4444;font-weight:bold;">{risk:.0f}/100</td></tr>
          </table>
        </div>
        <div style="background:#1a2236;border:2px solid #ef4444;border-radius:8px;padding:16px;margin-bottom:16px;">
          <p style="margin:0 0 10px;font-weight:bold;color:#ef4444;">Risk Signals:</p>
          <table style="width:100%;font-size:13px;">{rows}</table>
        </div>
        <p style="color:#64748b;font-size:12px;text-align:center;">Contact bank if this was you.</p>
        <p style="color:#374151;font-size:11px;text-align:center;margin-top:16px;">{time_now}</p>
      </div>
    </div>"""


# ─── Public API (sends both Telegram + Email) ─────────────────────────────────
async def send_otp_alert(txn: dict, result: dict) -> dict:
    """Send OTP alert via Telegram AND Email."""
    otp     = generate_otp()
    txn_id  = txn.get("transaction_id", "TXN???")
    amount  = txn.get("amount", 0)
    city    = txn.get("transaction_city", "Unknown")
    reason  = result.get("shap_explanation", [{}])[0].get("label", "unusual pattern")

    _otp_store[txn_id] = otp

    # Telegram message
    telegram_msg = (
        f"⚠️ <b>ArgusAI Security Alert</b>\n\n"
        f"🔔 <b>Suspicious Transaction Detected</b>\n"
        f"─────────────────────────\n"
        f"💳 Transaction : <code>{txn_id}</code>\n"
        f"💰 Amount      : ₹{amount:,.2f}\n"
        f"📍 Location    : {city}\n"
        f"⚡ Risk Score  : {result.get('risk_score', 0):.0f}/100\n"
        f"🔍 Reason      : {reason}\n"
        f"─────────────────────────\n"
        f"🔐 <b>Your OTP: <code>{otp}</code></b>\n\n"
        f"Reply <b>YES</b> to approve or <b>NO</b> to block.\n"
        f"⏰ Valid for 5 minutes."
    )

    # Send both
    telegram_sent = await _send_telegram(telegram_msg)
    
    email_subject = f"ArgusAI: Verify Transaction Rs.{amount:,.0f} - OTP inside"
    loop = asyncio.get_event_loop()
    email_sent = await loop.run_in_executor(
        None, _send_email, email_subject, _otp_email_html(txn, result, otp)
    )

    return {"otp": otp, "sent": telegram_sent or email_sent, "txn_id": txn_id}


async def send_block_alert(txn: dict, result: dict) -> bool:
    """Send block notification via Telegram AND Email."""
    txn_id = txn.get("transaction_id", "TXN???")
    amount = txn.get("amount", 0)
    city   = txn.get("transaction_city", "Unknown")

    # Build signals
    signals = []
    if txn.get("is_night"):          signals.append("🌙 Night-time transaction")
    if txn.get("device_mismatch"):   signals.append("📱 Unknown device")
    if txn.get("distance_from_home_km", 0) > 500:
        signals.append(f"📍 {txn['distance_from_home_km']:.0f}km from home")
    if txn.get("amount_vs_avg_ratio", 0) > 5:
        signals.append("💸 Amount far above average")
    signal_text = "\n".join(signals) if signals else "Multiple risk signals"

    # Telegram message
    telegram_msg = (
        f"🚫 <b>ArgusAI — Transaction BLOCKED</b>\n\n"
        f"High-risk transaction automatically blocked.\n"
        f"─────────────────────────\n"
        f"💳 Transaction : <code>{txn_id}</code>\n"
        f"💰 Amount      : ₹{amount:,.2f}\n"
        f"📍 Location    : {city}\n"
        f"⚡ Risk Score  : {result.get('risk_score', 0):.0f}/100\n\n"
        f"<b>Risk Signals:</b>\n{signal_text}\n"
        f"─────────────────────────\n"
        f"If this was you, contact support immediately.\n"
        f"🕐 {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    )

    # Send both
    telegram_sent = await _send_telegram(telegram_msg)
    
    email_subject = f"ArgusAI: Transaction BLOCKED - Rs.{amount:,.0f} HIGH RISK"
    loop = asyncio.get_event_loop()
    email_sent = await loop.run_in_executor(
        None, _send_email, email_subject, _block_email_html(txn, result)
    )

    return telegram_sent or email_sent


def verify_otp(txn_id: str, user_otp: str) -> bool:
    stored = _otp_store.get(txn_id)
    if stored and stored == user_otp.strip():
        del _otp_store[txn_id]
        return True
    return False