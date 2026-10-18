"""Main Entrypoint & Cross-Module Integrator.

Owned by: Sumit Kushwaha (Project Lead)
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.db.seed_mock_data import DB_FILE, seed_mock_database


def verify_environment() -> None:
    if not os.path.exists(DB_FILE):
        seed_mock_database(DB_FILE)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions;")
    txn_count = cur.fetchone()[0]
    cur.execute("SELECT internal_id, amount, payee_name FROM pending_transactions WHERE status='PENDING';")
    pending = cur.fetchall()
    conn.close()
    print(f"[Smoke Test PASS] Database ready: {txn_count} logged transactions, {len(pending)} pending fallback item(s).")


if __name__ == "__main__":
    verify_environment()
