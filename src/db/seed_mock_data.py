"""
src/db/seed_mock_data.py
Compact SQLite v1.1 6-Table Schema & 40-Transaction Seeder (Task S0-02).
"""

import os
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "tracker_dev.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    monthly_budget REAL DEFAULT 0.0,
    primary_upi_app TEXT DEFAULT 'GPay',
    biometric_enabled BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    budget_limit REAL DEFAULT 0.0,
    icon_name TEXT,
    is_default BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    amount REAL NOT NULL,
    payee_vpa TEXT NOT NULL,
    payee_name TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    category_id INTEGER,
    is_anomaly BOOLEAN DEFAULT 0,
    notes TEXT,
    FOREIGN KEY(category_id) REFERENCES categories(category_id)
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
    category_id INTEGER NOT NULL,
    confidence REAL DEFAULT 1.0,
    FOREIGN KEY(category_id) REFERENCES categories(category_id)
);

CREATE TABLE IF NOT EXISTS bill_splits (
    split_id INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id TEXT,
    friend_name TEXT NOT NULL,
    friend_contact TEXT,
    share_amount REAL NOT NULL,
    is_settled BOOLEAN DEFAULT 0,
    FOREIGN KEY(txn_id) REFERENCES transactions(txn_id)
);
"""

DEFAULT_CATEGORIES = [
    (1, "Food & Dining", 4000.0, "restaurant", 1),
    (2, "Travel", 2500.0, "directions_subway", 1),
    (3, "Groceries", 2500.0, "shopping_cart", 1),
    (4, "Fuel", 1500.0, "local_gas_station", 1),
    (5, "Utilities", 1000.0, "power", 1),
    (6, "Uncategorized", 500.0, "help_outline", 1),
]

MERCHANT_TAGS = [
    ("zomato@icici", 1, 1.0), ("swiggy@hdfcbank", 1, 1.0), ("chaipoint@icici", 1, 1.0),
    ("dmrc.metro@axis", 2, 1.0), ("irctc@sbi", 2, 1.0), ("uber@icici", 2, 1.0),
    ("reliancesmart@icici", 3, 1.0), ("zepto@hdfcbank", 3, 1.0),
    ("indianoil@kotak", 4, 1.0), ("tatapower@icici", 5, 1.0),
]

TXN_TEMPLATES = [
    (180.0, "zomato@icici", "Zomato", 1, 0, "Lunch order"),
    (40.0, "dmrc.metro@axis", "Delhi Metro DMRC", 2, 0, "Metro commute"),
    (520.0, "reliancesmart@icici", "Reliance Smart", 3, 0, "Grocery essentials"),
    (50.0, "sharmatea@upi", "Sharma Tea Stall", 1, 0, "Evening chai"),
    (240.0, "swiggy@hdfcbank", "Swiggy", 1, 0, "Dinner order"),
    (400.0, "indianoil@kotak", "Indian Oil Petrol Pump", 4, 0, "Fuel refill"),
    (150.0, "uber@icici", "Uber Rides", 2, 0, "Auto/Cab ride"),
    (120.0, "zepto@hdfcbank", "Zepto", 3, 0, "Milk & bread"),
]

def seed_mock_database(db_path: str = DB_FILE, force_reset: bool = False) -> None:
    """Creates all 6 SQLite v1.1 tables and seeds 40 UPI transactions + 1 PENDING row."""
    if force_reset and os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    cur.execute("DELETE FROM categories WHERE category_id > 6 OR name NOT IN ('Food & Dining','Travel','Groceries','Fuel','Utilities','Uncategorized')")
    for cid, name, limit, icon, is_def in DEFAULT_CATEGORIES:
        cur.execute(
            "INSERT OR REPLACE INTO categories (category_id, name, budget_limit, icon_name, is_default) VALUES (?, ?, ?, ?, ?)",
            (cid, name, limit, icon, is_def),
        )

    cur.execute("SELECT COUNT(*) FROM user_profile")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO user_profile (name, monthly_budget, primary_upi_app, biometric_enabled) VALUES (?, ?, ?, ?)",
            ("Sumit Kushwaha", 12000.0, "GPay", 0),
        )

    for vpa, cid, conf in MERCHANT_TAGS:
        cur.execute("INSERT OR REPLACE INTO merchant_tags (vpa_pattern, category_id, confidence) VALUES (?, ?, ?)", (vpa, cid, conf))

    cur.execute("SELECT COUNT(*) FROM transactions")
    if cur.fetchone()[0] == 0:
        now = datetime.now()
        for i in range(40):
            amt, vpa, name, cid, anom, note = TXN_TEMPLATES[i % len(TXN_TEMPLATES)]
            if i == 14:
                amt, anom, note = 4200.0, 1, "Team party catering (Z-Spike Anomaly)"
            ts = (now - timedelta(days=29 - (i * 29 // 39), hours=i % 12)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"TXN{10001 + i}", amt, vpa, name, ts, cid, anom, note),
            )

    cur.execute("SELECT COUNT(*) FROM pending_transactions WHERE status = 'PENDING'")
    if cur.fetchone()[0] == 0:
        raw_qr = "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&tid=TXN102938&tr=TR998877&sign=MEYCIQC3x...&orgid=159981&mode=02"
        cur.execute(
            "INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status) VALUES (?, ?, ?, ?, 'PENDING')",
            (450.0, "chaipoint@icici", "Chai Point", raw_qr),
        )

    cur.execute("SELECT COUNT(*) FROM bill_splits")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO bill_splits (txn_id, friend_name, friend_contact, share_amount, is_settled) VALUES ('TXN10015', 'Anuj Kushwaha', '+919876543210', 1400.0, 0)")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_mock_database(DB_FILE, force_reset=True)
    with sqlite3.connect(DB_FILE) as conn:
        tx_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        pend_count = conn.execute("SELECT COUNT(*) FROM pending_transactions WHERE status='PENDING'").fetchone()[0]
    assert tx_count == 40, f"Expected 40 transactions, got {tx_count}"
    assert cat_count == 6, f"Expected 6 categories, got {cat_count}"
    assert pend_count >= 1, "Expected at least 1 PENDING row"
    print(f"[PASS] src.db.seed_mock_data: 6 SQLite v1.1 tables ready ({tx_count} txns, {cat_count} categories, {pend_count} pending).")