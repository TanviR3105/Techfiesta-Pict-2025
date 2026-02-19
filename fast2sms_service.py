"""
Fast2SMS Service
Sends SMS via Fast2SMS API for OTP and alert notifications.
"""

import os
import httpx
from dotenv import load_dotenv

# Load .env first
load_dotenv()

FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "").strip()
ALERT_PHONE_NUMBER = os.getenv("ALERT_PHONE_NUMBER", "").strip()

# Print config on module load
print(f"[Fast2SMS] Configuration loaded:")
print(f"  - API Key: {'✅ Set' if FAST2SMS_API_KEY else '❌ MISSING - Update .env!'}")
print(f"  - Phone Number: {'✅' if ALERT_PHONE_NUMBER else '❌'} ({ALERT_PHONE_NUMBER if ALERT_PHONE_NUMBER else 'None'})")

if FAST2SMS_API_KEY:
    print(f"  - API Key Preview: {FAST2SMS_API_KEY[:10]}...{FAST2SMS_API_KEY[-10:]}")


async def send_otp_sms(phone: str, otp: str, txn_id: str = "") -> dict:
    """Send OTP via SMS using Fast2SMS."""
    if not FAST2SMS_API_KEY or not FAST2SMS_API_KEY.strip():
        print(f"❌ [Fast2SMS] OTP SMS skipped — API key not configured")
        return {"sent": False, "reason": "API key not configured"}

    if not phone or not phone.strip():
        print(f"❌ [Fast2SMS] OTP SMS skipped — phone number not provided")
        return {"sent": False, "reason": "phone number missing"}

    try:
        message = f"ArgusAI: Your OTP is {otp}. Transaction {txn_id}. Valid for 5 mins."
        
        print(f"[Fast2SMS] Sending OTP to {phone}...")
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://www.fast2sms.com/dev/bulkV2",
                params={
                    "authorization": FAST2SMS_API_KEY,
                    "message": message,
                    "numbers": phone,
                },
            )
            
            print(f"[Fast2SMS] Response: HTTP {resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("return") == True or data.get("return") == 1:
                    print(f"✅ [Fast2SMS] OTP sent to {phone}")
                    return {"sent": True, "phone": phone, "otp": otp}
                else:
                    error_msg = data.get("message", "Unknown error")
                    print(f"❌ [Fast2SMS] API returned error: {error_msg}")
                    return {"sent": False, "reason": error_msg}
            else:
                print(f"❌ [Fast2SMS] HTTP {resp.status_code}: {resp.text[:200]}")
                return {"sent": False, "reason": f"HTTP {resp.status_code}"}
    except Exception as e:
        print(f"❌ [Fast2SMS] Exception: {str(e)}")
        return {"sent": False, "reason": str(e)}


async def send_alert_sms(phone: str, alert_type: str, txn_id: str, amount: float, city: str, risk_score: float) -> bool:
    """Send alert SMS for HIGH risk transactions."""
    if not FAST2SMS_API_KEY or not FAST2SMS_API_KEY.strip() or not phone or not phone.strip():
        print(f"❌ [Fast2SMS] Alert SMS skipped — missing config")
        return False

    try:
        if alert_type == "BLOCK":
            message = f"🚫 ArgusAI: Transaction BLOCKED. TXN:{txn_id} ₹{amount:,.0f} from {city}. Risk:{risk_score:.0f}/100. Contact support."
        else:
            message = f"⚠️ ArgusAI: High-risk transaction detected. Amount: ₹{amount:,.0f}. Location: {city}. Please verify."
        
        print(f"[Fast2SMS] Sending {alert_type} alert to {phone}...")
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://www.fast2sms.com/dev/bulkV2",
                params={
                    "authorization": FAST2SMS_API_KEY,
                    "message": message,
                    "numbers": phone,
                },
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("return") == True or data.get("return") == 1:
                    print(f"✅ [Fast2SMS] {alert_type} alert sent to {phone}")
                    return True
            
            print(f"❌ [Fast2SMS] {alert_type} alert failed: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ [Fast2SMS] {alert_type} alert error: {e}")
        return False


def get_configured() -> bool:
    """Check if Fast2SMS is properly configured."""
    return bool(FAST2SMS_API_KEY and ALERT_PHONE_NUMBER)
