"""Uday Paswan — Pure-Python SQLite Aggregation Queries & Financial Health Score Engine (Task S1-05)."""

import os
import sqlite3
from datetime import datetime
from src.db.seed_mock_data import DB_FILE, seed_mock_database


def _ensure_seeded_db(db_path: str = DB_FILE) -> None:
    """Ensures tracker_dev.db exists and has seeded v1.1 tables before running aggregation queries."""
    if not db_path:
        return
    if not os.path.exists(db_path):
        seed_mock_database(db_path)
        return
    try:
        with sqlite3.connect(db_path) as conn:
            cat_count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
            if cat_count == 0:
                seed_mock_database(db_path)
    except sqlite3.OperationalError:
        seed_mock_database(db_path, force_reset=True)


def calculate_health_score(
    monthly_budget: float,
    spent: float,
    day: int = None,
    total_days: int = 30,
    anomalies: int = 0,
) -> dict:
    """Computes a clamped 0-100 Financial Health Score based on budget pacing and Z-Score anomalies."""
    day = int(day if day is not None else max(1, datetime.now().day))
    total_days = max(1, int(total_days or 30))
    budget_val = float(monthly_budget or 0.0)
    spent_val = max(0.0, float(spent or 0.0))
    anomaly_count = max(0, int(anomalies or 0))

    if budget_val <= 0.0:
        return {
            "score": 50,
            "status": "YELLOW",
            "color": "#F59E0B",
            "ideal_spend": 0.0,
        }

    ideal = (budget_val / total_days) * day
    overspend_ratio = max(0.0, (spent_val - ideal) / max(1.0, ideal))
    raw_score = 100.0 - (overspend_ratio * 50.0) - (anomaly_count * 5.0)
    score = int(max(0, min(100, round(raw_score))))

    if score >= 75:
        status, color = "GREEN", "#10B981"
    elif score >= 45:
        status, color = "YELLOW", "#F59E0B"
    else:
        status, color = "RED", "#EF4444"

    return {
        "score": score,
        "status": status,
        "color": color,
        "ideal_spend": round(ideal, 2),
    }


def get_monthly_spend_summary(db_path: str = DB_FILE) -> dict:
    """Queries user_profile and transactions for current month total spend, counts, and budget."""
    _ensure_seeded_db(db_path)
    with sqlite3.connect(db_path) as conn:
        prof_row = conn.execute("SELECT monthly_budget FROM user_profile LIMIT 1").fetchone()
        monthly_budget = float(prof_row[0]) if prof_row and prof_row[0] is not None else 12000.0

        tx_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0.0), COUNT(*) FROM transactions"
        ).fetchone()
        spent_this_month = round(float(tx_row[0] or 0.0), 2)
        transaction_count = int(tx_row[1] or 0)

        anomaly_count = int(
            conn.execute("SELECT COUNT(*) FROM transactions WHERE is_anomaly = 1").fetchone()[0]
        )
        pending_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM pending_transactions WHERE status = 'PENDING'"
            ).fetchone()[0]
        )
        splits_count = int(conn.execute("SELECT COUNT(*) FROM bill_splits").fetchone()[0])

    return {
        "monthly_budget": monthly_budget,
        "spent_this_month": spent_this_month,
        "total_spent": spent_this_month,
        "transaction_count": transaction_count,
        "anomaly_count": anomaly_count,
        "pending_count": pending_count,
        "splits_count": splits_count,
    }


def get_category_wise_totals(db_path: str = DB_FILE) -> list:
    """Aggregates category-wise spend and transaction counts via LEFT JOIN without pandas."""
    _ensure_seeded_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT c.category_id, c.name, COALESCE(SUM(t.amount), 0.0) AS total_spent, "
            "c.budget_limit, c.icon_name, COUNT(t.txn_id) AS txn_count "
            "FROM categories c "
            "LEFT JOIN transactions t ON c.category_id = t.category_id "
            "GROUP BY c.category_id "
            "ORDER BY total_spent DESC, c.category_id ASC"
        ).fetchall()

    categories = []
    for r in rows:
        safe_limit = float(r[3]) if r[3] and float(r[3]) > 0.0 else 1.0
        categories.append(
            {
                "id": int(r[0]),
                "name": str(r[1]),
                "spent": round(float(r[2] or 0.0), 2),
                "limit": safe_limit,
                "budget_limit": safe_limit,
                "icon": str(r[4] or "help_outline"),
                "count": int(r[5] or 0),
            }
        )
    return categories


