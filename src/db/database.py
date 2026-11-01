"""
src/db/database.py
Anuj Kushwaha — Production SQLite v1.1 Database Access Layer (Task S1-01).
Automated Expenditure Tracker with QR-Integrated Payment Gateway Log Analysis.
"""

from contextlib import contextmanager
import os
import sqlite3
from datetime import datetime

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

CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_pending_status ON pending_transactions(status);
"""

DEFAULT_CATEGORIES = [
    (1, "Food & Dining", 4000.0, "restaurant", 1),
    (2, "Travel", 2500.0, "directions_subway", 1),
    (3, "Groceries", 2500.0, "shopping_cart", 1),
    (4, "Fuel", 1500.0, "local_gas_station", 1),
    (5, "Utilities", 1000.0, "power", 1),
    (6, "Uncategorized", 500.0, "help_outline", 1),
]


@contextmanager
def get_db_connection(db_path: str = DB_FILE, timeout: float = 10.0):
    """
    Context manager that opens an SQLite connection, enables foreign keys and WAL mode,
    and guarantees conn.close() on exit to avoid Windows file locks (WinError 32).
    """
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str = DB_FILE) -> None:
    """Initializes all 6 v1.1 tables, indices, and ensures baseline seed records exist."""
    with get_db_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        cur = conn.cursor()

        # Seed categories if table is empty
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            for cid, name, limit, icon, is_def in DEFAULT_CATEGORIES:
                cur.execute(
                    "INSERT OR REPLACE INTO categories (category_id, name, budget_limit, icon_name, is_default) VALUES (?, ?, ?, ?, ?)",
                    (cid, name, limit, icon, is_def),
                )

        # Seed default profile if table is empty
        cur.execute("SELECT COUNT(*) FROM user_profile")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO user_profile (name, monthly_budget, primary_upi_app, biometric_enabled) VALUES (?, ?, ?, ?)",
                ("Anuj Kushwaha", 12000.0, "GPay", 0),
            )
        conn.commit()


def create_pending_txn(
    amount: float, payee_vpa: str, payee_name: str, raw_qr_uri: str, db_path: str = DB_FILE
) -> int:
    """Logs payment intent before launching external UPI app. Returns unique auto-increment internal_id."""
    init_db(db_path)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, init_time, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
            (float(amount), str(payee_vpa).strip(), str(payee_name).strip(), str(raw_qr_uri).strip(), now_str),
        )
        conn.commit()
        return cur.lastrowid


def get_unresolved_pending(db_path: str = DB_FILE) -> list:
    """Returns unresolved pending transactions ordered from newest to oldest for app resume check."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT internal_id, amount, payee_vpa, payee_name, raw_qr_uri, init_time, status FROM pending_transactions WHERE status = 'PENDING' ORDER BY internal_id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_pending_txn(
    internal_id: int,
    status: str = "RESOLVED",
    txn_id: str = None,
    category_id: int = None,
    is_anomaly: bool = None,
    notes: str = "",
    db_path: str = DB_FILE,
) -> dict:
    """
    Atomically resolves a pending transaction strictly targeting WHERE internal_id = ?.
    If confirmed ('RESOLVED'), inserts into transactions table with auto-generated fallback txn_id if stripped.
    """
    init_db(db_path)
    status_upper = status.upper() if status else "RESOLVED"
    with get_db_connection(db_path) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT amount, payee_vpa, payee_name FROM pending_transactions WHERE internal_id = ?",
            (internal_id,),
        ).fetchone()

        if not row:
            return {"success": False, "error": f"internal_id {internal_id} not found"}

        cur.execute(
            "UPDATE pending_transactions SET status = ? WHERE internal_id = ?",
            (status_upper, internal_id),
        )

        tid = None
        if status_upper == "RESOLVED":
            amount = row["amount"]
            payee_vpa = row["payee_vpa"]
            payee_name = row["payee_name"]

            # Category resolution: explicit override -> Uday tagger -> Tier 1 SQLite -> 6 (Uncategorized)
            if category_id is not None:
                cid = category_id
            else:
                try:
                    from src.contracts import categorize_transaction
                    tag_res = categorize_transaction(payee_vpa, payee_name, db_path=db_path)
                    cid = tag_res.get("category_id", 6)
                except Exception:
                    tag_row = cur.execute(
                        "SELECT category_id FROM merchant_tags WHERE vpa_pattern = ?",
                        (payee_vpa.lower().strip(),),
                    ).fetchone()
                    cid = tag_row["category_id"] if tag_row else 6

            # Anomaly resolution: explicit override -> Uday Z-Score engine -> 0 (Normal)
            if is_anomaly is not None:
                anom = 1 if is_anomaly else 0
            else:
                try:
                    from src.contracts import detect_spending_anomaly
                    anom_res = detect_spending_anomaly(cid, amount, db_path=db_path)
                    anom = 1 if anom_res.get("is_anomaly", False) else 0
                except Exception:
                    anom = 0

            # Fallback for stripped P2P gateway transaction IDs
            tid = txn_id or f"MANUAL_VERIFY_{int(datetime.now().timestamp() * 1000)}"
            now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                "INSERT OR REPLACE INTO transactions (txn_id, amount, payee_vpa, payee_name, timestamp, category_id, is_anomaly, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, amount, payee_vpa, payee_name, now_ts, cid, anom, notes or "1-Tap Verified"),
            )

        conn.commit()
        return {"success": True, "internal_id": internal_id, "status": status_upper, "txn_id": tid}


