"""
Automated Expenditure Tracker - Backend UPI Intent & State Preserver Bridge
Module: src/backend/upi_bridge.py
Owner: Anuj Kushwaha (Backend Developer)
Sprint: Sprint 1 (Core MVP) - Task S1-02
Branch: feature/upi-intent-state-preserver

Responsibilities:
1. NPCI UPI 2.0 Signed Deep Link generation (preserves mc, sign, orgid, tr, mode).
2. UPI URI extraction & normalization (parse_upi_uri).
3. Pre-intent atomic pending state preservation (initiate_upi_intent_flow -> pending_transactions).
4. Cross-platform intent dispatch with desktop simulator fallback (launch_upi_intent).
"""

import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

# Fallback-safe import for database layer
try:
    from src.db.database import DB_FILE, create_pending_txn, init_db
except ImportError:
    # If run standalone or via contracts fallback
    try:
        from src.contracts import create_pending_txn, ensure_db_ready
        DB_FILE = "tracker_dev.db"
        init_db = ensure_db_ready
    except ImportError:
        DB_FILE = "tracker_dev.db"
        create_pending_txn = None
        init_db = None


def parse_upi_uri(raw_uri: str) -> Dict[str, Any]:
    """
    Parses a raw UPI deep-link URI or shorthand VPA address into structured fields.
    
    Handles:
    - Canonical URIs: 'upi://pay?pa=store@upi&pn=Store&am=250.00&cu=INR&mc=5411'
    - Shorthand VPAs: 'merchant@okaxis' or 'friend@upi'
    
    Returns:
        dict with keys: 'pa', 'pn', 'am', 'cu', 'mc', 'tr', 'sign', 'orgid', 'mode', 'raw_params'
    """
    cleaned = (raw_uri or "").strip()
    if not cleaned:
        raise ValueError("UPI URI or VPA cannot be empty")

    if not cleaned.startswith("upi://pay"):
        if "@" in cleaned:
            # Handle shorthand VPA
            vpa = cleaned.split("?")[0]
            name = vpa.split("@")[0].replace(".", " ").title()
            return {
                "pa": vpa,
                "pn": name or "Merchant",
                "am": None,
                "cu": "INR",
                "mc": None,
                "tr": None,
                "sign": None,
                "orgid": None,
                "mode": "00",
                "raw_params": {"pa": vpa, "pn": name or "Merchant", "cu": "INR"},
            }
        else:
            cleaned = f"upi://pay?pa={cleaned}&pn=Merchant"

    parts = urlsplit(cleaned)
    query_tuples = parse_qsl(parts.query, keep_blank_values=True)
    raw_params = {k: v for k, v in query_tuples}

    # Extract amount if present and valid
    parsed_am = None
    if "am" in raw_params and raw_params["am"]:
        try:
            parsed_am = float(raw_params["am"])
        except ValueError:
            parsed_am = None

    payee_vpa = raw_params.get("pa", "").strip()
    payee_name = raw_params.get("pn", "").strip()
    if not payee_name and payee_vpa:
        payee_name = payee_vpa.split("@")[0].replace(".", " ").title()

    return {
        "pa": payee_vpa,
        "pn": payee_name or "Merchant",
        "am": parsed_am,
        "cu": raw_params.get("cu", "INR"),
        "mc": raw_params.get("mc"),
        "tr": raw_params.get("tr"),
        "sign": raw_params.get("sign"),
        "orgid": raw_params.get("orgid"),
        "mode": raw_params.get("mode", "00"),
        "raw_params": raw_params,
    }