def get_recent_10_transactions(limit: int = 10, db_path: str = DB_FILE) -> list:
    """Fetches the most recent 10 transactions joined with category names."""
    _ensure_seeded_db(db_path)
    safe_limit = max(1, int(limit or 10))
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT t.txn_id, t.amount, t.payee_vpa, t.payee_name, t.timestamp, "
            "COALESCE(c.name, 'Uncategorized'), t.is_anomaly "
            "FROM transactions t "
            "LEFT JOIN categories c ON t.category_id = c.category_id "
            "ORDER BY t.timestamp DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()

    return [
        {
            "id": str(r[0]),
            "amount": round(float(r[1] or 0.0), 2),
            "vpa": str(r[2]),
            "name": str(r[3]),
            "date": str(r[4]),
            "category": str(r[5]),
            "anomaly": bool(r[6]),
        }
        for r in rows
    ]


def get_dashboard_summary(db_path: str = DB_FILE) -> dict:
    """Combines monthly aggregates, category totals, recent 10 txns, and Health Score for UI views."""
    totals = get_monthly_spend_summary(db_path)
    cats = get_category_wise_totals(db_path)
    recent = get_recent_10_transactions(limit=10, db_path=db_path)

    budget = totals["monthly_budget"]
    spent = totals["spent_this_month"]
    anomalies = totals["anomaly_count"]

    health = calculate_health_score(budget, spent, anomalies=anomalies)
    days_left = max(1, 30 - datetime.now().day + 1)
    remaining = max(0.0, round(budget - spent, 2))
    daily_safe = round(remaining / days_left, 0)

    return {
        "monthly_budget": budget,
        "spent_this_month": spent,
        "total_spent": spent,
        "remaining_budget": remaining,
        "daily_safe_spend": daily_safe,
        "ideal_spend": health["ideal_spend"],
        "transaction_count": totals["transaction_count"],
        "anomaly_count": anomalies,
        "health_score": health["score"],
        "health_status": health["status"],
        "health_color": health["color"],
        "category_breakdown": cats,
        "recent_transactions": recent,
        "pending_count": totals["pending_count"],
        "splits_count": totals["splits_count"],
    }


if __name__ == "__main__":
    seed_mock_database(DB_FILE)

    # 1. Verify Health Score math & zero-budget guardrail
    h_normal = calculate_health_score(12000.0, 6000.0, day=15, total_days=30, anomalies=1)
    assert isinstance(h_normal, dict) and 0 <= h_normal["score"] <= 100
    assert h_normal["ideal_spend"] == 6000.0 and h_normal["status"] in ("GREEN", "YELLOW", "RED")

    h_zero_budget = calculate_health_score(0.0, 500.0, day=10)
    assert h_zero_budget["score"] == 50 and h_zero_budget["status"] == "YELLOW"

    # 2. Verify Category-Wise SQLite Aggregation (6 categories with non-zero budget limits)
    cat_list = get_category_wise_totals(DB_FILE)
    assert isinstance(cat_list, list) and len(cat_list) == 6
    assert all(c["limit"] > 1.0 and "spent" in c and "count" in c for c in cat_list)

    # 3. Verify Recent 10 Transactions SQLite Query
    recent_10 = get_recent_10_transactions(limit=10, db_path=DB_FILE)
    assert isinstance(recent_10, list) and len(recent_10) == 10
    assert all("id" in t and "amount" in t and "category" in t for t in recent_10)

    # 4. Verify Complete Dashboard Summary Contract & Non-Zero Real DB Values
    summary = get_dashboard_summary(DB_FILE)
    assert isinstance(summary, dict)
    assert summary["monthly_budget"] > 0.0 and summary["spent_this_month"] > 0.0
    assert summary["transaction_count"] >= 40 and 0 <= summary["health_score"] <= 100
    print(
        "[PASS] Uday S1-05 SQLite Aggregations & Health Score Verified:",
        {
            "spent_this_month": summary["spent_this_month"],
            "monthly_budget": summary["monthly_budget"],
            "health_score": summary["health_score"],
            "health_status": summary["health_status"],
            "categories": len(cat_list),
            "recent_txns": len(recent_10),
        },
    )