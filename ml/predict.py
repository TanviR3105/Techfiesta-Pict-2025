"""
ArgusAI — Prediction & Risk Engine
Loads trained models and scores any incoming transaction.
Returns: risk_score (0-100), risk_level, action, shap_explanation
"""

import os, json, warnings
warnings.filterwarnings("ignore")

import numpy as np
import joblib
import shap
import tensorflow as tf

# ─── Paths ────────────────────────────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")

# ─── Thresholds → risk levels ─────────────────────────────────────────────────
RISK_THRESHOLDS = {
    "LOW":    (0,  40),
    "MEDIUM": (40, 70),
    "HIGH":   (70, 100),
}


# ─── Singleton model loader ────────────────────────────────────────────────────
class FraudEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        print("🔄 Loading ArgusAI models...")

        self.xgb_model    = joblib.load(os.path.join(MODEL_DIR, "xgb_model.joblib"))
        self.scaler       = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
        self.le_dict      = joblib.load(os.path.join(MODEL_DIR, "label_encoders.joblib"))
        self.explainer    = joblib.load(os.path.join(MODEL_DIR, "shap_explainer.joblib"))
        self.autoencoder  = tf.keras.models.load_model(
                                os.path.join(MODEL_DIR, "autoencoder.keras"))

        with open(os.path.join(MODEL_DIR, "model_meta.json")) as f:
            self.meta = json.load(f)

        self.ae_threshold  = self.meta["ae_threshold"]
        self.feature_cols  = self.meta["feature_cols"]
        self.num_features  = self.meta["numeric_features"]
        self.cat_features  = self.meta["cat_features"]
        self._loaded       = True
        print("✅ Models loaded.")

    # ── Feature vector ─────────────────────────────────────────────────────────
    def _build_features(self, txn: dict) -> np.ndarray:
        row = []

        # Numeric
        for col in self.num_features:
            row.append(float(txn.get(col, 0)))

        # Categorical encoded
        for col in self.cat_features:
            le  = self.le_dict[col]
            val = str(txn.get(col, ""))
            try:
                enc = le.transform([val])[0]
            except ValueError:
                enc = 0   # unseen category → default 0
            row.append(float(enc))

        return np.array(row, dtype=np.float32).reshape(1, -1)

    # ── Risk Score Fusion ──────────────────────────────────────────────────────
    def _fuse_risk(self, fraud_prob: float, anomaly_score: float,
                   is_anomaly: bool, txn: dict) -> float:
        """
        Combine signals into 0-100 risk score.
        Weights:  XGBoost 60%  |  Autoencoder 25%  |  Rules 15%
        """
        xgb_component = fraud_prob * 60

        # Normalize anomaly score to 0-1 range
        ae_norm  = min(anomaly_score / (self.ae_threshold * 3), 1.0)
        ae_component = ae_norm * 25

        # Rule-based component (0-15)
        rule_score = 0
        if txn.get("is_night"):            rule_score += 4
        if txn.get("device_mismatch"):     rule_score += 4
        if txn.get("distance_from_home_km", 0) > 500:  rule_score += 4
        if txn.get("amount_vs_avg_ratio",  0) > 5:      rule_score += 3

        risk = xgb_component + ae_component + min(rule_score, 15)
        return round(min(max(risk, 0), 100), 2)

    # ── Decision ──────────────────────────────────────────────────────────────
    @staticmethod
    def _decide(risk_score: float):
        if risk_score < 40:
            return "LOW",    "ALLOW",    "✅ Transaction approved"
        elif risk_score < 70:
            return "MEDIUM", "OTP",      "⚠️  Step-up verification required (OTP)"
        else:
            return "HIGH",   "BLOCK",    "🚫 Transaction blocked — high fraud risk"

    # ── SHAP Explanation ───────────────────────────────────────────────────────
    def _explain(self, X_scaled: np.ndarray, top_n: int = 4) -> list[dict]:
        shap_vals = self.explainer.shap_values(X_scaled)[0]   # for fraud class
        feature_names = self.feature_cols

        pairs = sorted(zip(feature_names, shap_vals),
                       key=lambda x: abs(x[1]), reverse=True)

        explanations = []
        label_map = {
            "amount":                  "Transaction amount",
            "distance_from_home_km":   "Distance from home",
            "is_night":                "Night-time transaction",
            "device_mismatch":         "Device mismatch",
            "transaction_hour":        "Transaction hour",
            "amount_vs_avg_ratio":     "Amount vs 7-day average",
            "daily_txn_count":         "Daily transaction count",
            "card_age_days":           "Card age",
            "payment_type_enc":        "Payment method",
            "merchant_category_enc":   "Merchant category",
        }

        for feat, val in pairs[:top_n]:
            direction = "↑ increases" if val > 0 else "↓ decreases"
            label     = label_map.get(feat, feat.replace("_", " ").title())
            explanations.append({
                "feature":   feat,
                "label":     label,
                "shap_val":  round(float(val), 4),
                "direction": direction,
                "impact":    "HIGH" if abs(val) > 0.3 else
                             "MEDIUM" if abs(val) > 0.1 else "LOW",
            })
        return explanations

    # ── Main Predict ───────────────────────────────────────────────────────────
    def predict(self, txn: dict) -> dict:
        self.load()

        # Build feature vector
        X_raw    = self._build_features(txn)
        X_scaled = self.scaler.transform(X_raw)

        # XGBoost fraud probability
        fraud_prob = float(self.xgb_model.predict_proba(X_scaled)[0][1])

        # Autoencoder anomaly
        recon        = self.autoencoder.predict(X_scaled, verbose=0)
        ae_error     = float(np.mean(np.square(X_scaled - recon)))
        is_anomaly   = ae_error > self.ae_threshold

        # Fuse risk score
        risk_score   = self._fuse_risk(fraud_prob, ae_error, is_anomaly, txn)
        risk_level, action, message = self._decide(risk_score)

        # SHAP explanations
        explanations = self._explain(X_scaled)

        return {
            "risk_score":      risk_score,
            "risk_level":      risk_level,
            "action":          action,
            "message":         message,
            "fraud_prob":      round(fraud_prob * 100, 2),
            "anomaly_score":   round(ae_error, 6),
            "is_anomaly":      bool(is_anomaly),
            "shap_explanation": explanations,
            "model_version":   "ArgusAI-v1.0",
        }


