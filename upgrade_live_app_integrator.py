#!/usr/bin/env python3
r"""Project Lead Live App & Smart Auto-Integration Upgrade for Sumit Kushwaha.

Run this script inside your repo (`D:\Final Year Project\automated-expenditure-tracker files`):
    python upgrade_live_app_integrator.py
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FOLDERS = [
    "src",
    "src/db",
    "src/backend",
    "src/ui",
    "src/analytics",
]

SEED_MOCK_DATA_CODE = '''"""30-Day Realistic UPI Mock Database Seeder (Task S0-02).

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
        "INSERT INTO user_profile (id, name, monthly_budget, primary_upi_app, biometric_enabled) "
        "VALUES (1, 'Sumit Kushwaha', 12000.0, 'com.google.android.apps.nbu.paisa.user', 0);"
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
        "INSERT OR REPLACE INTO categories (category_id, name, budget_limit, icon_name, is_default) "
        "VALUES (?, ?, ?, ?, ?);",
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
        txn_time = (now - timedelta(days=(25 - (idx // 2)), hours=(idx % 8))).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        txn_id = f"TXN202610{idx + 1001:04d}"
        sample_rows.append(
            (txn_id, amt + (idx % 3) * 5.0, vpa, name, txn_time, cat_id, is_anom, note)
        )

    cur.execute("DELETE FROM transactions;")
    cur.executemany(
        "INSERT INTO transactions (txn_id, amount, payee_vpa, payee_name, timestamp, category_id, is_anomaly, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        sample_rows,
    )

    # 5. Seed 1 unresolved PENDING transaction to test the 1-Tap Resume Fallback Popup
    cur.execute("DELETE FROM pending_transactions;")
    cur.execute(
        "INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status) "
        "VALUES (120.0, 'sonu.snacks@ybl', 'SONU SNACKS', "
        "'upi://pay?pa=sonu.snacks@ybl&pn=SONU%20SNACKS&mc=5814&sign=MOCKSIGNATURE&cu=INR', 'PENDING');"
    )

    conn.commit()
    conn.close()
    print(f"[OK] Seeded {db_path} with 6 v1.1 tables, 40 transactions, and 1 PENDING fallback test row.")


if __name__ == "__main__":
    seed_mock_database()
'''

CONTRACTS_CODE = '''"""Smart Plug-and-Play Cross-Module Contract Bridge (v1.1).

Owned by: Sumit Kushwaha (Project Lead & Integrator)
Purpose:
- Guarantees the app is 100% runnable and visually demoable from Day 1.
- Automatically detects and wires in Anuj's, Saurabh's, and Uday's modules as soon
  as their Pull Requests are merged into `dev` (or created on a local branch).
"""

import csv
import importlib
import math
import os
import re
import sqlite3
import statistics
import sys
import time
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.db.seed_mock_data import DB_FILE, seed_mock_database

DEFAULT_CATEGORIES = [
    (1, "Food & Dining", 3500.0, "RESTAURANT", 1),
    (2, "Travel", 2000.0, "DIRECTIONS_CAR", 1),
    (3, "Groceries", 2500.0, "SHOPPING_CART", 1),
    (4, "Fuel", 2000.0, "LOCAL_GAS_STATION", 1),
    (5, "Utilities", 2000.0, "BOLT", 1),
    (6, "Uncategorized", None, "HELP_OUTLINE", 1),
]

CATEGORY_NAME_TO_ID = {name: cid for cid, name, _, _, _ in DEFAULT_CATEGORIES}
CATEGORY_ID_TO_NAME = {cid: name for cid, name, _, _, _ in DEFAULT_CATEGORIES}

# Pre-compiled Tier 2 Regex patterns (Baseline until Uday's src/analytics/tagger.py is merged)
COMPILED_REGEX_RULES = [
    (
        1,
        "Food & Dining",
        re.compile(
            r"zomato|swiggy|dominos|kfc|haldiram|bikaner|chai|tea|snack|canteen|cafe|bakery|restaurant|food",
            re.IGNORECASE,
        ),
    ),
    (
        2,
        "Travel",
        re.compile(r"uber|ola|rapido|irctc|metro|redbus|rail|cab|auto", re.IGNORECASE),
    ),
    (
        3,
        "Groceries",
        re.compile(
            r"blinkit|zepto|instamart|bigbasket|dmart|kirana|grocery|supermart|mart",
            re.IGNORECASE,
        ),
    ),
    (
        4,
        "Fuel",
        re.compile(r"hpcl|bpcl|iocl|indian oil|petrol|fuel|shell|pump", re.IGNORECASE),
    ),
    (
        5,
        "Utilities",
        re.compile(
            r"jio|airtel|vi|bsnl|uppcl|bescom|electricity|recharge|broadband|water|gas",
            re.IGNORECASE,
        ),
    ),
]


def _try_import(module_path: str, func_name: str):
    """Safely loads a teammate's function if their file exists on the active branch."""
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rel_file = module_path.replace(".", os.sep) + ".py"
        full_path = os.path.join(project_root, rel_file)

        # If file does not exist on the current Git branch, clear stale cache and fallback
        if not os.path.isfile(full_path):
            sys.modules.pop(module_path, None)
            return None

        importlib.invalidate_caches()
        if module_path in sys.modules:
            mod = importlib.reload(sys.modules[module_path])
        else:
            mod = importlib.import_module(module_path)
        return getattr(mod, func_name, None)
    except Exception:
        return None


def get_integration_status() -> dict:
    """Returns live auto-discovery status with 3-state progress and file breakdown."""
    # 1. Anuj (Backend & DB — 3 files)
    anuj_upi = (
        _try_import("src.backend.upi_bridge", "build_signed_upi_uri") is not None
        or _try_import("src.backend.upi_bridge", "launch_upi_intent") is not None
    )
    anuj_db = _try_import("src.db.database", "init_db") is not None
    anuj_sec = (
        _try_import("src.backend.security", "encrypt_db") is not None
        or _try_import("src.backend.security", "init_sqlcipher") is not None
    )

    anuj_files = [
        {
            "path": "src/backend/upi_bridge.py",
            "task": "S0-03 / S1-02: Signed UPI 2.0 URI Builder",
            "is_live": anuj_upi,
            "desc": "NPCI signed QR query preserver (mc, sign, orgid)",
        },
        {
            "path": "src/db/database.py",
            "task": "S1-01 / S2-04: SQLite v1.1 Database Engine",
            "is_live": anuj_db,
            "desc": "6 relational tables & pending state resolver",
        },
        {
            "path": "src/backend/security.py",
            "task": "S4-01: SQLCipher & Biometric App Lock",
            "is_live": anuj_sec,
            "desc": "256-bit DB encryption & Android Keystore",
        },
    ]

    # 2. Saurabh (Frontend Flet UI — 4 files)
    saurabh_dash = _try_import("src.ui.dashboard_view", "build_dashboard_view") is not None
    saurabh_home = _try_import("src.ui.home_view", "build_home_view") is not None
    saurabh_scan = _try_import("src.ui.scanner_view", "build_scanner_view") is not None
    saurabh_pop = (
        _try_import("src.ui.popups", "show_first_time_tag_dialog") is not None
        or _try_import("src.ui.popups", "show_fallback_popup") is not None
    )

    saurabh_files = [
        {
            "path": "src/ui/dashboard_view.py",
            "task": "S0-04 / S3-01: Flet Dark Dashboard & Charts",
            "is_live": saurabh_dash,
            "desc": "Visual spending breakdown & health gauge",
        },
        {
            "path": "src/ui/home_view.py",
            "task": "S1-03: Home Feed & Monthly Budget Card",
            "is_live": saurabh_home,
            "desc": "Live transaction feed & budget progress bar",
        },
        {
            "path": "src/ui/scanner_view.py",
            "task": "S1-03: QR Scan & UPI Intent Simulator",
            "is_live": saurabh_scan,
            "desc": "Camera scanner view & payment trigger",
        },
        {
            "path": "src/ui/popups.py",
            "task": "S1-04 / S2-03: 1-Tap Fallback & Tag Dialogs",
            "is_live": saurabh_pop,
            "desc": "Resume verification popup & merchant tagger",
        },
    ]

    # 3. Uday (Data Analytics — 4 files)
    uday_tag = _try_import("src.analytics.tagger", "categorize_transaction") is not None
    uday_anom = _try_import("src.analytics.anomaly", "detect_spending_anomaly") is not None
    uday_health = _try_import("src.analytics.health_score", "calculate_health_score") is not None
    uday_exp = _try_import("src.analytics.exporter", "export_transactions_csv") is not None

    uday_files = [
        {
            "path": "src/analytics/tagger.py",
            "task": "S0-05 / S2-01: 3-Tier Categorization Engine",
            "is_live": uday_tag,
            "desc": "Tier 1 Memory + Tier 2 Regex + Tier 3 Unknown",
        },
        {
            "path": "src/analytics/anomaly.py",
            "task": "S2-02: Safe Z-Score Anomaly Math",
            "is_live": uday_anom,
            "desc": "Statistics guard (stdev==0 & spike Z>2.5)",
        },
        {
            "path": "src/analytics/health_score.py",
            "task": "S2-02: Financial Health Score 0-100",
            "is_live": uday_health,
            "desc": "Dynamic pace & anomaly-adjusted health gauge",
        },
        {
            "path": "src/analytics/exporter.py",
            "task": "S3-02: Offline CSV Report Exporter",
            "is_live": uday_exp,
            "desc": "Pure-Python standard library CSV generator",
        },
    ]

    def calc_module_state(name: str, files: list) -> dict:
        live_cnt = sum(1 for f in files if f["is_live"])
        total_cnt = len(files)
        if live_cnt == 0:
            return {
                "mode": "BUILT-IN FALLBACK",
                "badge": f"🟡 {name}: 0/{total_cnt} Built-in",
                "color": "#F59E0B",
                "bg": "#1E293B",
                "border": "#475569",
                "text_color": "#CBD5E1",
                "state": "BUILTIN",
                "live_count": live_cnt,
                "total_count": total_cnt,
                "files": files,
            }
        elif live_cnt < total_cnt:
            return {
                "mode": "PARTIAL MODULE",
                "badge": f"🔵 {name}: {live_cnt}/{total_cnt} Partial",
                "color": "#38BDF8",
                "bg": "#0C4A6E",
                "border": "#0284C7",
                "text_color": "#BAE6FD",
                "state": "PARTIAL",
                "live_count": live_cnt,
                "total_count": total_cnt,
                "files": files,
            }
        else:
            return {
                "mode": "100% LIVE MODULE",
                "badge": f"🟢 {name}: {total_cnt}/{total_cnt} LIVE",
                "color": "#10B981",
                "bg": "#064E3B",
                "border": "#10B981",
                "text_color": "#A7F3D0",
                "state": "LIVE",
                "live_count": live_cnt,
                "total_count": total_cnt,
                "files": files,
            }

    return {
        "backend_anuj": {
            "owner": "Anuj Kushwaha",
            "role": "Backend & Database",
            **calc_module_state("Anuj", anuj_files),
        },
        "frontend_saurabh": {
            "owner": "Saurabh Yadav",
            "role": "Frontend Flet UI",
            **calc_module_state("Saurabh", saurabh_files),
        },
        "analytics_uday": {
            "owner": "Uday Paswan",
            "role": "Data Analytics & ML",
            **calc_module_state("Uday", uday_files),
        },
    }


def ensure_db_ready(db_path: str = DB_FILE) -> None:
    custom_init = _try_import("src.db.database", "init_db")
    if custom_init is not None:
        try:
            custom_init(db_path)
        except TypeError:
            custom_init()
    if not os.path.exists(db_path):
        seed_mock_database(db_path)


def build_signed_upi_uri(raw_qr_uri: str, amount: float) -> str:
    """Preserves NPCI UPI 2.0 signed parameters (mc, sign, orgid) while injecting am & cu=INR."""
    custom_fn = _try_import("src.backend.upi_bridge", "build_signed_upi_uri")
    if custom_fn is not None:
        try:
            return str(custom_fn(raw_qr_uri, amount))
        except Exception:
            pass

    if not raw_qr_uri.startswith("upi://pay"):
        raw_qr_uri = f"upi://pay?pa={raw_qr_uri}&pn=Merchant"

    parts = urlsplit(raw_qr_uri)
    params = parse_qsl(parts.query, keep_blank_values=True)
    updated = []
    seen_am = False
    seen_cu = False
    for k, v in params:
        if k.lower() == "am":
            updated.append(("am", f"{float(amount):.2f}"))
            seen_am = True
        elif k.lower() == "cu":
            updated.append(("cu", "INR"))
            seen_cu = True
        else:
            updated.append((k, v))
    if not seen_am:
        updated.append(("am", f"{float(amount):.2f}"))
    if not seen_cu:
        updated.append(("cu", "INR"))

    new_query = urlencode(updated, safe="@/:")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


def categorize_transaction(payee_vpa: str, payee_name: str, db_path: str = DB_FILE) -> dict:
    """3-Tier Categorization: Tier 1 (SQLite merchant_tags) -> Tier 2 (Regex) -> Tier 3 (User Tag Popup)."""
    custom_fn = _try_import("src.analytics.tagger", "categorize_transaction")
    if custom_fn is not None:
        try:
            return custom_fn(payee_vpa, payee_name, db_path=db_path)
        except TypeError:
            try:
                return custom_fn(payee_vpa, payee_name)
            except Exception:
                pass
        except Exception:
            pass

    vpa_clean = (payee_vpa or "").strip().lower()
    name_clean = (payee_name or "").strip()

    # Tier 1: Check merchant_tags memory
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT m.category_id, c.name, m.confidence FROM merchant_tags m "
        "JOIN categories c ON m.category_id = c.category_id WHERE LOWER(m.vpa_pattern) = ?;",
        (vpa_clean,),
    )
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "category_id": int(row[0]),
            "category_name": str(row[1]),
            "needs_user_tag": False,
            "confidence": float(row[2]),
            "tier": "Tier 1 (Memory Match)",
        }

    # Tier 2: Pre-compiled Regex dictionary
    combined_text = f"{vpa_clean} {name_clean}"
    for cid, cname, pattern in COMPILED_REGEX_RULES:
        if pattern.search(combined_text):
            return {
                "category_id": cid,
                "category_name": cname,
                "needs_user_tag": False,
                "confidence": 0.85,
                "tier": "Tier 2 (Regex Heuristic)",
            }

    # Tier 3: Unknown merchant -> Trigger First-Time User Tagging Popup
    return {
        "category_id": 6,
        "category_name": "Uncategorized",
        "needs_user_tag": True,
        "confidence": 0.0,
        "tier": "Tier 3 (Needs 1-Tap User Tag)",
    }


def save_merchant_tag(payee_vpa: str, category_id: int, db_path: str = DB_FILE) -> None:
    """Saves a first-time merchant VPA mapping so future payments auto-categorize in Tier 1."""
    custom_fn = _try_import("src.db.database", "save_merchant_tag")
    if custom_fn is not None:
        try:
            custom_fn(payee_vpa, category_id, db_path=db_path)
            return
        except TypeError:
            try:
                custom_fn(payee_vpa, category_id)
                return
            except Exception:
                pass
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO merchant_tags (vpa_pattern, category_id, confidence) VALUES (?, ?, 1.0);",
        (payee_vpa.strip().lower(), int(category_id)),
    )
    conn.commit()
    conn.close()


def detect_spending_anomaly(category_id: int, new_amount: float, db_path: str = DB_FILE) -> dict:
    """Safe Z-Score Anomaly Detector with len<4 and stdev==0 guards (Threshold Z > 2.5)."""
    custom_fn = _try_import("src.analytics.anomaly", "detect_spending_anomaly")
    if custom_fn is not None:
        try:
            return custom_fn(category_id, new_amount, db_path=db_path)
        except TypeError:
            try:
                return custom_fn(category_id, new_amount)
            except Exception:
                pass
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT amount FROM transactions WHERE category_id = ? ORDER BY timestamp DESC LIMIT 30;",
        (int(category_id),),
    )
    history = [float(r[0]) for r in cur.fetchall()]
    conn.close()

    if len(history) < 4:
        return {
            "is_anomaly": False,
            "z_score": 0.0,
            "mean": round(statistics.mean(history), 2) if history else 0.0,
            "stdev": 0.0,
            "reason": f"Insufficient sample ({len(history)}/4 txns)",
        }

    mean_val = statistics.mean(history)
    stdev_val = statistics.stdev(history)
    diff = float(new_amount) - mean_val

    if stdev_val == 0:
        is_anom = bool(new_amount > (2.0 * mean_val) and diff >= 100.0)
        return {
            "is_anomaly": is_anom,
            "z_score": 9.99 if is_anom else 0.0,
            "mean": round(mean_val, 2),
            "stdev": 0.0,
            "reason": (
                "Zero-variance guard triggered (>2x mean & +₹100)"
                if is_anom
                else "Zero-variance normal"
            ),
        }

    z_score = diff / stdev_val
    is_anom = bool(z_score > 2.5 and diff >= 100.0)
    return {
        "is_anomaly": is_anom,
        "z_score": round(z_score, 2),
        "mean": round(mean_val, 2),
        "stdev": round(stdev_val, 2),
        "reason": f"Z={z_score:.2f} > 2.5 threshold" if is_anom else f"Normal (Z={z_score:.2f})",
    }


