"""Smart Plug-and-Play Cross-Module Contract Bridge (v1.1).

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
    anomaly_count = int(tot_row[1])

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
