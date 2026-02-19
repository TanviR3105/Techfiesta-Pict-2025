# Fast2SMS + ArgusAI Setup Guide

## Quick Start — SMS OTP Integration

### Step 1: Get Fast2SMS API Key
1. Go to https://www.fast2sms.com/
2. Sign up (free for 5 SMS per day for testing)
3. Dashboard → API Settings
4. Copy your **Authorization Key** (API key)

### Step 2: Configure Environment

Create `.env` in the project root with your credentials:

```env
# Fast2SMS (for real SMS OTP delivery)
FAST2SMS_API_KEY=your_api_key_here
ALERT_PHONE_NUMBER=your_10_digit_phone_number_here

# Telegram (backup alerts)
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

**Important: ALERT_PHONE_NUMBER must be 10 digits WITHOUT +91 or country code**
- Example: `9876543210` (not `+919876543210`)

### Step 3: Start Backend

```bash
cd backend
python main.py
```

You should see:
```
✅ FastAPI server running on http://localhost:8000
```

### Step 4: Demo Flow

**Inject a MEDIUM Risk Transaction:**
1. Click the "🚨 Inject Fraud" button on dashboard
2. Select risk level: **MEDIUM**
3. You'll get a real SMS on your phone with OTP code
4. Type the OTP into the dashboard to verify

**Expected Experience:**
- Dashboard shows "🔐 Enter OTP" prompt
- SMS arrives on phone: `ArgusAI: Your OTP is 123456. Transaction TXN0001. Valid for 5 mins.`
- You enter `123456` to verify
- Transaction marked as approved ✅

## Risk-Based Alert Routing

### LOW Risk (< 40 score)
- Silent (logged to database only)
- No SMS, no Telegram

### MEDIUM Risk (40-70 score)  
- **Real SMS via Fast2SMS** with OTP code
- Telegram backup alert
- User must verify with OTP to approve

### HIGH Risk (> 70 score)
- **Telegram alert** with full breakdown + signals
- Brief SMS alert sent
- Transaction auto-blocked

## Troubleshooting

### SMS Not Arriving?
- Check: `ALERT_PHONE_NUMBER` format (10 digits, no +91)
- Check: Fast2SMS API key is valid (test limit: 5 free SMS/day)
- Check: Network connectivity to Fast2SMS API
- **Fallback**: Telegram alerts always work (if configured)

### Telegram Not Working?
- Verify `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` from @BotFather
- Test token validity:
  ```bash
  curl https://api.telegram.org/bot{YOUR_TOKEN}/getMe
  ```

### Test SMS Delivery
```bash
# Run test script
python -c "
import asyncio
from fast2sms_service import send_otp_sms

result = asyncio.run(send_otp_sms('9876543210', '123456', 'TEST001'))
print(result)
"
```

## Demo Talking Points

✨ **"Real-time fraud detection with multi-factor authentication"**

1. **Dual Alert System**: SMS for immediate verification, Telegram for audit trail
2. **Risk-Based Routing**: MEDIUM gets OTP-gated SMS, HIGH gets instant block + admin alert
3. **Production-Ready**: Fast2SMS is used by major Indian banks (yes, really!)
4. **Live Demo**: Pull out phone, get SMS, type OTP, transaction approved in real-time

---

**Ready for demo? Run `python backend/main.py` and start the Vite server!** 🚀
