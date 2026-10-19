"""Uday Paswan — Pure-Python 3-Tier Smart Categorization Engine (Task S0-05)."""

import re
import sqlite3
from src.db.seed_mock_data import DB_FILE

# Pre-compiled Tier 2 Regex patterns (<1ms latency, zero heavy ML libraries)
COMPILED_REGEX_RULES = [
    (1, "Food & Dining", re.compile(r"zomato|swiggy|dominos|kfc|haldiram|bikaner|chai|tea|snack|canteen|cafe|bakery|restaurant|food", re.IGNORECASE)),
    (2, "Travel", re.compile(r"uber|ola|rapido|irctc|metro|redbus|rail|cab|auto", re.IGNORECASE)),
    (3, "Groceries", re.compile(r"blinkit|zepto|instamart|bigbasket|dmart|kirana|grocery|supermart|mart", re.IGNORECASE)),
    (4, "Fuel", re.compile(r"hpcl|bpcl|iocl|indian oil|petrol|fuel|shell|pump", re.IGNORECASE)),
    (5, "Utilities", re.compile(r"jio|airtel|vi|bsnl|uppcl|bescom|electricity|recharge|broadband|water|gas", re.IGNORECASE)),
]


def categorize_transaction(payee_vpa: str, payee_name: str, db_path: str = DB_FILE) -> dict:
    """3-Tier Categorization: Tier 1 (SQLite merchant_tags) -> Tier 2 (Regex) -> Tier 3 (User Tag Popup)."""
    vpa_clean = (payee_vpa or "").strip().lower()
    name_clean = (payee_name or "").strip()

    # Tier 1: Exact VPA lookup in SQLite merchant_tags
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT m.category_id, c.name, m.confidence FROM merchant_tags m JOIN categories c ON m.category_id = c.category_id WHERE LOWER(m.vpa_pattern) = ?;",
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
    except Exception:
        pass

    # Tier 2: Pre-compiled Regex dictionary match
    combined = f"{vpa_clean} {name_clean}"
    for cid, cname, pattern in COMPILED_REGEX_RULES:
        if pattern.search(combined):
            return {
                "category_id": cid,
                "category_name": cname,
                "needs_user_tag": False,
                "confidence": 0.85,
                "tier": "Tier 2 (Regex Heuristic)",
            }

    # Tier 3: Unrecognized merchant -> triggers 1-Tap User Tag Popup
    return {
        "category_id": 6,
        "category_name": "Uncategorized",
        "needs_user_tag": True,
        "confidence": 0.0,
        "tier": "Tier 3 (Needs 1-Tap User Tag)",
    }


if __name__ == "__main__":
    r1 = categorize_transaction("zomato.order@hdfcbank", "Zomato India")
    r2 = categorize_transaction("unknown.shop@okaxis", "Gupta Stationery")
    assert r1["category_name"] == "Food & Dining" and r2["needs_user_tag"] is True
    print("[PASS] Uday S0-05 3-Tier Tagger Unit Test Verified:", r1, r2)