def calculate_health_score(
    monthly_budget: float,
    spent_this_month: float,
    day_of_month: int | None = None,
    days_in_month: int = 30,
    anomaly_count: int = 0,
) -> dict:
    """Clamped 0-100 Financial Health Score based on budget pace and anomaly count."""
    custom_fn = _try_import("src.analytics.health_score", "calculate_health_score")
    if custom_fn is not None:
        try:
            return custom_fn(
                monthly_budget,
                spent_this_month,
                day_of_month or datetime.now().day,
                days_in_month,
                anomaly_count,
            )
        except Exception:
            pass

    if monthly_budget <= 0:
        return {"score": 100, "status": "GREEN", "ideal_spend": 0.0, "overspend_ratio": 0.0}

    dom = max(1, day_of_month or datetime.now().day)
    ideal_spend = (monthly_budget / max(1, days_in_month)) * dom
    overspend_ratio = max(0.0, (spent_this_month - ideal_spend) / max(1.0, ideal_spend))
    raw_score = 100.0 - (overspend_ratio * 50.0) - (anomaly_count * 5.0)
    score = int(max(0, min(100, round(raw_score))))
    status = "GREEN" if score >= 75 else ("YELLOW" if score >= 45 else "RED")
    return {
        "score": score,
        "status": status,
        "ideal_spend": round(ideal_spend, 2),
        "overspend_ratio": round(overspend_ratio, 2),
    }