def get_user_profile(db_path: str = DB_FILE) -> dict:
    """Fetches user profile dictionary."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM user_profile LIMIT 1").fetchone()
        return dict(row) if row else {}


def update_monthly_budget(new_budget: float, db_path: str = DB_FILE) -> bool:
    """Updates the user's monthly budget threshold."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        conn.execute(
            "UPDATE user_profile SET monthly_budget = ? WHERE id = (SELECT id FROM user_profile LIMIT 1)",
            (float(new_budget),),
        )
        conn.commit()
        return True


def get_categories(db_path: str = DB_FILE) -> list:
    """Fetches all predefined categories and budget limits."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT category_id, name, budget_limit, icon_name, is_default FROM categories ORDER BY category_id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def save_merchant_tag(payee_vpa: str, category_id: int, confidence: float = 1.0, db_path: str = DB_FILE) -> bool:
    """Persists manual user tag into Tier 1 merchant_tags memory table."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO merchant_tags (vpa_pattern, category_id, confidence) VALUES (?, ?, ?)",
            (payee_vpa.lower().strip(), int(category_id), float(confidence)),
        )
        conn.commit()
        return True


def get_recent_transactions(limit: int = 10, db_path: str = DB_FILE) -> list:
    """Returns recently settled transactions formatted with category names."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT t.txn_id, t.amount, t.payee_vpa, t.payee_name, t.timestamp, c.name AS category_name, t.is_anomaly, t.notes "
            "FROM transactions t LEFT JOIN categories c ON t.category_id = c.category_id "
            "ORDER BY t.timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def _cleanup_test_db(path: str) -> None:
    """Safely removes temporary test database and WAL sidecar files on Windows."""
    for f in [path, f"{path}-wal", f"{path}-shm"]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except PermissionError:
                pass


# Mandatory Isolated Self-Test Suite (Priority Upgrade 1)
if __name__ == "__main__":
    test_db = "test_tracker_anuj.db"
    _cleanup_test_db(test_db)

    print("--- [Anuj S1-01] Running Isolated Database Self-Test Suite ---")

    # 1. Test init_db and baseline tables
    print("[1/5] Testing init_db() & schema generation...")
    init_db(test_db)
    cats = get_categories(test_db)
    assert len(cats) == 6, f"Expected 6 categories, got {len(cats)}"
    prof = get_user_profile(test_db)
    assert prof.get("monthly_budget") == 12000.0, "Expected default monthly budget Rs. 12,000"

    # 2. Test create_pending_txn
    print("[2/5] Testing create_pending_txn() state logging...")
    p1 = create_pending_txn(199.0, "zomato@icici", "Zomato", "upi://pay?pa=zomato@icici&am=199.00", db_path=test_db)
    p2 = create_pending_txn(45.0, "chai@upi", "Chai Point", "upi://pay?pa=chai@upi&am=45.00", db_path=test_db)
    assert p1 > 0 and p2 > p1, f"Expected sequential positive internal IDs, got {p1}, {p2}"

    # 3. Test get_unresolved_pending
    print("[3/5] Testing get_unresolved_pending() ordering...")
    unresolved = get_unresolved_pending(test_db)
    assert len(unresolved) == 2, f"Expected 2 unresolved rows, got {len(unresolved)}"
    assert unresolved[0]["internal_id"] == p2, "Expected DESC ordering (newest first)"

    # 4. Test resolve_pending_txn isolation (WHERE internal_id = ?)
    print("[4/5] Testing resolve_pending_txn() with WHERE internal_id = ?...")
    res = resolve_pending_txn(p1, status="RESOLVED", category_id=1, notes="Lunch order", db_path=test_db)
    assert res["success"] is True
    assert res["txn_id"].startswith("MANUAL_VERIFY_"), "Expected fallback MANUAL_VERIFY_<timestamp> ID"

    # Verify that p2 is untouched and remains PENDING
    remaining = get_unresolved_pending(test_db)
    assert len(remaining) == 1, f"Expected 1 remaining pending row, got {len(remaining)}"
    assert remaining[0]["internal_id"] == p2, f"Expected p2 ({p2}) to remain PENDING"

    # 5. Test Helper CRUD functions
    print("[5/5] Testing helper CRUD queries & updates...")
    recent = get_recent_transactions(5, db_path=test_db)
    assert len(recent) == 1
    assert recent[0]["amount"] == 199.0
    assert recent[0]["category_name"] == "Food & Dining"

    save_merchant_tag("chai@upi", 1, 1.0, db_path=test_db)
    update_monthly_budget(15000.0, db_path=test_db)
    assert get_user_profile(test_db)["monthly_budget"] == 15000.0

    _cleanup_test_db(test_db)
    print("\n[ALL PASS] Anuj S1-01 SQLite v1.1 Database Layer unit tests passed successfully!")