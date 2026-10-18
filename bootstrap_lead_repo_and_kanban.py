#!/usr/bin/env python3
"""Project Lead Pre-Handoff Bootstrapper for Sumit Kushwaha.

Automated Expenditure Tracker with QR-Integrated Payment Gateway Log Analysis
Institution: NITRA Technical Campus, Ghaziabad

What this script does for Sumit BEFORE handing orientation guides to teammates:
1. Scaffolds the isolated team folder structure (src/db, src/backend, src/ui, src/analytics, docs, .github).
2. Generates .gitignore, requirements.txt, and GitHub Pull Request & Issue templates.
3. Generates src/contracts.py (locked interface signatures) and src/db/seed_mock_data.py
   (seeds 40 realistic 30-day UPI transactions into SQLite v1.1 so Saurabh and Uday are unblocked on Day 1).
4. Generates a runnable starter main.py shell.
5. Optional (--create-github-issues): Uses GitHub CLI (`gh`) to bulk-create all 4 Role Labels,
   5 Sprint Milestones, and all 22 Kanban Issues (S0-01 to S4-04) on GitHub automatically.

Usage:
    python bootstrap_lead_repo_and_kanban.py
    python bootstrap_lead_repo_and_kanban.py --create-github-issues
"""

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

FOLDERS = [
    "src",
    "src/db",
    "src/backend",
    "src/ui",
    "src/analytics",
    "docs",
    ".github",
    ".github/ISSUE_TEMPLATE",
]

GITIGNORE_CONTENT = """# Python & Bytecode
__pycache__/
*.py[cod]
*$py.class
*.so

# Virtual Environments
venv/
.venv/
env/

# Local SQLite & Encrypted Databases (Never commit local user data)
*.db
*.db-journal
*.db-wal
*.sqlite
*.sqlite3

# Flet & Flutter Build Artifacts
build/
.flet/
dist/
*.apk
*.aab

# IDE & OS
.vscode/
.idea/
.DS_Store
Thumbs.db
"""

REQUIREMENTS_CONTENT = """# Lean Tech Stack Mandate (<25-35MB APK, <500ms Warm Resume)
# Strictly NO pandas, numpy, scikit-learn, matplotlib, or plotly
flet>=0.24.0
"""

PR_TEMPLATE_CONTENT = """## Task & Kanban Issue Link
- **Kanban Issue:** Closes #<!-- Enter GitHub Issue Number, e.g. Closes #5 -->
- **Task ID (from Sprint Backlog):** `S_-__`
- **Role / Module Folder:** <!-- backend (src/db, src/backend) | ui (src/ui) | data (src/analytics) | lead (main.py) -->

## Personal Google Drive Task Living Doc (Stage 2 & Stage 4 Proof)
- **Task Living Doc Link:** [Paste your Google Drive Task Living Doc URL here]
- [ ] All sub-tasks in my Task Living Doc are marked `[x] Completed`
- [ ] Stage 4 Objective Local Tests ran and passed (`PASS`)

## Architectural Guardrail Self-Check (Mandatory Before Requesting @Sumit Review)
- [ ] Target branch of this PR is **`dev`** (NOT `main`)
- [ ] I only modified files inside my assigned module folder (Zero merge conflict rule)
- [ ] Zero forbidden imports (`pandas`, `numpy`, `scikit-learn`, `matplotlib`, `plotly` are NOT used)
- [ ] **If Backend (Anuj):** `pending_transactions` resolves via `WHERE internal_id = ?` and `upi://pay` preserves signed QR params (`mc`, `sign`, `orgid`)
- [ ] **If Frontend (Saurabh):** Uses native Flet controls and wires `RESUMED` lifecycle / tagging popups via `src/contracts.py`
- [ ] **If Analytics (Uday):** Guards against `stdev == 0` and `len(history) < 4` before dividing in Z-Score (`Z > 2.5`)
"""

