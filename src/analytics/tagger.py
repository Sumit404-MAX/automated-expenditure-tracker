"""Uday Paswan — Pure-Python 3-Tier Smart Categorization Engine (Task S0-05)."""

import os
import re
import sqlite3
from src.db.seed_mock_data import DB_FILE, seed_mock_database

COMPILED_REGEX_RULES = [
    (
        1,
        "Food & Dining",
        re.compile(
            r"zomato|swiggy|eatsure|magicpin|box8|faasos|behrouz|ovenstory|wendys|dominos|pizzahut|pizza hut|"
            r"lapinoz|la pinoz|kfc|mcdonald|burgerking|burger king|subway|starbucks|chaayos|chaipoint|chai point|"
            r"ccd|barista|tim hortons|blue tokai|third wave|wow momo|haldiram|bikanervala|bikaner|aggarwal|aggrawal|"
            r"kaleva|nathu|baskin|naturals|kwality walls|keventers|sharmatea|"
            r"momo|momos|\broll\b|rolls|kathi|frankie|biryani|shawarma|kebab|kabab|tikka|tandoori|chaap|"
            r"burger|pizza|sandwich|toast|maggi|noodle|noodles|chowmein|manchurian|chinese|pasta|macaroni|"
            r"dosa|idli|\bvada\b|uttapam|sambhar|samosa|kachori|pakora|chaat|golgappa|pani puri|panipuri|bhel|tikki|"
            r"pav bhaji|vada pav|vadapav|chole|bhature|kulcha|rajma|chawal|kadhi|paratha|parantha|roti|naan|thali|"
            r"pulao|khichdi|poha|upma|jalebi|gulab jamun|rasgulla|rabri|kulfi|falooda|icecream|ice cream|sundae|"
            r"waffle|pancake|pastry|\bcake\b|brownie|donut|cookie|biscuit|namkeen|bhujia|"
            r"\bchai\b|\btea\b|coffee|espresso|cappuccino|latte|lassi|chaas|buttermilk|juice|shake|milkshake|"
            r"smoothie|sharbat|nimbu|soda|mojito|mocktail|cold drink|soft drink|lemonade|sugarcane|ganne|"
            r"snack|snacks|refreshment|canteen|cafeteria|mess|tiffin|dabba|rasoi|bhojanalaya|dhaba|restaurant|"
            r"restro|bistro|cafe|bakery|bakers|confectionery|sweet|sweets|mithai|mishthan|food|foods|foodie|"
            r"kitchen|diner|dining|\beat\b|eatery|zaika|tadka|bawarchi|caterer|catering",
            re.IGNORECASE,
        ),
    ),
    (
        2,
        "Travel",
        re.compile(
            r"uber|ola|rapido|indrive|blusmart|blu smart|meru|savaari|zoomcar|revv|yulu|bounce|vogo|"
            r"\bcab\b|cabs|\btaxi\b|\bauto\b|rickshaw|e-rickshaw|erickshaw|shuttle|carpool|\bride\b|rides|"
            r"irctc|rail|railway|\buts\b|metro|dmrc|nmrc|bmrc|mmrc|rrts|namo bharat|rapid rail|"
            r"redbus|abhibus|zingbus|intracity|nuego|flixbus|upsrtc|\bdtc\b|hrtc|rsrtc|msrtc|ksrtc|bmtc|"
            r"\bbus\b|transport|transit|commute|makemytrip|goibibo|ixigo|cleartrip|easemytrip|yatra|"
            r"agoda|booking\.com|airbnb|\boyo\b|indigo|air india|airindia|vistara|spicejet|akasa|"
            r"airline|airport|flight|fastag|nhai|\btoll\b|parking|\btour\b|travels|travel",
            re.IGNORECASE,
        ),
    ),
    (
        3,
        "Groceries",
        re.compile(
            r"blinkit|grofers|zepto|instamart|bigbasket|bbnow|bbdaily|dmart|d-mart|reliancesmart|reliance smart|"
            r"reliance fresh|jiomart|jio mart|spencers|star bazaar|easyday|nature basket|24seven|safal|"
            r"mother dairy|amul|country delight|milkbasket|freshtohome|licious|"
            r"kirana|kiryana|general store|provision|provisions|departmental|supermarket|supermart|hypermarket|"
            r"\bmart\b|grocery|groceries|rashan|ration|\batta\b|chakki|flour mill|\brice\b|\bdal\b|spices|masala|"
            r"dry fruit|dryfruits|sabzi|subzi|vegetable|veggies|fruits|mandi|organic|dairy|\bmilk\b|paneer|"
            r"\begg\b|eggs|poultry|meat|mutton|chicken shop|daily needs|home needs",
            re.IGNORECASE,
        ),
    ),
    (
        4,
        "Fuel",
        re.compile(
            r"hpcl|hindustan petroleum|bpcl|bharat petroleum|iocl|indian oil|indianoil|reliance petroleum|"
            r"jio-bp|jiobp|nayara|essar|shell|totalenergies|\bigl\b|indraprastha gas|\bmgl\b|adani gas|"
            r"\bcng\b|petrol|diesel|fuel|filling station|gas station|fuel station|petrol pump|\bpump\b|"
            r"octane|xtrapower|smartfleet|ev charging|tata power ez|statiq|ather grid|chargezone",
            re.IGNORECASE,
        ),
    ),
    (
        5,
        "Utilities",
        re.compile(
            r"jio|myjio|airtel|\bvi\b|vodafone|idea|bsnl|mtnl|act fibernet|excitel|hathway|tikona|"
            r"tata play|tataplay|tatasky|dish tv|dishtv|\bd2h\b|sun direct|\bdth\b|recharge|prepaid|postpaid|"
            r"broadband|wifi|wi-fi|fiber|fibernet|internet|telecom|mobile bill|telephone|"
            r"uppcl|pvvnl|dvvnl|mvvnl|npcl|torrent power|bses|brpl|bypl|tpddl|ndpl|tata power|tatapower|"
            r"adani electricity|mahavitaran|mseb|bescom|tangedco|cesc|wbsedcl|pspcl|dhbvn|uhbvn|"
            r"electricity|electric|power|bijli|jal board|\bdjb\b|water|sewage|"
            r"indane|bharatgas|bharat gas|hp gas|hpgas|piped gas|\bpng\b|\bgas\b|cylinder|"
            r"municipal|property tax|house tax|maintenance|utility|utilities|billdesk|bbps",
            re.IGNORECASE,
        ),
    ),
]


