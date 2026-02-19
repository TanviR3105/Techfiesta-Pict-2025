import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# ─── Config ───────────────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

NUM_USERS        = 500
NUM_TRANSACTIONS = 50000
FRAUD_RATE       = 0.06
OUTPUT_PATH      = os.path.join(os.path.dirname(__file__), "transactions.csv")

# ─── Reference Data ───────────────────────────────────────────────────────────
CITIES = [
    ("Mumbai",    19.0760,  72.8777),
    ("Delhi",     28.6139,  77.2090),
    ("Bangalore", 12.9716,  77.5946),
    ("Hyderabad", 17.3850,  78.4867),
    ("Chennai",   13.0827,  80.2707),
    ("Kolkata",   22.5726,  88.3639),
    ("Pune",      18.5204,  73.8567),
    ("Ahmedabad", 23.0225,  72.5714),
    ("Jaipur",    26.9124,  75.7873),
    ("Lucknow",   26.8467,  80.9462),
]

PAYMENT_TYPES = ["UPI", "Card", "NetBanking", "Wallet", "NEFT"]
DEVICE_TYPES  = ["Mobile", "Desktop", "Tablet"]
MERCHANT_CATS = [
    "Grocery", "Electronics", "Travel", "Food", "Fashion",
    "Fuel", "Healthcare", "Entertainment", "Utility", "Jewellery"
]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi   = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def generate_users(n):
    users = {}
    for uid in range(1, n + 1):
        home_city = random.choice(CITIES)
        users[uid] = {
            "user_id":       uid,
            "home_city":     home_city[0],
            "home_lat":      home_city[1],
            "home_lon":      home_city[2],
            "card_age_days": random.randint(30, 1825),
            "avg_spend":     random.uniform(200, 15000),
            "device":        random.choice(DEVICE_TYPES),
        }
    return users


def pick_timestamp(base_date, is_fraud):
    day_offset = random.randint(0, 364)
    if is_fraud and random.random() < 0.6:
        hour = random.choice([0, 1, 2, 3, 22, 23])
    else:
        hour = random.randint(7, 22)
    return base_date + timedelta(
        days=day_offset, hours=hour,
        minutes=random.randint(0, 59), seconds=random.randint(0, 59)
    )


def pick_location(user, is_fraud):
    if is_fraud and random.random() < 0.55:
        city = random.choice([c for c in CITIES if c[0] != user["home_city"]])
    else:
        city = next(c for c in CITIES if c[0] == user["home_city"])
    lat = city[1] + np.random.normal(0, 0.05)
    lon = city[2] + np.random.normal(0, 0.05)
    return city[0], round(lat, 4), round(lon, 4)


# ─── Main ─────────────────────────────────────────────────────────────────────
def generate_dataset():
    print("⚙️  Generating ArgusAI synthetic dataset...")
    users     = generate_users(NUM_USERS)
    base_date = datetime(2024, 1, 1)
    records   = []

    fraud_indices    = set(random.sample(range(NUM_TRANSACTIONS),
                                         int(NUM_TRANSACTIONS * FRAUD_RATE)))
    user_daily_counts = {}
    user_recent_txns  = {}

    for i in range(NUM_TRANSACTIONS):
        is_fraud = i in fraud_indices
        uid      = random.randint(1, NUM_USERS)
        user     = users[uid]

        ts       = pick_timestamp(base_date, is_fraud)
        date_key = (uid, ts.date())
        user_daily_counts[date_key] = user_daily_counts.get(date_key, 0) + 1

        # Amount
        if is_fraud:
            amount = round(random.choice([
                random.uniform(50000, 200000),
                random.uniform(1, 10),
            ]), 2)
        else:
            amount = round(np.random.lognormal(
                mean=np.log(max(user["avg_spend"], 1)), sigma=0.8), 2)
            amount = max(10, min(amount, 80000))

        # Location
        txn_city, txn_lat, txn_lon = pick_location(user, is_fraud)
        distance = round(haversine(
            user["home_lat"], user["home_lon"], txn_lat, txn_lon), 2)

        # Device
        if is_fraud and random.random() < 0.45:
            device = random.choice([d for d in DEVICE_TYPES if d != user["device"]])
        else:
            device = user["device"]

        # 7-day avg
        recent = user_recent_txns.get(uid, [])
        avg_7d = round(np.mean(recent[-20:]) if recent else user["avg_spend"], 2)
        user_recent_txns.setdefault(uid, []).append(amount)

        # Payment type
        pay_type = random.choice(["UPI", "Card", "Wallet"]) if is_fraud \
                   else random.choice(PAYMENT_TYPES)

        # Merchant
        merchant_cat = random.choice(MERCHANT_CATS)
        if is_fraud and random.random() < 0.5:
            merchant_cat = random.choice(["Jewellery", "Electronics", "Travel"])

        records.append({
            "transaction_id":        f"TXN{i+1:06d}",
            "user_id":               uid,
            "timestamp":             ts.strftime("%Y-%m-%d %H:%M:%S"),
            "amount":                amount,
            "payment_type":          pay_type,
            "merchant_category":     merchant_cat,
            "transaction_city":      txn_city,
            "transaction_lat":       txn_lat,
            "transaction_lon":       txn_lon,
            "home_city":             user["home_city"],
            "home_lat":              user["home_lat"],
            "home_lon":              user["home_lon"],
            "distance_from_home_km": distance,
            "device_type":           device,
            "user_home_device":      user["device"],
            "device_mismatch":       int(device != user["device"]),
            "card_age_days":         user["card_age_days"],
            "transaction_hour":      ts.hour,
            "transaction_day":       ts.weekday(),
            "is_weekend":            int(ts.weekday() >= 5),
            "is_night":              int(ts.hour < 6 or ts.hour >= 22),
            "daily_txn_count":       user_daily_counts[date_key],
            "avg_amount_7d":         avg_7d,
            "amount_vs_avg_ratio":   round(amount / (avg_7d + 1), 4),
            "is_fraud":              int(is_fraud),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df.to_csv(OUTPUT_PATH, index=False)

    total  = len(df)
    frauds = df["is_fraud"].sum()
    print(f"✅ Dataset saved → {OUTPUT_PATH}")
    print(f"   Total        : {total:,}")
    print(f"   Fraud        : {frauds:,}  ({frauds/total*100:.1f}%)")
    print(f"   Legitimate   : {total - frauds:,}")
    return df


if __name__ == "__main__":
    generate_dataset()