def build_signed_upi_uri(raw_qr_uri: str, amount: float) -> str:
    """
    Builds a canonical UPI payment URI preserving signed merchant parameters (UPI 2.0).
    
    Critical NPCI Parameters Preserved:
    - mc: Merchant Category Code (4-digit ISO 18245 code)
    - sign: Base64/Hex digital signature verified by PSP
    - orgid: NPCI registered payment aggregator ID
    - tr: Transaction reference ID for merchant reconciliation
    - mode: Payment flow mode (e.g. 01 for static QR, 02 for dynamic QR)
    
    Safe injection:
    - Injects 'am' formatted to 2 decimal places (e.g., '199.00')
    - Injects 'cu=INR'
    - Uses safe='@/:=' and quote_via=quote to protect VPA separators, Base64 '=' padding, and '%20'
    """
    if amount <= 0:
        raise ValueError(f"Transaction amount must be strictly positive (> 0), got: {amount}")

    raw_cleaned = (raw_qr_uri or "").strip()
    if not raw_cleaned.startswith("upi://pay"):
        raw_cleaned = f"upi://pay?pa={raw_cleaned}&pn=Merchant"

    parts = urlsplit(raw_cleaned)
    params = parse_qsl(parts.query, keep_blank_values=True)

    updated_params = []
    seen_am = False
    seen_cu = False

    for k, v in params:
        k_lower = k.lower()
        if k_lower == "am":
            updated_params.append(("am", f"{float(amount):.2f}"))
            seen_am = True
        elif k_lower == "cu":
            updated_params.append(("cu", "INR"))
            seen_cu = True
        else:
            updated_params.append((k, v))

    if not seen_am:
        updated_params.append(("am", f"{float(amount):.2f}"))
    if not seen_cu:
        updated_params.append(("cu", "INR"))

    # Critical Guardrail: safe="@/:=" ensures '=' in Base64 signatures and '@' in VPAs are not escaped
    new_query = urlencode(updated_params, quote_via=quote, safe="@/:=")
    return urlunsplit((parts.scheme or "upi", parts.netloc or "pay", parts.path, new_query, parts.fragment))


