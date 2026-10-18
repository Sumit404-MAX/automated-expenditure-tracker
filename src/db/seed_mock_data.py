"""30-Day Realistic UPI Mock Database Seeder (Task S0-02).

Owned by: Sumit Kushwaha (Project Lead)
Purpose: Creates all 6 SQLite v1.1 tables in `tracker_dev.db` and populates
40 realistic Indian UPI transactions + 1 sample PENDING transaction so Saurabh (UI)
and Uday (Analytics) can test charts, popups, and Z-Score math on Day 1.
"""

import sqlite3
from datetime import datetime, timedelta

DB_FILE = "tracker_dev.db"

SCHEMA_SQL = """
PRAGMA journal_mode = MEMORY;
PRAGMA synchronous = OFF;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_budget REAL NOT NULL DEFAULT 15000.0,
    primary_upi_app TEXT DEFAULT 'com.google.android.apps.nbu.paisa.user',
    biometric_enabled BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    budget_limit REAL DEFAULT NULL,
    icon_name TEXT,
    is_default BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    payee_vpa TEXT NOT NULL,
    payee_name TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    category_id INTEGER,
    is_anomaly BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS pending_transactions (
    internal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    payee_vpa TEXT NOT NULL,
    payee_name TEXT NOT NULL,
    raw_qr_uri TEXT,
    init_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'PENDING'
);

CREATE TABLE IF NOT EXISTS merchant_tags (
    vpa_pattern TEXT PRIMARY KEY,
    category_id INTEGER,
    confidence REAL DEFAULT 1.0,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS bill_splits (
    split_id INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id TEXT NOT NULL,
    friend_name TEXT NOT NULL,
    friend_contact TEXT,
    share_amount REAL NOT NULL,
    is_settled BOOLEAN DEFAULT 0,
    FOREIGN KEY (txn_id) REFERENCES transactions(txn_id)
);
"""


def seed_mock_database(db_path: str = DB_FILE) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    # 1. Seed user profile
    cur.execute("DELETE FROM user_profile;")
    cur.execute(
        "INSERT INTO user_profile (id, name, monthly_budget, primary_upi_app, biometric_enabled) VALUES (1, 'Sumit Kushwaha', 12000.0, 'com.google.android.apps.nbu.paisa.user', 0);"
    )

    # 2. Seed categories
    categories = [
        (1, "Food & Dining", 3500.0, "RESTAURANT", 1),
        (2, "Travel", 2000.0, "DIRECTIONS_CAR", 1),
        (3, "Groceries", 2500.0, "SHOPPING_CART", 1),
        (4, "Fuel", 2000.0, "LOCAL_GAS_STATION", 1),
        (5, "Utilities", 2000.0, "BOLT", 1),
        (6, "Uncategorized", None, "HELP_OUTLINE", 1),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO categories (category_id, name, budget_limit, icon_name, is_default) VALUES (?, ?, ?, ?, ?);",
        categories,
    )

    # 3. Seed merchant_tags (Tier 1 Heuristic Memory)
    merchant_tags = [
        ("ramesh.chai@ybl", 1, 1.0),
        ("nitra.canteen@okaxis", 1, 1.0),
        ("sharma.kirana@paytm", 3, 1.0),
    ]
    cur.executemany(
        "INSERT OR REPLACE INTO merchant_tags (vpa_pattern, category_id, confidence) VALUES (?, ?, ?);",
        merchant_tags,
    )

    # 4. Seed 40 realistic transactions over the last 25 days
    now = datetime.now()
    sample_rows = []
    base_data = [
        ("zomato.order@hdfcbank", "Zomato Limited", 180.0, 1, 0, "#Dinner"),
        ("swiggy.instamart@icici", "Swiggy Food", 220.0, 1, 0, ""),
        ("ramesh.chai@ybl", "Ramesh Tea Stall", 20.0, 1, 0, "#Chai"),
        ("ramesh.chai@ybl", "Ramesh Tea Stall", 20.0, 1, 0, "#Chai"),
        ("ramesh.chai@ybl", "Ramesh Tea Stall", 20.0, 1, 0, "#Chai"),
        ("ramesh.chai@ybl", "Ramesh Tea Stall", 20.0, 1, 0, "#Chai"),
        ("ramesh.chai@ybl", "Ramesh Tea Stall", 20.0, 1, 0, "#Chai"),
        ("uber.india@axisbank", "Uber Rides", 145.0, 2, 0, "#College"),
        ("rapido.bike@ybl", "Rapido Captain", 65.0, 2, 0, ""),
        ("irctc.tourism@sbi", "IRCTC Rail Connect", 480.0, 2, 0, "#HomeTrip"),
        ("blinkit.grofers@kotak", "Blinkit Commerce", 310.0, 3, 0, ""),
        ("sharma.kirana@paytm", "Sharma Kirana Store", 190.0, 3, 0, "#Hostel"),
        ("dmart.ready@icici", "Avenue Supermarts DMart", 640.0, 3, 0, ""),
        ("hpcl.petrol@sbi", "HPCL Highway Pump", 250.0, 4, 0, "#Bike"),
        ("iocl.fuel@axis", "Indian Oil SmartFill", 300.0, 4, 0, ""),
        ("jio.recharge@paytm", "Jio Prepaid Recharge", 299.0, 5, 0, "#Mobile"),
        ("uppcl.bill@sbi", "UPPCL Electricity", 850.0, 5, 0, "#RoomBill"),
        ("bikanervala.gzb@okicici", "Bikanervala Ghaziabad", 160.0, 1, 0, ""),
        ("haldiram.snacks@hdfc", "Haldiram Snacks", 210.0, 1, 0, ""),
        ("zomato.party@hdfcbank", "Zomato Celebration Order", 1450.0, 1, 1, "#BirthdaySpike"),
    ]

    for idx in range(40):
        vpa, name, amt, cat_id, is_anom, note = base_data[idx % len(base_data)]
        txn_time = (now - timedelta(days=(25 - (idx // 2)), hours=(idx % 8))).strftime("%Y-%m-%d %H:%M:%S")
        txn_id = f"TXN202610{idx + 1001:04d}"
        sample_rows.append((txn_id, amt + (idx % 3) * 5.0, vpa, name, txn_time, cat_id, is_anom, note))

    cur.execute("DELETE FROM transactions;")
    cur.executemany(
        "INSERT INTO transactions (txn_id, amount, payee_vpa, payee_name, timestamp, category_id, is_anomaly, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        sample_rows,
    )

    # 5. Seed 1 unresolved PENDING transaction to test the 1-Tap Resume Fallback Popup
    cur.execute("DELETE FROM pending_transactions;")
    cur.execute(
        """INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status)
           VALUES (120.0, 'sonu.snacks@ybl', 'SONU SNACKS', 'upi://pay?pa=sonu.snacks@ybl&pn=SONU%20SNACKS&mc=5814&sign=MOCKSIGNATURE&cu=INR', 'PENDING');"""
    )

    conn.commit()
    conn.close()
    print(f"[OK] Seeded {db_path} with 6 v1.1 tables, 40 transactions, and 1 PENDING fallback test row.")


if __name__ == "__main__":
    seed_mock_database()