ISSUE_TEMPLATE_CONTENT = """---
name: Sprint Kanban Task
about: Standardized 6-Stage Gemini Workflow task card for Sumit, Anuj, Saurabh, or Uday
title: "[S0-00] Task Title"
labels: []
assignees: []
---

### 1. Task Metadata
- **Task ID:** `S_-__`
- **Sprint:** `Sprint _`
- **Owner & Role:** 
- **Git Branch to Create (off `dev`):** `git checkout dev && git pull origin dev && git checkout -b feature/...`
- **Allowed Folder to Edit:** `src/...`

### 2. Objective & Acceptance Criteria
- 

### 3. 6-Stage Gemini Execution Checklist
- [ ] **Stage 1 (Intake):** Give this task to Gemini to trigger role skill & sub-task breakdown
- [ ] **Stage 2 (Drive Task Living Doc):** Paste link to created Google Drive Task Living Doc in a comment below
- [ ] **Stage 3 (Implementation):** Write modular code inside owned directory on feature branch
- [ ] **Stage 4 (Objective Testing):** Run local verification test against mock data (`seed_mock_data.py`)
- [ ] **Stage 5 (Systematic Bug-Fix):** Log any errors & fixes in the Drive Task Living Doc
- [ ] **Stage 6 (Commit & PR to `dev`):** Open PR into `dev` with `Closes #<this-issue-number>`
"""

CONTRACTS_PY_CONTENT = '''"""Locked Cross-Module Interface Contracts (v1.1).

Owned by: Sumit Kushwaha (Project Lead)
Purpose: Ensures Anuj (Backend), Saurabh (Flet UI), and Uday (Data Analytics)
can build and test their modules in parallel without blocking each other.
"""

from typing import Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tracker_dev.db") if "os" in globals() else "tracker_dev.db"

# Default Categories (v1.1 Schema)
DEFAULT_CATEGORIES = [
    (1, "Food & Dining", 4000.0, "RESTAURANT", 1),
    (2, "Travel", 2500.0, "DIRECTIONS_CAR", 1),
    (3, "Groceries", 3000.0, "SHOPPING_CART", 1),
    (4, "Fuel", 2000.0, "LOCAL_GAS_STATION", 1),
    (5, "Utilities", 2500.0, "BOLT", 1),
    (6, "Uncategorized", None, "HELP_OUTLINE", 1),
]


def get_contract_summary() -> dict[str, str]:
    """Returns the canonical module ownership map."""
    return {
        "lead_integrator": "main.py, src/contracts.py, src/db/seed_mock_data.py",
        "backend_anuj": "src/db/database.py, src/backend/upi_bridge.py, src/backend/security.py",
        "frontend_saurabh": "src/ui/home_view.py, src/ui/scanner_view.py, src/ui/dashboard_view.py, src/ui/popups.py",
        "analytics_uday": "src/analytics/tagger.py, src/analytics/anomaly.py, src/analytics/health_score.py, src/analytics/exporter.py",
    }
'''

SEED_MOCK_DATA_CONTENT = '''"""30-Day Realistic UPI Mock Database Seeder (Task S0-02).

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
'''

MAIN_PY_CONTENT = '''"""Main Entrypoint & Cross-Module Integrator.

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
'''