def initiate_upi_intent_flow(
    raw_qr_uri: str,
    amount: float,
    db_path: str = DB_FILE,
) -> Dict[str, Any]:
    """
    Core S1-02 Pipeline: Preserves transaction state BEFORE launching UPI app.
    
    Steps:
    1. Validates amount and parses payee VPA and Name.
    2. Constructs verified signed UPI deep link URI.
    3. Atomically inserts a PENDING row in SQLite 'pending_transactions'.
    4. Returns structured payload containing 'internal_id' for downstream verification.
    
    Returns:
        {
            "internal_id": int,
            "intent_uri": str,
            "payee_vpa": str,
            "payee_name": str,
            "amount": float,
            "status": "PENDING"
        }
    """
    if amount <= 0:
        raise ValueError(f"Amount must be greater than zero, received {amount}")

    parsed = parse_upi_uri(raw_qr_uri)
    payee_vpa = parsed["pa"]
    payee_name = parsed["pn"]

    if not payee_vpa:
        raise ValueError(f"Failed to extract payee VPA from URI: {raw_qr_uri}")

    # 1. Build canonical signed URI
    signed_uri = build_signed_upi_uri(raw_qr_uri, amount)

    # 2. Persist state in SQLite before external switch
    internal_id = None
    if create_pending_txn is not None:
        internal_id = create_pending_txn(
            amount=amount,
            payee_vpa=payee_vpa,
            payee_name=payee_name,
            raw_qr_uri=raw_qr_uri,
            db_path=db_path,
        )
    else:
        # Fallback direct insert with explicit connection closing
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=5.0)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO pending_transactions (amount, payee_vpa, payee_name, raw_qr_uri, status)
                VALUES (?, ?, ?, ?, 'PENDING')
                """,
                (float(amount), payee_vpa, payee_name, raw_qr_uri),
            )
            conn.commit()
            internal_id = cur.lastrowid
        finally:
            conn.close()

    return {
        "internal_id": internal_id,
        "intent_uri": signed_uri,
        "payee_vpa": payee_vpa,
        "payee_name": payee_name,
        "amount": round(float(amount), 2),
        "status": "PENDING",
    }


def launch_upi_intent(intent_uri: str, page: Optional[Any] = None) -> bool:
    """
    Cross-platform UPI intent launcher.
    
    - In mobile Flet runtime: invokes page.launch_url(intent_uri) which issues
      an Android Intent (android.intent.action.VIEW).
    - In desktop/CLI simulation runtime: safely logs the intent launch without crashing.
    """
    if not intent_uri:
        return False

    if page is not None and hasattr(page, "launch_url"):
        try:
            page.launch_url(intent_uri)
            return True
        except Exception as e:
            print(f"[UPI Bridge Warning] page.launch_url failed: {e}. Falling back to simulation.")

    # Desktop simulator log
    print(f"[SIMULATED INTENT LAUNCH] Dispatched URI -> {intent_uri}")
    return True


# =====================================================================
# Priority Upgrade 1: Mandatory Self-Test Footer (Viva & Unit Check)
# =====================================================================
if __name__ == "__main__":
    import sqlite3
    import tempfile

    print("\n==================================================")
    print(" Running Anuj Kushwaha's Task S1-02 Isolated Unit Tests")
    print("==================================================")

    # Test 1: Signed NPCI 2.0 QR Code preservation
    sample_qr = (
        "upi://pay?pa=starbucks@hdfcbank&pn=Starbucks%20Coffee"
        "&mc=5812&sign=MEYCIQC3Z8810A98BCF==&orgid=159002&tr=SBX982341&mode=02"
    )
    built_uri = build_signed_upi_uri(sample_qr, 349.50)
    assert "mc=5812" in built_uri, "Failed: 'mc' parameter was dropped"
    assert "sign=MEYCIQC3Z8810A98BCF==" in built_uri, "Failed: 'sign' signature was dropped"
    assert "orgid=159002" in built_uri, "Failed: 'orgid' was dropped"
    assert "tr=SBX982341" in built_uri, "Failed: 'tr' transaction reference dropped"
    assert "mode=02" in built_uri, "Failed: 'mode' dropped"
    assert "am=349.50" in built_uri, "Failed: 'am' not injected with 2 decimals"
    assert "cu=INR" in built_uri, "Failed: 'cu=INR' not injected"
    assert "@" in built_uri and "%40" not in built_uri, "Failed: '@' was double-encoded"
    assert built_uri.startswith("upi://pay?"), f"Failed: Invalid URI scheme prefix: {built_uri}"
    print("[PASS] Test 1: NPCI UPI 2.0 signed merchant parameters preserved verbatim.")

    # Test 2: Shorthand VPA parsing
    parsed_vpa = parse_upi_uri("anuj.kushwaha@paytm")
    assert parsed_vpa["pa"] == "anuj.kushwaha@paytm"
    assert "Anuj" in parsed_vpa["pn"]
    assert parsed_vpa["cu"] == "INR"
    built_from_vpa = build_signed_upi_uri("anuj.kushwaha@paytm", 50.0)
    assert built_from_vpa.startswith("upi://pay?")
    assert "pa=anuj.kushwaha@paytm" in built_from_vpa
    assert "am=50.00" in built_from_vpa
    print("[PASS] Test 2: Shorthand VPA conversion and URI normalization.")

    # Test 3: Zero & Negative amount guard
    try:
        build_signed_upi_uri("merchant@upi", -10.0)
        assert False, "Failed: Negative amount did not raise ValueError"
    except ValueError:
        pass
    print("[PASS] Test 3: Negative amount input guard passed.")

    # Test 4: Atomic State Preservation in SQLite (pending_transactions)
    test_db = os.path.join(tempfile.gettempdir(), "test_s1_02_tracker.db")
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except (PermissionError, OSError):
        pass

    conn = sqlite3.connect(test_db)
    try:
        conn.execute(
            """
            CREATE TABLE pending_transactions (
                internal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                payee_vpa TEXT NOT NULL,
                payee_name TEXT NOT NULL,
                raw_qr_uri TEXT,
                init_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING'
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    payload = initiate_upi_intent_flow(sample_qr, 349.50, db_path=test_db)
    assert payload["internal_id"] is not None and payload["internal_id"] > 0, "Missing internal_id"
    assert payload["status"] == "PENDING"
    assert payload["amount"] == 349.50
    assert payload["payee_vpa"] == "starbucks@hdfcbank"

    # Verify row actually exists in SQLite with explicit close
    conn = sqlite3.connect(test_db)
    try:
        row = conn.execute(
            "SELECT internal_id, amount, payee_vpa, status FROM pending_transactions WHERE internal_id = ?",
            (payload["internal_id"],),
        ).fetchone()
        assert row is not None, "Pending row not found in database"
        assert row[0] == payload["internal_id"]
        assert row[1] == 349.50
        assert row[2] == "starbucks@hdfcbank"
        assert row[3] == "PENDING"
    finally:
        conn.close()
    print(f"[PASS] Test 4: Pre-intent state recorded atomically in SQLite (internal_id={payload['internal_id']}).")

    # Test 5: Intent dispatch simulation
    dispatched = launch_upi_intent(payload["intent_uri"], page=None)
    assert dispatched is True, "Intent launcher failed"
    print("[PASS] Test 5: Cross-platform intent dispatch simulation passed.")

    # Cleanup temporary test database with safe Windows exception guard
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except (PermissionError, OSError):
        pass

    print("==================================================")
    print(" ALL TASK S1-02 UNIT TESTS PASSED SUCCESSFULLY! ")
    print("==================================================\n")