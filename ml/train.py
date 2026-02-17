"""
ArgusAI — Model Training
Trains:
  1. XGBoost classifier  (supervised fraud detection)
  2. Autoencoder         (unsupervised anomaly detection)
Saves all artifacts to ml/models/
"""

import os, sys, warnings
warnings.filterwarnings("ignore")
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
import joblib
import json

from sklearn.model_selection   import train_test_split
from sklearn.preprocessing     import StandardScaler, LabelEncoder
from sklearn.metrics           import (classification_report,
                                       roc_auc_score,
                                       precision_recall_curve,
                                       average_precision_score)
import xgboost as xgb
import shap

import tensorflow as tf
from tensorflow.keras.models  import Model
from tensorflow.keras.layers  import Input, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE, "data", "transactions.csv")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# ─── Features ─────────────────────────────────────────────────────────────────
NUMERIC_FEATURES = [
    "amount", "distance_from_home_km", "card_age_days",
    "transaction_hour", "transaction_day",
    "is_weekend", "is_night", "device_mismatch",
    "daily_txn_count", "avg_amount_7d", "amount_vs_avg_ratio",
]

CATEGORICAL_FEATURES = ["payment_type", "merchant_category", "device_type"]
TARGET = "is_fraud"


# ─── Data Loading & Feature Engineering ───────────────────────────────────────
def load_and_prepare(path):
    print("📂 Loading dataset...")
    df = pd.read_csv(path)
    print(f"   Shape: {df.shape}  |  Fraud rate: {df[TARGET].mean()*100:.2f}%")

    # Encode categoricals
    le_dict = {}
    for col in CATEGORICAL_FEATURES:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        le_dict[col] = le

    feature_cols = NUMERIC_FEATURES + [c + "_enc" for c in CATEGORICAL_FEATURES]
    X = df[feature_cols].values.astype(np.float32)
    y = df[TARGET].values.astype(np.int32)

    return df, X, y, feature_cols, le_dict


# ─── XGBoost Training ─────────────────────────────────────────────────────────
def train_xgboost(X_train, X_test, y_train, y_test, feature_cols):
    print("\n🚀 Training XGBoost classifier...")

    # Cost-sensitive: weight fraud samples higher
    fraud_count = y_train.sum()
    legit_count = len(y_train) - fraud_count
    scale_pos_weight = legit_count / fraud_count
    print(f"   scale_pos_weight = {scale_pos_weight:.2f}  (penalising false negatives)")

    model = xgb.XGBClassifier(
        n_estimators      = 400,
        max_depth         = 6,
        learning_rate     = 0.05,
        subsample         = 0.8,
        colsample_bytree  = 0.8,
        scale_pos_weight  = scale_pos_weight,   # cost-sensitive
        use_label_encoder = False,
        eval_metric       = "aucpr",
        random_state      = 42,
        n_jobs            = -1,
    )
    model.fit(
        X_train, y_train,
        eval_set              = [(X_test, y_test)],
        verbose               = 50,
    )

    # Evaluate
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc    = roc_auc_score(y_test, y_prob)
    ap     = average_precision_score(y_test, y_prob)

    print(f"\n📊 XGBoost Results:")
    print(f"   ROC-AUC          : {auc:.4f}")
    print(f"   Avg Precision    : {ap:.4f}")
    print(classification_report(y_test, y_pred,
                                target_names=["Legit", "Fraud"]))

    # SHAP explainer
    print("🔍 Building SHAP explainer...")
    explainer = shap.TreeExplainer(model)

    return model, explainer, auc, ap


# ─── Autoencoder Training ─────────────────────────────────────────────────────
def train_autoencoder(X_train, y_train, input_dim):
    print("\n🧠 Training Autoencoder (anomaly detection)...")

    # Train ONLY on normal transactions
    X_normal = X_train[y_train == 0]
    print(f"   Training on {len(X_normal):,} normal transactions")

    inp  = Input(shape=(input_dim,))
    x    = Dense(64, activation="relu")(inp)
    x    = Dropout(0.2)(x)
    x    = Dense(32, activation="relu")(x)
    x    = Dense(16, activation="relu")(x)    # bottleneck
    x    = Dense(32, activation="relu")(x)
    x    = Dropout(0.2)(x)
    x    = Dense(64, activation="relu")(x)
    out  = Dense(input_dim, activation="linear")(x)

    autoencoder = Model(inp, out)
    autoencoder.compile(optimizer="adam", loss="mse")

    cb = EarlyStopping(patience=5, restore_best_weights=True, monitor="val_loss")
    autoencoder.fit(
        X_normal, X_normal,
        epochs          = 60,
        batch_size      = 256,
        validation_split= 0.1,
        callbacks       = [cb],
        verbose         = 1,
    )

    # Compute reconstruction errors on training set
    recon        = autoencoder.predict(X_normal, verbose=0)
    errors       = np.mean(np.square(X_normal - recon), axis=1)
    threshold    = float(np.percentile(errors, 95))   # flag top 5% as anomalous
    print(f"   Anomaly threshold (95th pct): {threshold:.6f}")

    return autoencoder, threshold


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # 1. Load data
    df, X, y, feature_cols, le_dict = load_and_prepare(DATA_PATH)

    # 2. Scale
    scaler  = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\n   Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # 4. Train models
    xgb_model, explainer, auc, ap = train_xgboost(
        X_train, X_test, y_train, y_test, feature_cols)
    ae_model, ae_threshold = train_autoencoder(
        X_train, y_train, X_train.shape[1])

    # 5. Save everything
    print("\n💾 Saving artifacts...")
    joblib.dump(xgb_model,    os.path.join(MODEL_DIR, "xgb_model.joblib"))
    joblib.dump(scaler,       os.path.join(MODEL_DIR, "scaler.joblib"))
    joblib.dump(le_dict,      os.path.join(MODEL_DIR, "label_encoders.joblib"))
    joblib.dump(explainer,    os.path.join(MODEL_DIR, "shap_explainer.joblib"))
    ae_model.save(            os.path.join(MODEL_DIR, "autoencoder.keras"))

    meta = {
        "feature_cols":     feature_cols,
        "numeric_features": NUMERIC_FEATURES,
        "cat_features":     CATEGORICAL_FEATURES,
        "ae_threshold":     ae_threshold,
        "roc_auc":          round(auc, 4),
        "avg_precision":    round(ap, 4),
        "trained_at":       pd.Timestamp.now().isoformat(),
        "n_train":          int(len(X_train)),
        "n_test":           int(len(X_test)),
        "fraud_rate":       float(y.mean()),
    }
    with open(os.path.join(MODEL_DIR, "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("\n✅ All artifacts saved to ml/models/")
    print("   xgb_model.joblib")
    print("   scaler.joblib")
    print("   label_encoders.joblib")
    print("   shap_explainer.joblib")
    print("   autoencoder.keras")
    print("   model_meta.json")
    print(f"\n🎯 Final ROC-AUC: {auc:.4f}  |  Avg Precision: {ap:.4f}")


if __name__ == "__main__":
    main()
