"""
ArgusAI — Database Layer (SQLite)
Stores every transaction decision for audit, analytics, and the dashboard.
"""

import sqlite3, os, json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "argusai.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id   TEXT    NOT NULL,
            user_id          INTEGER,
            timestamp        TEXT,
            amount           REAL,
            payment_type     TEXT,
            merchant_category TEXT,
            transaction_city TEXT,
            device_type      TEXT,
            device_mismatch  INTEGER,
            distance_km      REAL,
            is_night         INTEGER,
            risk_score       REAL,
            risk_level       TEXT,
            action           TEXT,
            fraud_prob       REAL,
            anomaly_score    REAL,
            is_anomaly       INTEGER,
            shap_explanation TEXT,
            model_version    TEXT,
            created_at       TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_risk_profile (
            user_id          INTEGER PRIMARY KEY,
            cumulative_risk  REAL    DEFAULT 0,
            txn_count        INTEGER DEFAULT 0,
            fraud_count      INTEGER DEFAULT 0,
            last_updated     TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialised →", DB_PATH)


def log_transaction(txn: dict, result: dict):
    conn  = get_conn()
    now   = datetime.utcnow().isoformat()

    conn.execute("""
        INSERT INTO transactions
        (transaction_id, user_id, timestamp, amount, payment_type,
         merchant_category, transaction_city, device_type, device_mismatch,
         distance_km, is_night, risk_score, risk_level, action,
         fraud_prob, anomaly_score, is_anomaly, shap_explanation,
         model_version, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        txn.get("transaction_id", f"TXN{int(datetime.utcnow().timestamp())}"),
        txn.get("user_id",         0),
        txn.get("timestamp",       now),
        txn.get("amount",          0),
        txn.get("payment_type",    ""),
        txn.get("merchant_category",""),
        txn.get("transaction_city",""),
        txn.get("device_type",     ""),
        txn.get("device_mismatch", 0),
        txn.get("distance_from_home_km", 0),
        txn.get("is_night",        0),
        result.get("risk_score",   0),
        result.get("risk_level",   ""),
        result.get("action",       ""),
        result.get("fraud_prob",   0),
        result.get("anomaly_score",0),
        int(result.get("is_anomaly", False)),
        json.dumps(result.get("shap_explanation", [])),
        result.get("model_version",""),
        now,
    ))

    # Update rolling user risk profile
    uid = txn.get("user_id", 0)
    conn.execute("""
        INSERT INTO user_risk_profile (user_id, cumulative_risk, txn_count,
                                       fraud_count, last_updated)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            cumulative_risk = (cumulative_risk * txn_count + excluded.cumulative_risk)
                              / (txn_count + 1),
            txn_count       = txn_count + 1,
            fraud_count     = fraud_count + excluded.fraud_count,
            last_updated    = excluded.last_updated
    """, (
        uid,
        result.get("risk_score", 0),
        1 if result.get("action") == "BLOCK" else 0,
        now,
    ))

    conn.commit()
    conn.close()


def get_recent_transactions(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = get_conn()
    total  = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    fraud  = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE action='BLOCK'").fetchone()[0]
    otp    = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE action='OTP'").fetchone()[0]
    allow  = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE action='ALLOW'").fetchone()[0]
    avg_risk = conn.execute(
        "SELECT AVG(risk_score) FROM transactions").fetchone()[0] or 0
    conn.close()
    return {
        "total":     total,
        "blocked":   fraud,
        "otp":       otp,
        "allowed":   allow,
        "fraud_rate": round(fraud / total * 100, 2) if total else 0,
        "avg_risk":   round(avg_risk, 2),
    }


def get_user_profile(user_id: int) -> dict:
    conn = get_conn()
    row  = conn.execute(
        "SELECT * FROM user_risk_profile WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def get_risk_trend(hours: int = 24) -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT
            strftime('%H:00', created_at) as hour,
            COUNT(*) as total,
            SUM(CASE WHEN action='BLOCK' THEN 1 ELSE 0 END) as fraud,
            AVG(risk_score) as avg_risk
        FROM transactions
        WHERE created_at >= datetime('now', ?)
        GROUP BY hour
        ORDER BY hour
    """, (f"-{hours} hours",)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Initialise on import
init_db()