# 🛡️ ArgusAI — AI-Based Fraud Detection & Risk Management

Real-time fraud detection system with:
- **XGBoost + Autoencoder** hybrid ML model
- **SHAP** explainability
- **FastAPI** REST + WebSocket backend
- **React** live dashboard
- **Telegram OTP** alerts (optional)
- Auto-streaming synthetic transaction pipeline

---

## 📁 Project Structure

```
argusai/
├── data/
│   └── generate_dataset.py     # Generates 50,000 synthetic transactions
├── ml/
│   ├── train.py                # Trains XGBoost + Autoencoder
│   ├── predict.py              # Risk scoring engine
│   └── models/                 # Saved model artifacts (auto-created)
├── backend/
│   ├── main.py                 # FastAPI app (REST + WebSocket)
│   ├── transaction_stream.py   # Live transaction generator
│   ├── alert.py                # Telegram OTP alerts
│   └── database.py             # SQLite audit log
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Main dashboard
│   │   ├── index.css           # Dark theme styles
│   │   └── components/
│   │       ├── StatsBar.jsx    # Live metrics
│   │       ├── RiskGauge.jsx   # Animated risk meter
│   │       ├── ShapPanel.jsx   # SHAP explainability
│   │       ├── AlertBanner.jsx # OTP / Block alerts
│   │       └── Dashboard.jsx   # Transaction feed table
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
└── README.md
```

---

## 🚀 Setup (Windows — VSCode Terminal)

### STEP 1 — Install Python dependencies
```bash
cd argusai
pip install -r requirements.txt
```

### STEP 2 — Generate the dataset
```bash
python data/generate_dataset.py
```
> Creates `data/transactions.csv` with 50,000 realistic Indian UPI/Card transactions

### STEP 3 — Train the models
```bash
python ml/train.py
```
> Takes ~5-10 minutes. Saves XGBoost, Autoencoder, SHAP explainer to `ml/models/`

### STEP 4 — Start the backend (Terminal 1)
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
> API docs available at: http://localhost:8000/docs

### STEP 5 — Start the frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```
> Dashboard at: http://localhost:3000

---

## 🎯 Demo Flow (For Hackathon Presentation)

1. Open `http://localhost:3000` on your laptop
2. Show the **live transaction stream** auto-running (every 3 seconds)
3. Click **"🚨 Inject Fraud"** button
4. Watch the risk gauge spike to HIGH (red)
5. AlertBanner appears with OTP verification UI
6. Show SHAP panel explaining WHY it's fraud
7. Click any row to inspect individual transactions

---

## 📱 Telegram OTP Setup (Optional but WOW factor)

1. Search `@BotFather` on Telegram
2. Send `/newbot` → get your bot token
3. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Set environment variables:
   ```bash
   set TELEGRAM_TOKEN=your_token_here
   set TELEGRAM_CHAT_ID=your_chat_id_here
   ```

---

## 🏗️ Architecture

```
📱 Auto-generated transactions (every 3s)
        ↓
🌐 FastAPI Backend (port 8000)
        ↓ WebSocket broadcast
🧠 Fraud Engine:
   ├── XGBoost (supervised)     → fraud probability
   ├── Autoencoder (anomaly)    → reconstruction error
   └── Risk Fusion Engine       → 0-100 risk score
        ↓
📊 React Dashboard (port 3000)
        ↓ if MEDIUM risk
📲 Telegram OTP Alert
        ↓ if HIGH risk
🚫 Auto-block + Alert
        ↓
🗃️ SQLite Audit Log
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/transaction` | Analyze a transaction |
| POST | `/api/transaction/fraud` | Inject fraud demo |
| POST | `/api/transaction/simulate` | Simulate random txn |
| GET  | `/api/transactions` | Recent history |
| GET  | `/api/stats` | System statistics |
| POST | `/api/otp/verify` | Verify OTP |
| WS   | `/ws/stream` | Live WebSocket feed |

---

## 🧠 ML Model Details

- **XGBoost** — 400 trees, cost-sensitive (scale_pos_weight), AUC-PR optimized
- **Autoencoder** — 5-layer neural net, trained on normal transactions only
- **Risk Fusion** — XGBoost 60% + Autoencoder 25% + Rules 15%
- **SHAP** — TreeExplainer for feature attribution per transaction
- **Dataset** — 50,000 synthetic Indian payment transactions, 6% fraud rate