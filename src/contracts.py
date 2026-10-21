"""
src/contracts.py
Smart Plug-and-Play Auto-Discovery Bridge & 3-State Module Registry (Task S0-02).
"""

import csv
import importlib
import os
import sqlite3
import urllib.parse
from datetime import datetime
from src.db.seed_mock_data import DB_FILE, seed_mock_database

def _try_import(module_path: str, func_name: str):
    """Dynamically imports func_name from module_path; returns None if not yet built."""
    try:
        return getattr(importlib.import_module(module_path), func_name, None)
    except Exception:
        return None

def ensure_db_ready(db_path: str = DB_FILE) -> None:
    if not os.path.exists(db_path):
        seed_mock_database(db_path)

# 1. UPI 2.0 Signed QR URI Builder (Anuj - src/backend/upi_bridge.py)
def build_signed_upi_uri(raw_qr_uri: str, amount: float) -> str:
    live_fn = _try_import("src.backend.upi_bridge", "build_signed_upi_uri")
    if live_fn:
        return live_fn(raw_qr_uri, amount)

    parsed = urllib.parse.urlsplit(raw_qr_uri if "://" in raw_qr_uri else f"upi://pay?pa={raw_qr_uri}")
    params = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if k not in ("am", "cu")]
    params.extend([("am", f"{float(amount):.2f}"), ("cu", "INR")])
    return urllib.parse.urlunsplit((parsed.scheme or "upi", parsed.netloc or "pay", parsed.path, urllib.parse.urlencode(params), parsed.fragment))

# 2. 3-Tier Categorization Engine (Uday - src/analytics/tagger.py)
KEYWORD_MAP = [
    (1, "Food & Dining", ("zomato", "swiggy", "tea", "chai", "food", "cafe", "restaurant")),
    (2, "Travel", ("metro", "dmrc", "uber", "ola", "rail", "irctc")),
    (3, "Groceries", ("mart", "smart", "grocery", "zepto", "blinkit")),
    (4, "Fuel", ("petrol", "fuel", "oil", "hpcl", "bpcl", "ioc")),
    (5, "Utilities", ("electric", "power", "tata", "broadband", "recharge")),
]

def categorize_transaction(payee_vpa: str, payee_name: str, db_path: str = DB_FILE) -> dict:
    live_fn = _try_import("src.analytics.tagger", "categorize_transaction")
    if live_fn:
        return live_fn(payee_vpa, payee_name, db_path=db_path)

    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT m.category_id, c.name FROM merchant_tags m JOIN categories c ON m.category_id = c.category_id WHERE m.vpa_pattern = ?",
            (payee_vpa.lower().strip(),),
        ).fetchone()
    if row:
        return {"category_id": row[0], "category_name": row[1], "needs_user_tag": False, "confidence": 1.0, "tier": "Tier 1 (SQLite Cache)"}

    low = f"{payee_vpa} {payee_name}".lower()
    for cid, cname, words in KEYWORD_MAP:
        if any(w in low for w in words):
            return {"category_id": cid, "category_name": cname, "needs_user_tag": False, "confidence": 0.85, "tier": "Tier 2 (Regex Heuristic)"}
    return {"category_id": 6, "category_name": "Uncategorized", "needs_user_tag": True, "confidence": 0.3, "tier": "Tier 3 (Needs User Tag)"}

def save_merchant_tag(payee_vpa: str, category_id: int, db_path: str = DB_FILE) -> bool:
    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR REPLACE INTO merchant_tags VALUES (?, ?, 1.0)", (payee_vpa.lower().strip(), category_id))
    return True