def categorize_transaction(payee_vpa: str, payee_name: str, db_path: str = DB_FILE) -> dict:
    """3-Tier Categorization: Tier 1 (SQLite merchant_tags) -> Tier 2 (Regex) -> Tier 3 (User Tag Popup)."""
    vpa_clean = (payee_vpa or "").strip().lower()
    name_clean = (payee_name or "").strip()

    try:
        if db_path and not os.path.exists(db_path):
            seed_mock_database(db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT m.category_id, c.name, m.confidence "
                "FROM merchant_tags m "
                "JOIN categories c ON m.category_id = c.category_id "
                "WHERE LOWER(m.vpa_pattern) = ?;",
                (vpa_clean,),
            )
            row = cur.fetchone()
        except sqlite3.OperationalError:
            conn.close()
            seed_mock_database(db_path, force_reset=True)
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT m.category_id, c.name, m.confidence "
                "FROM merchant_tags m "
                "JOIN categories c ON m.category_id = c.category_id "
                "WHERE LOWER(m.vpa_pattern) = ?;",
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

    return {
        "category_id": 6,
        "category_name": "Uncategorized",
        "needs_user_tag": True,
        "confidence": 0.0,
        "tier": "Tier 3 (Needs 1-Tap User Tag)",
    }


if __name__ == "__main__":
    # Ensure tracker_dev.db is freshly seeded with all 6 v1.1 tables & 10 merchant_tags
    seed_mock_database(DB_FILE)

    # Re-tag any existing Uncategorized (6) transactions in tracker_dev.db that now match new Regex rules
    with sqlite3.connect(DB_FILE) as _conn:
        for _tid, _vpa, _name in _conn.execute(
            "SELECT txn_id, payee_vpa, payee_name FROM transactions WHERE category_id = 6"
        ).fetchall():
            _retag = categorize_transaction(_vpa, _name, DB_FILE)
            if _retag["category_id"] != 6:
                _conn.execute(
                    "UPDATE transactions SET category_id = ? WHERE txn_id = ?",
                    (_retag["category_id"], _tid),
                )

    # 1. Verify Tier 1 (SQLite merchant_tags Memory Match from tracker_dev.db)
    r_tier1 = categorize_transaction("zomato@icici", "Zomato")
    assert isinstance(r_tier1, dict) and r_tier1["category_id"] == 1
    assert r_tier1["category_name"] == "Food & Dining" and r_tier1["needs_user_tag"] is False
    assert r_tier1["confidence"] == 1.0 and "Tier 1" in r_tier1["tier"]

    # 2. Verify Tier 2 (Pre-Compiled Regex Heuristic on new VPA + AP Momos)
    r1 = categorize_transaction("apmomos@upi", "AP momos")
    assert isinstance(r1, dict) and r1["category_id"] == 1 and r1["category_name"] == "Food & Dining"
    assert r1["needs_user_tag"] is False and r1["confidence"] == 0.85

    # 3. Verify Tier 3 (Unknown Merchant -> Needs 1-Tap User Tag)
    r2 = categorize_transaction("unknown.shop@okaxis", "Gupta Stationery")
    assert isinstance(r2, dict) and r2["needs_user_tag"] is True and r2["category_id"] == 6
    assert r2["category_name"] == "Uncategorized" and r2["confidence"] == 0.0

    # 4. Verify 20 Sample Indian Merchants (Sprint 0 S0-05 Acceptance Criteria)
    sample_20_merchants = [
        ("zomato.order@hdfcbank", "Zomato India", 1),
        ("apmomos@upi", "AP Momos", 1),
        ("Nitracanteen.order@sbi", "NITRA CANTEEN", 1),
        ("haldiram.snacks@sbi", "Haldiram Bhujiawala", 1),
        ("sharmatea@upi", "Sharma Tea Stall", 1),
        ("uber.india@axis", "Uber Cab Trip", 2),
        ("ola.cabs@hdfcbank", "Ola Auto Ride", 2),
        ("rapido.bike@icici", "Rapido Bike Taxi", 2),
        ("irctc.tourism@sbi", "IRCTC Rail Ticket", 2),
        ("dmrc.smartcard@axis", "Delhi Metro Rail", 2),
        ("blinkit.grofers@hdfcbank", "Blinkit Instant", 3),
        ("zepto.now@icici", "Zepto Grocery", 3),
        ("bigbasket.daily@axis", "BigBasket Supermart", 3),
        ("dmart.avenue@sbi", "DMart Supermarket", 3),
        ("apnakirana@okaxis", "Apna Kirana Mart", 3),
        ("hpcl.retail@icici", "HPCL Petrol Pump", 4),
        ("bpcl.smartfleet@sbi", "BPCL Fuel Station", 4),
        ("iocl.xtrapower@axis", "Indian Oil Pump", 4),
        ("jio.prepaid@paytm", "Jio Mobile Recharge", 5),
        ("uppcl.bill@sbi", "UPPCL Electricity Bill", 5),
    ]
    for vpa, m_name, expected_cid in sample_20_merchants:
        res = categorize_transaction(vpa, m_name)
        assert res["category_id"] == expected_cid, f"Mismatch for {m_name}: {res}"

    print("[PASS] Uday S0-05 3-Tier Tagger Unit Test Verified (Tier 1 DB + 20 Indian Merchants + Tier 3):", r1, r2)