# ─── Singleton accessor ───────────────────────────────────────────────────────
_engine = FraudEngine()

def predict_transaction(txn: dict) -> dict:
    return _engine.predict(txn)


# ─── Quick test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_legit = {
        "amount": 450.0, "distance_from_home_km": 2.5,
        "card_age_days": 730, "transaction_hour": 14,
        "transaction_day": 2, "is_weekend": 0, "is_night": 0,
        "device_mismatch": 0, "daily_txn_count": 2,
        "avg_amount_7d": 500.0, "amount_vs_avg_ratio": 0.9,
        "payment_type": "UPI", "merchant_category": "Grocery",
        "device_type": "Mobile",
    }
    sample_fraud = {
        "amount": 95000.0, "distance_from_home_km": 850.0,
        "card_age_days": 45, "transaction_hour": 2,
        "transaction_day": 6, "is_weekend": 1, "is_night": 1,
        "device_mismatch": 1, "daily_txn_count": 12,
        "avg_amount_7d": 500.0, "amount_vs_avg_ratio": 190.0,
        "payment_type": "Card", "merchant_category": "Jewellery",
        "device_type": "Desktop",
    }

    import json
    print("\n=== LEGITIMATE TRANSACTION ===")
    print(json.dumps(predict_transaction(sample_legit), indent=2))
    print("\n=== FRAUD TRANSACTION ===")
    print(json.dumps(predict_transaction(sample_fraud), indent=2))