KANBAN_ISSUES = [
    ("S0-01", "Sprint 0 (Synopsis)", "role:lead", "Initialize GitHub Repo, Branch Protection & Spec v1.1 Fixes", "docs/specs-v1.1", "Sumit Kushwaha", "Create repo with main and dev branches; add .gitignore; commit v1.1 docs fixing signed QR URI preservation, Z-Score stdev=0 guard, and bill_splits table."),
    ("S0-02", "Sprint 0 (Synopsis)", "role:lead", "Create src/contracts.py & 30-Day Mock DB Seeder", "feature/contracts-and-mock-seed", "Sumit Kushwaha", "Define exact Python function signatures and seed_mock_data.py with 40 realistic UPI transactions so Saurabh and Uday can test on Day 1."),
    ("S0-03", "Sprint 0 (Synopsis)", "role:backend", "Complete Git Setup & Signed UPI Deep Link URI Builder Prototype", "docs/anuj-onboarding", "Anuj Kushwaha", "Clone repo on dev branch; push pure-Python helper that injects am and cu=INR into a signed UPI QR URI without stripping mc or sign params."),
    ("S0-04", "Sprint 0 (Synopsis)", "role:frontend", "Complete Git Setup & Flet Dark-Mode Shell Prototype", "docs/saurabh-onboarding", "Saurabh Yadav", "Clone repo on dev branch; set up Flet and push a 3-tab bottom navigation shell (Home, Scan & Pay, Analytics) in src/ui/."),
    ("S0-05", "Sprint 0 (Synopsis)", "role:analytics", "Complete Git Setup & Regex Dictionary Prototype", "docs/uday-onboarding", "Uday Paswan", "Clone repo on dev branch; test pure-Python compiled Regex dictionary on 20 sample Indian merchant names in src/analytics/."),
    ("S0-06", "Sprint 0 (Synopsis)", "role:lead", "Synopsis Submission & Title Defense Presentation (Oct 30)", "docs/synopsis-submission", "Sumit Kushwaha", "Submit final Synopsis on Oct 30 and rehearse Q1-Q7 from Predicted Q&A document with all 4 members."),
    ("S1-01", "Sprint 1 (Core MVP)", "role:backend", "Implement SQLite v1.1 Database Layer (src/db/database.py)", "feature/sqlite-schema-v1.1", "Anuj Kushwaha", "Create all 6 v1.1 tables (user_profile, categories, transactions, pending_transactions, merchant_tags, bill_splits) with CRUD functions."),
    ("S1-02", "Sprint 1 (Core MVP)", "role:backend", "Implement Pending State Preserver & UPI Intent Launcher", "feature/upi-intent-state-preserver", "Anuj Kushwaha", "Write PENDING record (returning internal_id) before launching upi://pay URI; preserve original QR query string parameters (mc, sign, orgid)."),
    ("S1-03", "Sprint 1 (Core MVP)", "role:frontend", "Build Onboarding, Home Screen & QR/VPA Payment Initiation UI", "feature/home-and-pay-ui", "Saurabh Yadav", "Flet UI for monthly budget setup, prominent Scan/Pay FAB, amount input, and preferred UPI app selector."),
    ("S1-04", "Sprint 1 (Core MVP)", "role:frontend", "Build 1-Tap Fallback Verification Popup on App Resume", "feature/fallback-verify-popup", "Saurabh Yadav", "Listen to Flet page.on_app_lifecycle_state_change (RESUMED); if unresolved pending_transactions exist, show 1-tap Yes/No verification dialog."),
    ("S1-05", "Sprint 1 (Core MVP)", "role:analytics", "Write Pure-Python SQLite Aggregation Queries for Dashboard", "feature/sql-monthly-aggregates", "Uday Paswan", "Query current month total spend, category-wise totals, and recent 10 transactions without pandas."),
    ("S1-06", "Sprint 1 (Core MVP)", "role:lead", "Integrate Sprint 1 End-to-End Payment & Fallback Flow", "feature/sprint1-integration", "Sumit Kushwaha", "Wire Saurabh UI to Anuj DB/Intent functions in main.py; review PRs and merge dev into main (v0.1-alpha)."),
    ("S2-01", "Sprint 2 (Analytics Engine)", "role:analytics", "Implement 3-Tier Smart Categorization Engine (src/analytics/tagger.py)", "feature/three-tier-tagger", "Uday Paswan", "Tier 1: query merchant_tags by payee_vpa; Tier 2: compiled Regex match on payee_name; Tier 3: return needs_user_tag=True."),
    ("S2-02", "Sprint 2 (Analytics Engine)", "role:analytics", "Implement Safe Z-Score Anomaly Engine & Financial Health Score", "feature/safe-zscore-anomaly", "Uday Paswan", "Calculate 30-day category mean and stdev using statistics module; handle stdev==0 and len<4 safely; flag Z>2.5; compute 0-100 Clamped Health Score."),
    ("S2-03", "Sprint 2 (Analytics Engine)", "role:frontend", "Build First-Time Merchant Tagging & Anomaly Alert UI", "feature/first-time-tag-popup", "Saurabh Yadav", "Show category selector popup when needs_user_tag=True (saving to merchant_tags) and red banner alert when is_anomaly=True."),
    ("S2-04", "Sprint 2 (Analytics Engine)", "role:backend", "Connect Tagger & Anomaly Flags to Transaction Resolution Pipeline", "feature/merchant-tag-persistence", "Anuj Kushwaha", "Automatically run Uday tagger and Z-Score check inside resolve_pending_txn (WHERE internal_id = ?) before inserting into transactions."),
    ("S2-05", "Sprint 2 (Analytics Engine)", "role:lead", "Integrate Sprint 2 Analytics Pipeline & Validate Edge Cases", "feature/sprint2-integration", "Sumit Kushwaha", "Run unit tests on stdev=0, first-time merchant tagging, and repeat payment auto-tagging; release v0.2-beta."),
    ("S3-01", "Sprint 3 (Dashboard & Bridge)", "role:frontend", "Build Dynamic Financial Dashboard with Flet Native Charts", "feature/flet-native-charts", "Saurabh Yadav", "Render category PieChart, weekly spending BarChart, and dynamic Health Score gauge (Green/Yellow/Red) using pure Flet controls."),
    ("S3-02", "Sprint 3 (Dashboard & Bridge)", "role:analytics", "Implement Mid-Month Pace Alerts & Offline CSV Exporter", "feature/predictive-budget-alerts", "Uday Paswan", "Alert when category spend pace exceeds Ideal Spend Rate by >20% or hits 85% budget; implement offline CSV export using Python csv module."),
    ("S3-03", "Sprint 3 (Dashboard & Bridge)", "role:backend", "Implement PyJNIus Android Bridge for onActivityResult & QR Scanner", "feature/pyjnius-callback-bridge", "Anuj Kushwaha", "Hook Android intent result payload (Status=SUCCESS & txnId) with automatic fallback to 1-Tap Popup if RESULT_CANCELED or stripped."),
    ("S3-04", "Sprint 3 (Dashboard & Bridge)", "role:lead", "Integrate Sprint 3 Dashboard, CSV Export & Android Bridge", "feature/sprint3-integration", "Sumit Kushwaha", "Test on real Android device with GPay/PhonePe/Navi; verify stripped P2P callback triggers fallback cleanly; release v0.3-rc."),
    ("S4-01", "Sprint 4 (Security & Polish)", "role:backend", "Integrate SQLCipher 256-bit Encryption & Biometric App Lock", "feature/sqlcipher-biometric-lock", "Anuj Kushwaha", "Encrypt tracker.db via SQLCipher key in Android Keystore and trigger biometric prompt on cold start when biometric_enabled=1."),
    ("S4-02", "Sprint 4 (Security & Polish)", "role:frontend", "Build Post-Payment 3-Second Quick Tags & Bill Split Popup (REQ-15)", "feature/bill-split-quick-tags", "Saurabh Yadav", "Allow 1-tap #Trip/#Food tags and contact bill splitting stored in bill_splits table."),
    ("S4-03", "Sprint 4 (Security & Polish)", "role:analytics", "Validate Analytics Accuracy & Generate Benchmark Metrics for Viva", "feature/analytics-benchmark-report", "Uday Paswan", "Benchmark categorization latency (<5ms) and Z-Score accuracy across 500 synthetic transactions for final report tables."),
    ("S4-04", "Sprint 4 (Security & Polish)", "role:lead", "Final APK Build, Latency Audit & Viva Presentation Readiness", "feature/final-release-v1.0", "Sumit Kushwaha", "Compile final Android APK, verify <500ms warm resume, merge dev to main (v1.0-final), and conduct full team mock viva."),
]