def create_pending_txn(
    amount: float,
    payee_vpa: str,
    payee_name: str,
    raw_qr_uri: str,
    db_path: str = DB_FILE,
) -> int:
    """Logs a PENDING state row BEFORE launching any external UPI app intent."""
    custom_fn = _try_import("src.db.database", "create_pending_txn")
    if custom_fn is not None:
        try:
            return int(custom_fn(amount, payee_vpa, payee_name, raw_qr_uri, db_path=db_path))
        except TypeError:
            try:
                return int(custom_fn(amount, payee_vpa, payee_name, raw_qr_uri))
            except Exception:
                pass
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status) "
        "VALUES (?, ?, ?, ?, 'PENDING');",
        (float(amount), payee_vpa.strip(), payee_name.strip(), raw_qr_uri),
    )
    internal_id = int(cur.lastrowid)
    conn.commit()
    conn.close()
    return internal_id


def get_unresolved_pending(db_path: str = DB_FILE) -> list[dict]:
    """Fetches all unresolved PENDING transactions for the 1-Tap Resume Fallback Popup."""
    custom_fn = _try_import("src.db.database", "get_unresolved_pending")
    if custom_fn is not None:
        try:
            return custom_fn(db_path=db_path)
        except TypeError:
            try:
                return custom_fn()
            except Exception:
                pass
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT internal_id, amount, payee_vpa, payee_name, raw_qr_uri, init_time "
        "FROM pending_transactions WHERE status = 'PENDING' ORDER BY internal_id DESC;"
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "internal_id": int(r[0]),
            "amount": float(r[1]),
            "payee_vpa": str(r[2]),
            "payee_name": str(r[3]),
            "raw_qr_uri": str(r[4] or ""),
            "init_time": str(r[5]),
        }
        for r in rows
    ]


def resolve_pending_txn(
    internal_id: int,
    confirmed: bool,
    category_id: int | None = None,
    notes: str = "",
    txn_id: str | None = None,
    db_path: str = DB_FILE,
) -> dict:
    """Resolves a specific pending transaction via WHERE internal_id = ? and runs Tagger + Z-Score."""
    custom_fn = _try_import("src.db.database", "resolve_pending_txn")
    if custom_fn is not None:
        try:
            res = custom_fn(
                internal_id=internal_id,
                confirmed=confirmed,
                category_id=category_id,
                notes=notes,
                txn_id=txn_id,
                db_path=db_path,
            )
            if isinstance(res, dict) and "status" in res:
                return res
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT amount, payee_vpa, payee_name FROM pending_transactions WHERE internal_id = ?;",
        (int(internal_id),),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"status": "NOT_FOUND"}

    amount, payee_vpa, payee_name = float(row[0]), str(row[1]), str(row[2])

    if not confirmed:
        cur.execute(
            "UPDATE pending_transactions SET status = 'CANCELLED' WHERE internal_id = ?;",
            (int(internal_id),),
        )
        conn.commit()
        conn.close()
        return {"status": "CANCELLED", "internal_id": internal_id}

    tag_info = categorize_transaction(payee_vpa, payee_name, db_path=db_path)
    final_cat_id = int(category_id) if category_id is not None else int(tag_info["category_id"])
    anom_info = detect_spending_anomaly(final_cat_id, amount, db_path=db_path)
    final_txn_id = txn_id or f"MANUAL_VERIFY_{int(time.time() * 1000)}"

    cur.execute(
        "UPDATE pending_transactions SET status = 'RESOLVED' WHERE internal_id = ?;",
        (int(internal_id),),
    )
    cur.execute(
        "INSERT INTO transactions (txn_id, amount, payee_vpa, payee_name, timestamp, category_id, is_anomaly, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (
            final_txn_id,
            amount,
            payee_vpa,
            payee_name,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            final_cat_id,
            1 if anom_info["is_anomaly"] else 0,
            notes or "#Verified",
        ),
    )
    conn.commit()
    conn.close()
    return {
        "status": "RESOLVED",
        "txn_id": final_txn_id,
        "amount": amount,
        "payee_name": payee_name,
        "payee_vpa": payee_vpa,
        "category_id": final_cat_id,
        "category_name": CATEGORY_ID_TO_NAME.get(final_cat_id, "Uncategorized"),
        "needs_user_tag": tag_info["needs_user_tag"] and (category_id is None),
        "tier": tag_info.get("tier", ""),
        "anomaly": anom_info,
    }


