"""Anuj Kushwaha — UPI 2.0 Signed QR Deep-Link Builder (Task S0-03)."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def build_signed_upi_uri(raw_qr_uri: str, amount: float) -> str:
    """Preserves NPCI UPI 2.0 signed parameters (mc, sign, orgid, tr, mode) while injecting am & cu=INR."""
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


if __name__ == "__main__":
    sample = "upi://pay?pa=zomato@hdfcbank&pn=Zomato&mc=5812&sign=NPCI_SIG_99&orgid=159002"
    out = build_signed_upi_uri(sample, 199.0)
    assert "mc=5812" in out and "sign=NPCI_SIG_99" in out and "am=199.00" in out
    print("[PASS] Anuj S0-03 Signed UPI URI Builder Unit Test:", out)