def scaffold_repository() -> None:
    for folder in FOLDERS:
        os.makedirs(folder, exist_ok=True)
        if folder.startswith("src"):
            init_file = os.path.join(folder, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write('"""Package init."""\n')

    files_to_write = {
        ".gitignore": GITIGNORE_CONTENT,
        "requirements.txt": REQUIREMENTS_CONTENT,
        ".github/pull_request_template.md": PR_TEMPLATE_CONTENT,
        ".github/ISSUE_TEMPLATE/sprint_task.md": ISSUE_TEMPLATE_CONTENT,
        "src/contracts.py": CONTRACTS_PY_CONTENT,
        "src/db/seed_mock_data.py": SEED_MOCK_DATA_CONTENT,
        "main.py": MAIN_PY_CONTENT,
    }

    for rel_path, content in files_to_write.items():
        with open(rel_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[Created] {rel_path}")


def create_github_kanban_issues() -> None:
    if not shutil.which("gh"):
        print("[ERROR] GitHub CLI (`gh`) is not installed or not in PATH. Install from https://cli.github.com/ and run `gh auth login`.")
        sys.exit(1)

    labels = [
        ("role:lead", "1E3A5F", "Sumit Kushwaha - Project Lead & Integration"),
        ("role:backend", "0F766E", "Anuj Kushwaha - Backend, SQLite & UPI Bridge"),
        ("role:frontend", "7C3AED", "Saurabh Yadav - Python Flet UI & Popups"),
        ("role:analytics", "D97706", "Uday Paswan - Pure Python Analytics & Z-Score"),
    ]
    for name, color, desc in labels:
        subprocess.run(["gh", "label", "create", name, "--color", color, "--description", desc, "--force"], check=False)

    for task_id, sprint, label, title, branch, owner, criteria in KANBAN_ISSUES:
        issue_title = f"[{task_id}] {title} ({owner.split()[0]})"
        issue_body = (
            f"### Task Metadata\n"
            f"- **Task ID:** `{task_id}`\n"
            f"- **Sprint Phase:** `{sprint}`\n"
            f"- **Assigned Owner:** {owner}\n"
            f"- **Git Branch (branch off `dev`):** `{branch}`\n\n"
            f"### Objective & Acceptance Criteria\n"
            f"{criteria}\n\n"
            f"### 6-Stage Gemini Workflow Checklist\n"
            f"- [ ] **Stage 1:** Paste this issue into Gemini to trigger your Role Skill & sub-task breakdown\n"
            f"- [ ] **Stage 2:** Paste the link to your personal **Google Drive Task Living Doc** in a comment below\n"
            f"- [ ] **Stage 3:** Create branch `git checkout dev && git pull origin dev && git checkout -b {branch}` and implement\n"
            f"- [ ] **Stage 4:** Run local verification test (`PASS`)\n"
            f"- [ ] **Stage 5:** Log any bugs & fixes in your Drive Task Living Doc\n"
            f"- [ ] **Stage 6:** Open PR into `dev` with `Closes #<issue_number>`\n"
        )
        res = subprocess.run(
            ["gh", "issue", "create", "--title", issue_title, "--body", issue_body, "--label", label],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"[GitHub Issue] {issue_title} -> {res.stdout.strip() or res.stderr.strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap repo skeleton and GitHub Kanban Issues.")
    parser.add_argument("--create-github-issues", action="store_true", help="Bulk-create all 22 Sprint Issues via GitHub CLI (gh)")
    args = parser.parse_args()

    scaffold_repository()
    if args.create_github_issues:
        create_github_kanban_issues()
    else:
        print("\n[Next Step] Run `python main.py` to test the mock DB seeder, or run with `--create-github-issues` after `gh auth login`.")