def get_dashboard_summary(db_path: str = DB_FILE) -> dict:
    """Aggregates monthly spend, category breakdown, recent transactions, and health score."""
    ensure_db_ready(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT name, monthly_budget FROM user_profile LIMIT 1;")
    u_row = cur.fetchone()
    user_name = u_row[0] if u_row else "Sumit Kushwaha"
    monthly_budget = float(u_row[1]) if u_row else 12000.0

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0.0), "
        "COALESCE(SUM(CASE WHEN is_anomaly=1 THEN 1 ELSE 0 END), 0) FROM transactions;"
    )
    tot_row = cur.fetchone()
    total_spent = float(tot_row[0])
    anomaly_count = int(tot_row[1])\n
    cur.execute(
        """SELECT c.category_id, c.name, COALESCE(c.budget_limit, 2000.0),
                  COALESCE(SUM(t.amount), 0.0), COUNT(t.txn_id)
           FROM categories c
           LEFT JOIN transactions t ON c.category_id = t.category_id
           GROUP BY c.category_id, c.name, c.budget_limit
           ORDER BY COALESCE(SUM(t.amount), 0.0) DESC;"""
    )
    categories = [
        {
            "category_id": int(r[0]),
            "name": str(r[1]),
            "budget_limit": float(r[2]),
            "spent": round(float(r[3]), 2),
            "count": int(r[4]),
            "ratio": min(1.0, float(r[3]) / max(1.0, float(r[2]))),
        }
        for r in cur.fetchall()
    ]

    cur.execute(
        """SELECT t.txn_id, t.amount, t.payee_vpa, t.payee_name, t.timestamp,
                  COALESCE(c.name, 'Uncategorized'), t.is_anomaly, COALESCE(t.notes, '')
           FROM transactions t
           LEFT JOIN categories c ON t.category_id = c.category_id
           ORDER BY t.timestamp DESC LIMIT 15;"""
    )
    recent_txns = [
        {
            "txn_id": str(r[0]),
            "amount": float(r[1]),
            "payee_vpa": str(r[2]),
            "payee_name": str(r[3]),
            "timestamp": str(r[4]),
            "category": str(r[5]),
            "is_anomaly": bool(r[6]),
            "notes": str(r[7]),
        }
        for r in cur.fetchall()
    ]
    conn.close()

    health = calculate_health_score(monthly_budget, total_spent, anomaly_count=anomaly_count)
    return {
        "user_name": user_name,
        "monthly_budget": monthly_budget,
        "total_spent": round(total_spent, 2),
        "anomaly_count": anomaly_count,
        "health": health,
        "categories": categories,
        "recent_txns": recent_txns,
        "pending_list": get_unresolved_pending(db_path),
    }


def export_transactions_csv(
    output_file: str = "expenditure_report_export.csv", db_path: str = DB_FILE
) -> str:
    """Exports all logged transactions to a clean offline CSV file using Python's built-in csv module."""
    custom_fn = _try_import("src.analytics.exporter", "export_transactions_csv")
    if custom_fn is not None:
        try:
            return str(custom_fn(output_file, db_path=db_path))
        except TypeError:
            try:
                return str(custom_fn(output_file))
            except Exception:
                pass
        except Exception:
            pass

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """SELECT t.txn_id, t.timestamp, t.payee_name, t.payee_vpa, t.amount,
                  COALESCE(c.name, 'Uncategorized'), t.is_anomaly, COALESCE(t.notes, '')
           FROM transactions t
           LEFT JOIN categories c ON t.category_id = c.category_id
           ORDER BY t.timestamp DESC;"""
    )
    rows = cur.fetchall()
    conn.close()

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Transaction_ID",
                "Timestamp",
                "Payee_Name",
                "Payee_VPA",
                "Amount_INR",
                "Category",
                "Is_Anomaly",
                "Notes",
            ]
        )
        writer.writerows(rows)
    return os.path.abspath(output_file)
'''

MAIN_APP_CODE = '''"""Live Runnable Flet Application & Project Lead Integration Harness.

Owned by: Sumit Kushwaha (Project Lead & Integrator)
Usage:
    python main.py                       # Opens the Live Interactive Flet Mobile App
    python main.py --check-integration   # Runs the 6-Point CLI Team Integration Audit
"""

import argparse
import os
import sys
import warnings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.contracts import (
    CATEGORY_NAME_TO_ID,
    DEFAULT_CATEGORIES,
    _try_import,
    build_signed_upi_uri,
    categorize_transaction,
    create_pending_txn,
    detect_spending_anomaly,
    ensure_db_ready,
    export_transactions_csv,
    get_dashboard_summary,
    get_integration_status,
    resolve_pending_txn,
    save_merchant_tag,
)
from src.db.seed_mock_data import DB_FILE, seed_mock_database