# 3. Safe Z-Score Anomaly Detector (Uday - src/analytics/anomaly.py)
def detect_spending_anomaly(category_id: int, new_amount: float, db_path: str = DB_FILE) -> dict:
    live_fn = _try_import("src.analytics.anomaly", "detect_spending_anomaly")
    if live_fn:
        return live_fn(category_id, new_amount, db_path=db_path)

    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        vals = [r[0] for r in conn.execute("SELECT amount FROM transactions WHERE category_id = ? ORDER BY timestamp DESC LIMIT 30", (category_id,)).fetchall()]
    if len(vals) < 4:
        return {"is_anomaly": False, "z_score": 0.0, "reason": "History < 4 txns"}

    mean = sum(vals) / len(vals)
    stdev = (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5
    if stdev == 0.0:
        spike = (new_amount > 2.0 * mean) and ((new_amount - mean) >= 100.0)
        return {"is_anomaly": spike, "z_score": 99.0 if spike else 0.0, "reason": "stdev==0 guard"}
    z = (new_amount - mean) / stdev
    return {"is_anomaly": z > 2.5, "z_score": round(z, 2), "reason": f"Z={z:.2f} (Avg Rs.{mean:.0f})"}

# 4. Clamped 0-100 Financial Health Score (Uday - src/analytics/health_score.py)
def calculate_health_score(monthly_budget: float, spent: float, day: int = None, total_days: int = 30, anomalies: int = 0) -> dict:
    live_fn = _try_import("src.analytics.health_score", "calculate_health_score")
    if live_fn:
        return live_fn(monthly_budget, spent, day=day, total_days=total_days, anomalies=anomalies)

    day = day or max(1, datetime.now().day)
    if monthly_budget <= 0:
        return {"score": 50, "status": "YELLOW", "color": "#F59E0B", "ideal_spend": 0.0}
    ideal = (monthly_budget / total_days) * day
    overspend = max(0.0, (spent - ideal) / max(1.0, ideal))
    score = max(0, min(100, round(100.0 - (overspend * 50.0) - (anomalies * 5.0))))
    status, color = ("GREEN", "#10B981") if score >= 75 else (("YELLOW", "#F59E0B") if score >= 45 else ("RED", "#EF4444"))
    return {"score": score, "status": status, "color": color, "ideal_spend": round(ideal, 2)}

# 5. Pending Transaction Lifecycle (Anuj - src/db/database.py)
def create_pending_txn(amount: float, payee_vpa: str, payee_name: str, raw_qr_uri: str, db_path: str = DB_FILE) -> int:
    live_fn = _try_import("src.db.database", "create_pending_txn")
    if live_fn:
        return live_fn(amount, payee_vpa, payee_name, raw_qr_uri, db_path=db_path)

    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status) VALUES (?, ?, ?, ?, 'PENDING')", (amount, payee_vpa, payee_name, raw_qr_uri))
        return cur.lastrowid

def get_unresolved_pending(db_path: str = DB_FILE) -> list:
    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute("SELECT * FROM pending_transactions WHERE status = 'PENDING' ORDER BY internal_id DESC").fetchall()]

def resolve_pending_txn(internal_id: int, status: str = "RESOLVED", txn_id: str = None, category_id: int = None, is_anomaly: bool = None, notes: str = "", db_path: str = DB_FILE) -> dict:
    live_fn = _try_import("src.db.database", "resolve_pending_txn")
    if live_fn:
        return live_fn(internal_id, status, txn_id=txn_id, category_id=category_id or 1, is_anomaly=bool(is_anomaly), notes=notes, db_path=db_path)

    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT amount, payee_vpa, payee_name FROM pending_transactions WHERE internal_id = ?", (internal_id,)).fetchone()
        if not row:
            return {"success": False, "error": f"internal_id {internal_id} not found"}
        conn.execute("UPDATE pending_transactions SET status = ? WHERE internal_id = ?", (status, internal_id))
        if status.upper() == "RESOLVED":
            tag = categorize_transaction(row[1], row[2], db_path)
            cid = category_id or tag["category_id"]
            anom = is_anomaly if is_anomaly is not None else detect_spending_anomaly(cid, row[0], db_path)["is_anomaly"]
            tid = txn_id or f"MANUAL_VERIFY_{int(datetime.now().timestamp()*1000)}"
            conn.execute(
                "INSERT OR REPLACE INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, row[0], row[1], row[2], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), cid, int(anom), notes or "1-Tap Verified"),
            )
    return {"success": True, "internal_id": internal_id, "status": status}

