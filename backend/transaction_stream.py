"""
ArgusAI — Live Transaction Stream Simulator
Generates realistic UPI/Card transactions every few seconds.
Simulates a real payment network feeding into the fraud engine.
"""

import random, asyncio
from datetime import datetime
import numpy as np

# ─── Reference data (mirrors dataset generator) ───────────────────────────────
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

PAYMENT_TYPES   = ["UPI", "Card", "NetBanking", "Wallet", "NEFT"]
DEVICE_TYPES    = ["Mobile", "Desktop", "Tablet"]
MERCHANT_CATS   = [
    "Grocery", "Electronics", "Travel", "Food", "Fashion",
    "Fuel", "Healthcare", "Entertainment", "Utility", "Jewellery"
]

# Fixed user pool (simulate 500 real users)
USER_PROFILES = {}
for uid in range(1, 501):
    home = random.choice(CITIES)
    USER_PROFILES[uid] = {
        "home_city": home[0], "home_lat": home[1], "home_lon": home[2],
        "avg_spend":    random.uniform(300, 12000),
        "card_age_days": random.randint(30, 1825),
        "device":       random.choice(DEVICE_TYPES),
    }

_txn_counter = 50001   # start after dataset


def _haversine(lat1, lon1, lat2, lon2):
    R = 6371
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((np.radians(lat2-lat1))/2)**2
         + np.cos(phi1)*np.cos(phi2)*np.sin((np.radians(lon2-lon1))/2)**2)
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))


def generate_live_transaction(force_fraud: bool = False) -> dict:
    """
    Generate one realistic transaction.
    force_fraud=True → inject a high-risk transaction (for demo button).
    """
    global _txn_counter
    _txn_counter += 1

    is_fraud = force_fraud or (random.random() < 0.06)
    uid      = random.randint(1, 500)
    user     = USER_PROFILES[uid]
    now      = datetime.now()

    # ── Amount ────────────────────────────────────────────────────────────────
    if is_fraud:
        amount = round(random.choice([
            random.uniform(50000, 180000),
            random.uniform(1, 9),
        ]), 2)
    else:
        amount = round(np.random.lognormal(
            mean=np.log(max(user["avg_spend"], 1)), sigma=0.7), 2)
        amount = max(10, min(amount, 75000))

    # ── Location ──────────────────────────────────────────────────────────────
    if is_fraud and random.random() < 0.6:
        city = random.choice([c for c in CITIES if c[0] != user["home_city"]])
    else:
        city = next(c for c in CITIES if c[0] == user["home_city"])

    txn_lat = city[1] + np.random.normal(0, 0.04)
    txn_lon = city[2] + np.random.normal(0, 0.04)
    distance = round(_haversine(user["home_lat"], user["home_lon"],
                                txn_lat, txn_lon), 2)

    # ── Device ────────────────────────────────────────────────────────────────
    if is_fraud and random.random() < 0.5:
        device = random.choice([d for d in DEVICE_TYPES if d != user["device"]])
    else:
        device = user["device"]

    # ── Derived features ──────────────────────────────────────────────────────
    avg_7d            = round(user["avg_spend"] * random.uniform(0.7, 1.3), 2)
    amount_vs_avg     = round(amount / (avg_7d + 1), 4)
    daily_count       = random.randint(1, 15) if is_fraud else random.randint(1, 5)
    pay_type          = random.choice(["UPI","Card","Wallet"]) if is_fraud \
                        else random.choice(PAYMENT_TYPES)
    merchant_cat      = random.choice(["Jewellery","Electronics","Travel"]) \
                        if (is_fraud and random.random() < 0.5) \
                        else random.choice(MERCHANT_CATS)
    device_mismatch   = int(device != user["device"])
    is_night          = int(now.hour < 6 or now.hour >= 22)

    return {
        "transaction_id":        f"TXN{_txn_counter:06d}",
        "user_id":               uid,
        "timestamp":             now.strftime("%Y-%m-%d %H:%M:%S"),
        "amount":                amount,
        "payment_type":          pay_type,
        "merchant_category":     merchant_cat,
        "transaction_city":      city[0],
        "transaction_lat":       round(txn_lat, 4),
        "transaction_lon":       round(txn_lon, 4),
        "home_city":             user["home_city"],
        "home_lat":              user["home_lat"],
        "home_lon":              user["home_lon"],
        "distance_from_home_km": distance,
        "device_type":           device,
        "user_home_device":      user["device"],
        "device_mismatch":       device_mismatch,
        "card_age_days":         user["card_age_days"],
        "transaction_hour":      now.hour,
        "transaction_day":       now.weekday(),
        "is_weekend":            int(now.weekday() >= 5),
        "is_night":              is_night,
        "daily_txn_count":       daily_count,
        "avg_amount_7d":         avg_7d,
        "amount_vs_avg_ratio":   amount_vs_avg,
        # meta for dashboard only (not fed to model)
        "_simulated_fraud":      is_fraud,
    }


async def stream_transactions(callback, interval_sec: float = 3.0):
    """
    Continuously generate transactions and call `callback(txn)`.
    Use from FastAPI background task.
    """
    while True:
        txn = generate_live_transaction()
        await callback(txn)
        await asyncio.sleep(interval_sec)