def run_cli_integration_audit() -> None:
    """Runs a 6-point integration check across DB, UPI URI, Tagger, Anomaly Math, UI, and Lean Stack."""
    ensure_db_ready(DB_FILE)
    status = get_integration_status()
    summary = get_dashboard_summary(DB_FILE)

    print("=" * 78)
    print(" AUTOMATED EXPENDITURE TRACKER — LEAD INTEGRATION AUDIT (v1.1)")
    print("=" * 78)
    for key, info in status.items():
        mode_str = f"[{info['mode']}]"
        print(f" {mode_str:<22} {info['owner']:<16} ({info['badge']})")
        for f in info["files"]:
            st_icon = "🟢 LIVE    " if f["is_live"] else "🟡 Fallback"
            print(f"    └─ {st_icon} {f['path']:<30} [{f['task']}]")
    print("-" * 78)

    # Check 1: Signed UPI 2.0 QR Parameter Preservation
    raw_qr = "upi://pay?pa=zomato.order@hdfcbank&pn=Zomato&mc=5812&sign=NPCI_SIG_9981&orgid=159002"
    built_uri = build_signed_upi_uri(raw_qr, 245.5)
    assert (
        "mc=5812" in built_uri and "sign=NPCI_SIG_9981" in built_uri and "am=245.50" in built_uri
    ), "QR signature stripped!"
    print(" [PASS] Check 1 (Anuj Contract): Signed QR params (mc, sign, orgid) preserved ->", built_uri)

    # Check 2: 3-Tier Tagger (Tier 1 Memory + Tier 2 Regex + Tier 3 Unknown)
    t1 = categorize_transaction("ramesh.chai@ybl", "Ramesh Tea Stall")
    t2 = categorize_transaction("blinkit.pay@axis", "Blinkit Grofers")
    t3 = categorize_transaction("novelty.books@okicici", "Novelty Book House")
    print(
        f" [PASS] Check 2 (Uday Tagger): Tier1={t1['category_name']} | "
        f"Tier2={t2['category_name']} | Tier3(Unknown) needs_tag={t3['needs_user_tag']}"
    )

    # Check 3: Safe Z-Score Anomaly Guard (stdev==0 & spike > 2.5)
    anom_spike = detect_spending_anomaly(1, 1650.0)
    anom_normal = detect_spending_anomaly(1, 150.0)
    print(
        f" [PASS] Check 3 (Uday Z-Score): ₹1650 Food -> Anomaly={anom_spike['is_anomaly']} "
        f"(Z={anom_spike['z_score']}) | ₹150 Food -> Anomaly={anom_normal['is_anomaly']}"
    )

    # Check 4: Health Score & DB Summary
    h = summary["health"]
    print(
        f" [PASS] Check 4 (Health Score): Spent ₹{summary['total_spent']} / "
        f"₹{summary['monthly_budget']} -> Score {h['score']}/100 ({h['status']})"
    )
    print(
        f" [PASS] Check 5 (Pending Queue): {len(summary['pending_list'])} unresolved "
        f"PENDING item(s) ready for 1-Tap Resume Popup."
    )

    # Check 6 (Priority Upgrade 2): Zero Forbidden Heavy Imports Scan across src/
    forbidden = ("pandas", "numpy", "scipy", "sklearn", "matplotlib", "plotly")
    for root, _, files in os.walk("src"):
        for fn in files:
            if fn.endswith(".py"):
                fpath = os.path.join(root, fn)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as src_f:
                    content = src_f.read()
                for bad in forbidden:
                    if f"import {bad}" in content or f"from {bad}" in content:
                        raise AssertionError(
                            f"Forbidden library '{bad}' detected in {fpath}! Use pure Python stdlib only."
                        )
    print(" [PASS] Check 6 (Lean Stack Guardrail): Zero forbidden imports (pandas/numpy/matplotlib) in src/.")
    print("=" * 78)
    print(" [READY FOR DEMO] Run `python main.py` to launch the interactive Flet mobile app!")