# 6. Dashboard Summary & Offline CSV Exporter
def get_dashboard_summary(db_path: str = DB_FILE) -> dict:
    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        budget = (conn.execute("SELECT monthly_budget FROM user_profile LIMIT 1").fetchone() or [12000.0])[0]
        spent, count = conn.execute("SELECT COALESCE(SUM(amount), 0.0), COUNT(*) FROM transactions").fetchone()
        anomalies = conn.execute("SELECT COUNT(*) FROM transactions WHERE is_anomaly = 1").fetchone()[0]
        cats = [{"id": r[0], "name": r[1], "spent": r[2], "limit": r[3], "icon": r[4]} for r in conn.execute(
            "SELECT c.category_id, c.name, COALESCE(SUM(t.amount), 0.0), c.budget_limit, c.icon_name FROM categories c LEFT JOIN transactions t ON c.category_id = t.category_id GROUP BY c.category_id ORDER BY 3 DESC"
        ).fetchall()]
        recent = [{"id": r[0], "amount": r[1], "vpa": r[2], "name": r[3], "date": r[4], "category": r[5], "anomaly": bool(r[6])} for r in conn.execute(
            "SELECT t.txn_id, t.amount, t.payee_vpa, t.payee_name, t.timestamp, c.name, t.is_anomaly FROM transactions t LEFT JOIN categories c ON t.category_id = c.category_id ORDER BY t.timestamp DESC LIMIT 10"
        ).fetchall()]
        pend_count = conn.execute("SELECT COUNT(*) FROM pending_transactions WHERE status = 'PENDING'").fetchone()[0]
        splits_count = conn.execute("SELECT COUNT(*) FROM bill_splits").fetchone()[0]

    health = calculate_health_score(budget, spent, anomalies=anomalies)
    days_left = max(1, 30 - datetime.now().day + 1)
    rem = max(0.0, budget - spent)
    return {
        "monthly_budget": budget, "spent_this_month": round(spent, 2), "remaining_budget": round(rem, 2),
        "daily_safe_spend": round(rem / days_left, 0), "ideal_spend": health["ideal_spend"],
        "transaction_count": count, "anomaly_count": anomalies, "health_score": health["score"],
        "health_status": health["status"], "health_color": health["color"],
        "category_breakdown": cats, "recent_transactions": recent, "pending_count": pend_count, "splits_count": splits_count,
    }

def export_transactions_csv(output_file: str = "transactions_export.csv", db_path: str = DB_FILE) -> str:
    live_fn = _try_import("src.analytics.exporter", "export_transactions_csv")
    if live_fn:
        return live_fn(output_file, db_path=db_path)

    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT txn_id, timestamp, amount, payee_vpa, payee_name, category_id, is_anomaly, notes FROM transactions ORDER BY timestamp DESC").fetchall()
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["txn_id", "timestamp", "amount", "payee_vpa", "payee_name", "category_id", "is_anomaly", "notes"])
        writer.writerows(rows)
    return os.path.abspath(output_file)

