"""Locked Cross-Module Interface Contracts (v1.1).

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