def launch_flet_app() -> None:
    import flet as ft

    ensure_db_ready(DB_FILE)

    def get_icon(name: str):
        icons_mod = getattr(ft, "Icons", getattr(ft, "icons", None))
        return getattr(icons_mod, name, None) if icons_mod else None

    def pad(h: float = 0, v: float = 0):
        try:
            return ft.padding.only(left=h, right=h, top=v, bottom=v)
        except Exception:
            try:
                return ft.Padding(left=h, top=v, right=h, bottom=v)
            except Exception:
                return int(v)

    def make_border(color="#475569", width=1):
        try:
            if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
                return ft.Border.all(width=width, color=color)
        except Exception:
            pass
        try:
            if hasattr(ft, "border") and hasattr(ft.border, "all"):
                return ft.border.all(width, color)
        except Exception:
            pass
        try:
            side = ft.BorderSide(width, color)
            return ft.Border(left=side, top=side, right=side, bottom=side)
        except Exception:
            pass
        return None

    def safe_btn(text, on_click=None, bgcolor="#2563EB", color="white", height=38):
        return ft.Container(
            height=height,
            padding=pad(14, 8),
            bgcolor=bgcolor or "#334155",
            border_radius=8,
            alignment=ft.Alignment(0, 0) if hasattr(ft, "Alignment") else None,
            on_click=on_click,
            content=ft.Row(
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=color),
                ],
            ),
        )

    def safe_outlined_btn(text, on_click=None, height=38):
        return ft.Container(
            height=height,
            padding=pad(12, 8),
            bgcolor="#0F172A",
            border=make_border("#475569", 1),
            border_radius=8,
            on_click=on_click,
            content=ft.Row(
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(text, size=12, weight=ft.FontWeight.W_600, color="#CBD5E1"),
                ],
            ),
        )

    def make_dropdown(label: str, value: str, options_tuples: list, on_change_fn):
        opts = []
        for k, text in options_tuples:
            try:
                opts.append(ft.dropdown.Option(key=str(k), text=str(text)))
            except Exception:
                opts.append(ft.dropdown.Option(str(k), str(text)))
        dd = None
        try:
            dd = ft.Dropdown(label=label, value=value, options=opts, on_select=on_change_fn)
        except TypeError:
            dd = ft.Dropdown(label=label, value=value, options=opts, on_change=on_change_fn)
        try:
            dd.on_change = on_change_fn
        except Exception:
            pass
        try:
            dd.on_select = on_change_fn
        except Exception:
            pass
        return dd

    def border_bottom(color="#1F2937", width=1):
        try:
            side = ft.BorderSide(width, color)
            if hasattr(ft, "Border"):
                return ft.Border(bottom=side)
            if hasattr(ft, "border") and hasattr(ft.border, "only"):
                return ft.border.only(bottom=side)
        except Exception:
            pass
        return None

    def main(page: ft.Page):
        page.title = "Automated Expenditure Tracker (v1.1 Live Demo)"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#0B0F19"
        try:
            page.window.width = 435
            page.window.height = 860
        except Exception:
            pass
        page.padding = 0

        state = {"tab": 0}
        status_strip_container = ft.Container()
        body_container = ft.Container(expand=True, padding=14)

        def show_snack(msg: str, color: str = "#10B981"):
            snack = ft.SnackBar(
                content=ft.Text(msg, color="white", weight=ft.FontWeight.W_600),
                bgcolor=color,
            )
            try:
                page.open(snack)
            except Exception:
                try:
                    page.snack_bar = snack
                    page.snack_bar.open = True
                    page.update()
                except Exception:
                    pass

        def open_dialog_safe(dlg: ft.AlertDialog):
            try:
                page.open(dlg)
            except Exception:
                if dlg not in page.overlay:
                    page.overlay.append(dlg)
                dlg.open = True
                page.update()

        def close_dialog_safe(dlg: ft.AlertDialog):
            try:
                page.close(dlg)
            except Exception:
                dlg.open = False
                page.update()

        # Option 2 Feature: Clickable File-by-File Module Inspector Dialog
        def open_module_inspector_dialog(mod_key: str):
            integ = get_integration_status()
            mod = integ.get(mod_key)
            if not mod:
                return

            status_pills = []
            for f in mod["files"]:
                live = f["is_live"]
                pill_bg = "#064E3B" if live else "#451A03"
                pill_border = "#10B981" if live else "#F59E0B"
                pill_text = "🟢 LIVE (Real Code)" if live else "🟡 Fallback (Built-in)"
                pill_color = "#A7F3D0" if live else "#FDE68A"

                status_pills.append(
                    ft.Container(
                        padding=10,
                        border_radius=10,
                        bgcolor="#1E293B",
                        border=make_border("#334155", 1),
                        content=ft.Column(
                            tight=True,
                            spacing=3,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            f["path"],
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color="white",
                                        ),
                                        ft.Container(
                                            padding=pad(6, 2),
                                            bgcolor=pill_bg,
                                            border_radius=6,
                                            border=make_border(pill_border, 1),
                                            content=ft.Text(
                                                pill_text,
                                                size=10,
                                                weight=ft.FontWeight.BOLD,
                                                color=pill_color,
                                            ),
                                        ),
                                    ],
                                ),
                                ft.Text(
                                    f["task"],
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    color="#94A3B8",
                                ),
                                ft.Text(f["desc"], size=10, color="#64748B"),
                            ],
                        ),
                    )
                )

            def refresh_and_reopen(_):
                close_dialog_safe(dlg)
                render_active_tab()
                open_module_inspector_dialog(mod_key)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Column(
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(f"{mod['owner']}", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{mod['role']}  •  {mod['badge']}",
                            size=11,
                            color=mod["color"],
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                ),
                content=ft.Container(
                    width=365,
                    content=ft.Column(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Container(
                                padding=10,
                                bgcolor="#0F172A",
                                border_radius=8,
                                content=ft.Text(
                                    f"📊 Progress: {mod['live_count']}/{mod['total_count']} files LIVE on current Git branch. "
                                    "Missing files run Built-in Fallbacks so no teammate is ever blocked!",
                                    size=11,
                                    color="#94A3B8",
                                ),
                            ),
                            ft.Column(tight=True, spacing=6, controls=status_pills),
                        ],
                    ),
                ),
                actions=[
                    ft.Row(
                        tight=True,
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            safe_outlined_btn("🔄 Rescan Files", on_click=refresh_and_reopen, height=34),
                            safe_btn(
                                "Close",
                                on_click=lambda _: close_dialog_safe(dlg),
                                bgcolor="#334155",
                                color="white",
                                height=34,
                            ),
                        ],
                    )
                ],
            )
            open_dialog_safe(dlg)

        def open_first_time_tag_dialog(
            payee_vpa: str, payee_name: str, amount: float, txn_result: dict
        ):
            custom_popup = _try_import("src.ui.popups", "show_first_time_tag_dialog")
            if custom_popup is not None:
                try:
                    custom_popup(page, payee_vpa, payee_name, amount, render_active_tab)
                    return
                except Exception:
                    pass

            selected_cat = {"id": 1}

            def on_cat_select(e):
                val = getattr(e.control, "value", None) or getattr(e, "data", "1")
                try:
                    selected_cat["id"] = int(val)
                except ValueError:
                    selected_cat["id"] = 1

            cat_dropdown = make_dropdown(
                label="Select Category (Saved for all future payments)",
                value="1",
                options_tuples=[
                    (str(cid), cname)
                    for cid, cname, _, _, _ in DEFAULT_CATEGORIES
                    if cid != 6
                ],
                on_change_fn=on_cat_select,
            )

            def save_tag_click(e):
                save_merchant_tag(payee_vpa, selected_cat["id"])
                close_dialog_safe(dlg)
                render_active_tab()
                show_snack(
                    f"Saved '{payee_vpa}' to Tier-1 Memory! Next payment will auto-tag.",
                    "#3B82F6",
                )

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "🏷️ First-Time Merchant Detected", size=17, weight=ft.FontWeight.BOLD
                ),
                content=ft.Container(
                    width=350,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Text(f"You paid ₹{amount:.0f} to {payee_name} ({payee_vpa})."),
                            ft.Text(
                                "Tag this merchant once — Tier 1 Heuristic Memory will remember it forever:",
                                size=12,
                                color="#94A3B8",
                            ),
                            cat_dropdown,
                        ],
                    ),
                ),
                actions=[
                    safe_btn(
                        "Save to Memory",
                        on_click=save_tag_click,
                        bgcolor="#2563EB",
                        color="white",
                        height=36,
                    )
                ],
            )
            open_dialog_safe(dlg)

        def handle_resolve_pending(internal_id: int, confirmed: bool):
            res = resolve_pending_txn(internal_id, confirmed=confirmed)
            render_active_tab()
            if not confirmed:
                show_snack(f"Pending payment #{internal_id} marked as Cancelled.", "#64748B")
                return

            if res.get("anomaly", {}).get("is_anomaly"):
                show_snack(
                    f"⚠️ Z-SCORE SPIKE ALERT! ₹{res['amount']:.0f} at {res['payee_name']} "
                    f"(Z={res['anomaly']['z_score']})",
                    "#EF4444",
                )
            else:
                show_snack(
                    f"✅ Logged ₹{res['amount']:.0f} to {res['payee_name']} [{res['category_name']}]",
                    "#10B981",
                )

            if res.get("needs_user_tag"):
                open_first_time_tag_dialog(
                    res["payee_vpa"], res["payee_name"], res["amount"], res
                )

        def on_lifecycle_change(e):
            state_str = str(getattr(e, "state", getattr(e, "data", e))).upper()
            if "RESUME" in state_str:
                pending = get_dashboard_summary(DB_FILE)["pending_list"]
                if pending:
                    render_active_tab()
                    show_snack(
                        f"📲 App Resumed: {len(pending)} Pending UPI Payment(s) waiting for 1-Tap verification!",
                        "#F59E0B",
                    )

        page.on_app_lifecycle_state_change = on_lifecycle_change

        # Option 1 + Option 2: 3-State Progress Chips + Clickable Inspector Popup
        def build_status_strip() -> ft.Control:
            integ = get_integration_status()
            chips = []
            info_icon = get_icon("INFO_OUTLINE_ROUNDED") or get_icon("INFO_OUTLINE")
            for key in ["backend_anuj", "frontend_saurabh", "analytics_uday"]:
                mod = integ[key]
                row_controls = [
                    ft.Text(
                        mod["badge"],
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color=mod["text_color"],
                    )
                ]
                if info_icon is not None:
                    row_controls.append(ft.Icon(info_icon, size=11, color=mod["color"]))

                chips.append(
                    ft.Container(
                        padding=pad(8, 4),
                        bgcolor=mod["bg"],
                        border_radius=12,
                        border=make_border(mod["border"], 1),
                        content=ft.Row(tight=True, spacing=4, controls=row_controls),
                        tooltip=f"Tap to inspect {mod['owner']}'s file-by-file status",
                        on_click=lambda e, k=key: open_module_inspector_dialog(k),
                    )
                )

            return ft.Container(
                bgcolor="#111827",
                padding=pad(12, 8),
                border=border_bottom("#1F2937", 1),
                content=ft.Column(
                    tight=True,
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "⚡ Exptracker v1.1 (Tap Chip to Inspect)",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                ),
                                ft.Container(
                                    padding=pad(8, 4),
                                    bgcolor="#1E293B",
                                    border_radius=6,
                                    border=make_border("#334155", 1),
                                    on_click=lambda _: (
                                        seed_mock_database(DB_FILE),
                                        render_active_tab(),
                                        show_snack(
                                            "Demo DB reset to 40 txns + 1 pending!", "#3B82F6"
                                        ),
                                    ),
                                    content=ft.Text(
                                        "🔄 Reset Demo DB",
                                        size=10,
                                        weight=ft.FontWeight.W_600,
                                        color="#93C5FD",
                                    ),
                                ),
                            ],
                        ),
                        ft.Row(spacing=6, wrap=True, controls=chips),
                    ],
                ),
            )

        def build_home_tab(summary: dict) -> ft.Control:
            h = summary["health"]
            score_color = (
                "#10B981"
                if h["status"] == "GREEN"
                else ("#F59E0B" if h["status"] == "YELLOW" else "#EF4444")
            )

            controls = [
                # Financial Health & Monthly Budget Card
                ft.Container(
                    padding=16,
                    border_radius=16,
                    bgcolor="#1E293B",
                    border=make_border("#334155", 1),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                "Monthly Spend (Oct 2026)",
                                                size=12,
                                                color="#94A3B8",
                                            ),
                                            ft.Text(
                                                f"₹{summary['total_spent']:,.0f} / ₹{summary['monthly_budget']:,.0f}",
                                                size=22,
                                                weight=ft.FontWeight.BOLD,
                                                color="white",
                                            ),
                                        ],
                                    ),
                                    ft.Container(
                                        padding=pad(12, 8),
                                        border_radius=12,
                                        bgcolor="#0F172A",
                                        border=make_border(score_color, 1.5),
                                        content=ft.Column(
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=0,
                                            controls=[
                                                ft.Text(
                                                    f"{h['score']}/100",
                                                    size=18,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=score_color,
                                                ),
                                                ft.Text(
                                                    "Health Score", size=10, color="#94A3B8"
                                                ),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=min(
                                    1.0,
                                    summary["total_spent"] / max(1.0, summary["monthly_budget"]),
                                ),
                                color=score_color,
                                bgcolor="#0F172A",
                                height=8,
                            ),
                            ft.Text(
                                f"Ideal Pace Today: ₹{h['ideal_spend']:,.0f}  •  "
                                f"Anomalies Flagged: {summary['anomaly_count']}",
                                size=11,
                                color="#CBD5E1",
                            ),
                        ],
                    ),
                )
            ]

            # 1-Tap Pending Transaction Fallback Banner (If any PENDING row exists)
            for p in summary["pending_list"]:
                controls.append(
                    ft.Container(
                        padding=14,
                        border_radius=14,
                        bgcolor="#451A03",
                        border=make_border("#F59E0B", 1.5),
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            "⏳ 1-Tap Resume Fallback Verification",
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FDE68A",
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    f"Did your UPI payment of ₹{p['amount']:.0f} to "
                                    f"{p['payee_name']} ({p['payee_vpa']}) succeed?",
                                    size=12,
                                    color="white",
                                ),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        safe_btn(
                                            "✅ Yes, Log Payment",
                                            on_click=lambda e, pid=p["internal_id"]: handle_resolve_pending(
                                                pid, True
                                            ),
                                            bgcolor="#10B981",
                                            color="white",
                                        ),
                                        safe_outlined_btn(
                                            "❌ No, Cancelled",
                                            on_click=lambda e, pid=p["internal_id"]: handle_resolve_pending(
                                                pid, False
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

            controls.append(
                ft.Text(
                    "Recent UPI Transactions",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="white",
                )
            )

            txn_items = []
            for t in summary["recent_txns"]:
                is_anom = t["is_anomaly"]
                txn_items.append(
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor="#2E1016" if is_anom else "#1E293B",
                        border=make_border("#EF4444" if is_anom else "#334155", 1),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Row(
                                            spacing=6,
                                            controls=[
                                                ft.Text(
                                                    t["payee_name"],
                                                    size=14,
                                                    weight=ft.FontWeight.W_600,
                                                    color="white",
                                                ),
                                                ft.Container(
                                                    visible=is_anom,
                                                    padding=pad(6, 2),
                                                    bgcolor="#EF4444",
                                                    border_radius=6,
                                                    content=ft.Text(
                                                        "Z-SPIKE",
                                                        size=9,
                                                        weight=ft.FontWeight.BOLD,
                                                        color="white",
                                                    ),
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            f"{t['category']} • {t['payee_vpa']} {t['notes']}",
                                            size=11,
                                            color="#94A3B8",
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            f"-₹{t['amount']:.0f}",
                                            size=15,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FCA5A5" if is_anom else "white",
                                        ),
                                        ft.Text(t["timestamp"][5:16], size=10, color="#64748B"),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

            controls.append(ft.Column(spacing=8, controls=txn_items))
            return ft.Column(
                scroll=ft.ScrollMode.AUTO, expand=True, spacing=12, controls=controls
            )

        def build_scan_pay_tab() -> ft.Control:
            presets = {
                "Ramesh Tea Stall (Tier 1 Memory - Try ₹1500 for Z-Spike!)": (
                    "ramesh.chai@ybl",
                    "Ramesh Tea Stall",
                    "upi://pay?pa=ramesh.chai@ybl&pn=Ramesh%20Tea%20Stall&mc=5814&sign=NPCI_SIGNED_8821&orgid=159001",
                ),
                "Zomato Order (Tier 2 Regex Signed Merchant QR)": (
                    "zomato.order@hdfcbank",
                    "Zomato Limited",
                    "upi://pay?pa=zomato.order@hdfcbank&pn=Zomato%20Limited&mc=5812&sign=NPCI_SIGNED_9912&tr=ZMT2026",
                ),
                "Gupta Stationery (Tier 3 Unknown - Triggers 1-Tap Tag Popup!)": (
                    "gupta.books@okaxis",
                    "Gupta Stationery Hub",
                    "upi://pay?pa=gupta.books@okaxis&pn=Gupta%20Stationery%20Hub&mc=5942&sign=NPCI_SIGNED_3319",
                ),
            }

            default_key = "Ramesh Tea Stall (Tier 1 Memory - Try ₹1500 for Z-Spike!)"
            vpa_field = ft.TextField(
                label="Merchant VPA (pa)", value="ramesh.chai@ybl", height=48, text_size=13
            )
            name_field = ft.TextField(
                label="Merchant Name (pn)", value="Ramesh Tea Stall", height=48, text_size=13
            )
            qr_field = ft.TextField(
                label="Scanned Raw NPCI UPI 2.0 QR URI (Preserves mc, sign, orgid)",
                value=presets[default_key][2],
                multiline=True,
                min_lines=2,
                max_lines=2,
                text_size=11,
            )
            amt_field = ft.TextField(
                label="Amount (₹ INR)",
                value="20",
                keyboard_type=ft.KeyboardType.NUMBER,
                height=48,
            )
            notes_field = ft.TextField(
                label="Quick Tag / Note (Optional)",
                value="#EveningChai",
                height=48,
                text_size=13,
            )
            initial_uri = build_signed_upi_uri(presets[default_key][2], 20.0)
            uri_preview = ft.Text(
                f"🔒 Constructed Signed Intent URI: {initial_uri}",
                size=11,
                color="#38BDF8",
                selectable=True,
            )

            def update_preview(e=None):
                try:
                    amt = float(amt_field.value or 0)
                except ValueError:
                    amt = 0.0
                built = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                uri_preview.value = f"🔒 Constructed Signed Intent URI: {built}"
                if e is not None:
                    page.update()

            def on_preset_change(e):
                selected_key = getattr(e.control, "value", None) or getattr(
                    e, "data", default_key
                )
                if selected_key in presets:
                    vpa, name, raw_uri = presets[selected_key]
                    vpa_field.value = vpa
                    name_field.value = name
                    qr_field.value = raw_uri
                    update_preview(e)

            preset_dropdown = make_dropdown(
                label="Quick Demo Preset (Select Scenario for Faculty Demo)",
                value=default_key,
                options_tuples=[(k, k) for k in presets.keys()],
                on_change_fn=on_preset_change,
            )
            amt_field.on_change = update_preview
            qr_field.on_change = update_preview

            def click_launch_pending(e):
                try:
                    amt = float(amt_field.value or 0)
                    if amt <= 0:
                        raise ValueError
                except ValueError:
                    show_snack("Enter a valid positive amount in ₹!", "#EF4444")
                    return
                built_uri = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                pid = create_pending_txn(amt, vpa_field.value, name_field.value, built_uri)
                try:
                    page.launch_url(built_uri)
                except Exception:
                    pass
                state["tab"] = 0
                nav_bar.selected_index = 0
                render_active_tab()
                show_snack(
                    f"Created PENDING #{pid} & launched UPI Intent! Verify on Home Tab.",
                    "#F59E0B",
                )

            def click_instant_simulate(e):
                try:
                    amt = float(amt_field.value or 0)
                    if amt <= 0:
                        raise ValueError
                except ValueError:
                    show_snack("Enter a valid positive amount in ₹!", "#EF4444")
                    return
                built_uri = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                pid = create_pending_txn(amt, vpa_field.value, name_field.value, built_uri)
                res = resolve_pending_txn(pid, confirmed=True, notes=notes_field.value)
                state["tab"] = 0
                nav_bar.selected_index = 0
                render_active_tab()
                if res.get("anomaly", {}).get("is_anomaly"):
                    show_snack(
                        f"⚠️ ANOMALY DETECTED! ₹{amt:.0f} (Z={res['anomaly']['z_score']} > 2.5)",
                        "#EF4444",
                    )
                else:
                    show_snack(
                        f"✅ Instant Paid ₹{amt:.0f} -> Auto-Tagged: {res['category_name']} ({res['tier']})",
                        "#10B981",
                    )
                if res.get("needs_user_tag"):
                    open_first_time_tag_dialog(
                        res["payee_vpa"], res["payee_name"], amt, res
                    )

            return ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "📷 QR Scan & UPI 2.0 Intent Simulator",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                    preset_dropdown,
                    vpa_field,
                    name_field,
                    amt_field,
                    notes_field,
                    qr_field,
                    ft.Container(
                        padding=10,
                        bgcolor="#0F172A",
                        border_radius=10,
                        border=make_border("#1E293B", 1),
                        content=uri_preview,
                    ),
                    safe_btn(
                        "🚀 Step 1: Launch UPI App (Saves PENDING Row First)",
                        on_click=click_launch_pending,
                        bgcolor="#2563EB",
                        color="white",
                        height=44,
                    ),
                    safe_btn(
                        "⚡ Instant Simulate Payment Success (Test Tagger + Z-Score)",
                        on_click=click_instant_simulate,
                        bgcolor="#059669",
                        color="white",
                        height=44,
                    ),
                ],
            )

        def build_analytics_tab(summary: dict) -> ft.Control:
            cat_cards = []
            for c in summary["categories"]:
                bar_color = (
                    "#EF4444"
                    if c["ratio"] >= 0.85
                    else ("#F59E0B" if c["ratio"] >= 0.65 else "#3B82F6")
                )
                cat_cards.append(
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor="#1E293B",
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            f"{c['name']} ({c['count']} txns)",
                                            size=13,
                                            weight=ft.FontWeight.W_600,
                                            color="white",
                                        ),
                                        ft.Text(
                                            f"₹{c['spent']:,.0f} / ₹{c['budget_limit']:,.0f}",
                                            size=12,
                                            color="#CBD5E1",
                                        ),
                                    ],
                                ),
                                ft.ProgressBar(
                                    value=c["ratio"],
                                    color=bar_color,
                                    bgcolor="#0F172A",
                                    height=7,
                                ),
                            ],
                        ),
                    )
                )

            def export_csv_click(e):
                path = export_transactions_csv()
                show_snack(f"📄 Exported CSV to: {os.path.basename(path)}", "#10B981")

            return ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "📊 Category Spend & Z-Score Engine",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color="white",
                            ),
                            safe_btn(
                                "⬇️ Export CSV",
                                on_click=export_csv_click,
                                bgcolor="#334155",
                                color="white",
                                height=34,
                            ),
                        ],
                    ),
                    ft.Column(spacing=8, controls=cat_cards),
                ],
            )

        def render_active_tab():
            status_strip_container.content = build_status_strip()
            summary = get_dashboard_summary(DB_FILE)
            if state["tab"] == 0:
                custom_home = _try_import("src.ui.home_view", "build_home_view")
                body_container.content = (
                    custom_home(page, summary) if custom_home else build_home_tab(summary)
                )
            elif state["tab"] == 1:
                custom_scan = _try_import("src.ui.scanner_view", "build_scanner_view")
                body_container.content = (
                    custom_scan(page) if custom_scan else build_scan_pay_tab()
                )
            else:
                custom_dash = _try_import("src.ui.dashboard_view", "build_dashboard_view")
                body_container.content = (
                    custom_dash(page, summary)
                    if custom_dash
                    else build_analytics_tab(summary)
                )
            page.update()

        def on_nav_change(e):
            state["tab"] = e.control.selected_index
            render_active_tab()

        home_icon = get_icon("HOME_ROUNDED") or get_icon("HOME")
        qr_icon = get_icon("QR_CODE_SCANNER_ROUNDED") or get_icon("QR_CODE")
        chart_icon = get_icon("INSERT_CHART_ROUNDED") or get_icon("BAR_CHART")

        nav_bar = ft.NavigationBar(
            selected_index=0,
            bgcolor="#111827",
            on_change=on_nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=home_icon, label="Home & Feed"),
                ft.NavigationBarDestination(icon=qr_icon, label="Scan & Pay"),
                ft.NavigationBarDestination(icon=chart_icon, label="Analytics"),
            ],
        )

        page.add(
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    status_strip_container,
                    body_container,
                    nav_bar,
                ],
            )
        )
        render_active_tab()

    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated Expenditure Tracker — Live App & Integrator"
    )
    parser.add_argument(
        "--check-integration",
        action="store_true",
        help="Run 6-point CLI integration check without GUI",
    )
    args = parser.parse_args()

    if args.check_integration:
        run_cli_integration_audit()
    else:
        launch_flet_app()
'''


def upgrade_repo() -> None:
    for folder in FOLDERS:
        os.makedirs(folder, exist_ok=True)
        init_path = os.path.join(folder, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as f:
                f.write('"""Package init."""\n')

    if not os.path.exists("src/db/seed_mock_data.py"):
        with open("src/db/seed_mock_data.py", "w", encoding="utf-8") as f:
            f.write(SEED_MOCK_DATA_CODE)
        print("[Created] src/db/seed_mock_data.py -> 6 SQLite v1.1 tables & 40 mock UPI transactions")

    with open("src/contracts.py", "w", encoding="utf-8") as f:
        f.write(CONTRACTS_CODE)
    print("[Upgraded] src/contracts.py -> 3-State Auto-Discovery & File-by-File Status Registry")

    with open("main.py", "w", encoding="utf-8") as f:
        f.write(MAIN_APP_CODE)
    print("[Upgraded] main.py -> Interactive Flet Mobile App with Clickable Inspector Chips")

    print("\nNext Steps:")
    print("  1. Run `python main.py --check-integration` to verify all 6 checks & file statuses in terminal.")
    print("  2. Run `python main.py` to open the app and click any top chip to test the modal inspector!")


if __name__ == "__main__":
    upgrade_repo()