# 7. Detailed 3-State Module Registry (Powers Top Progress Chips & File-by-File Popup)
TEAM_MODULES_SPEC = {
    "anuj": {
        "member": "Anuj Kushwaha", "short": "Anuj DB/UPI", "role": "Backend & Android UPI Bridge",
        "files": [
            ("src/backend/upi_bridge.py", "S0-03 / S1-02", "src.backend.upi_bridge", "build_signed_upi_uri", "Preserves signed QR params (mc, sign, orgid)"),
            ("src/db/database.py", "S1-01 / S2-04", "src.db.database", "create_pending_txn", "6-table SQLite v1.1 CRUD & WHERE internal_id=?"),
            ("src/backend/security.py", "S4-01", "src.backend.security", "get_encrypted_connection", "SQLCipher 256-bit & Biometric lock"),
        ],
    },
    "saurabh": {
        "member": "Saurabh Yadav", "short": "Saurabh UI", "role": "Frontend Python Flet UI",
        "files": [
            ("src/ui/dashboard_view.py", "S0-04 / S3-01", "src.ui.dashboard_view", "build_dashboard_view", "Category spend cards & Flet charts"),
            ("src/ui/home_view.py", "S1-03", "src.ui.home_view", "build_home_view", "Wallet card, 1-Tap banner & passbook feed"),
            ("src/ui/scanner_view.py", "S1-03", "src.ui.scanner_view", "build_scanner_view", "QR viewfinder & UPI intent launcher"),
            ("src/ui/popups.py", "S1-04 / S2-03", "src.ui.popups", "show_resume_verification_popup", "Resume verification, Tag & Bill Split modals"),
        ],
    },
    "uday": {
        "member": "Uday Paswan", "short": "Uday Analytics", "role": "Data Analytics (Pure Python)",
        "files": [
            ("src/analytics/tagger.py", "S0-05 / S2-01", "src.analytics.tagger", "categorize_transaction", "3-Tier Categorization (SQLite -> Regex -> Tag)"),
            ("src/analytics/anomaly.py", "S2-02", "src.analytics.anomaly", "detect_spending_anomaly", "Crash-proof Z-Score (stdev==0 guard, Z>2.5)"),
            ("src/analytics/health_score.py", "S2-02 / S3-02", "src.analytics.health_score", "calculate_health_score", "Clamped 0-100 Score & Mid-Month Pace alert"),
            ("src/analytics/exporter.py", "S3-02", "src.analytics.exporter", "export_transactions_csv", "Offline pure-Python CSV ledger export"),
        ],
    },
}

def get_detailed_module_registry() -> dict:
    """Returns 3-state progress (Built-in 0/N -> Partial k/N -> LIVE N/N) and file-by-file status."""
    registry = {}
    for key, spec in TEAM_MODULES_SPEC.items():
        file_rows = []
        live_count = 0
        for rel_path, task_id, mod_path, fn_name, desc in spec["files"]:
            is_live = _try_import(mod_path, fn_name) is not None
            if is_live:
                live_count += 1
            file_rows.append({
                "path": rel_path, "task": task_id, "func": f"{fn_name}()",
                "desc": desc, "is_live": is_live,
                "status_label": "🟢 LIVE MODULE" if is_live else "🟡 Built-in Fallback",
            })
        total = len(file_rows)
        if live_count == 0:
            state, icon, color, label = "BUILTIN", "🟡", "#F59E0B", f"🟡 {spec['short']}: Built-in (0/{total})"
        elif live_count < total:
            state, icon, color, label = "PARTIAL", "🔵", "#38BDF8", f"🔵 {spec['short']}: Partial ({live_count}/{total})"
        else:
            state, icon, color, label = "LIVE", "🟢", "#10B981", f"🟢 {spec['short']}: LIVE ({live_count}/{total})"
        registry[key] = {
            "member": spec["member"], "short": spec["short"], "role": spec["role"],
            "live_count": live_count, "total_count": total, "state": state,
            "icon": icon, "color": color, "chip_label": label, "files": file_rows,
        }
    return registry

def get_integration_status() -> dict:
    reg = get_detailed_module_registry()
    return {
        f"{v['member']} ({v['short']})": f"[{v['state']} {v['live_count']}/{v['total_count']}]"
        for v in reg.values()
    }

if __name__ == "__main__":
    ensure_db_ready()
    uri = build_signed_upi_uri("upi://pay?pa=shop@upi&pn=Shop&mc=5411&sign=XYZ&orgid=11", 250.0)
    assert "sign=XYZ" in uri and "am=250.00" in uri
    assert categorize_transaction("zomato@icici", "Zomato")["category_name"] == "Food & Dining"
    assert 0 <= calculate_health_score(12000.0, 6000.0, day=15)["score"] <= 100
    assert len(get_detailed_module_registry()) == 3
    print("[PASS] src.contracts: Smart auto-discovery bridge & 3-state registry verified.")