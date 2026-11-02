"""
src/ui/scanner_view.py
Saurabh Yadav (Frontend UI - Task S1-03)
Flet 1.0+/0.80+ Dark-Mode QR / VPA Scanner & UPI 2.0 Intent Launcher UI:
- 4 Interactive Indian Merchant QR Presets (Signed NPCI QR, Anomaly Spike, Metro, Tier-3 Kirana)
- Payee VPA, Payee Name & Amount (INR) Inputs with Real-Time Validation
- Preferred UPI App Selector Chips (GPay, PhonePe, Paytm, BHIM)
- Live Pre-Payment Intelligence Card (3-Tier Auto-Tag + Z-Score Check + Signed URI Inspector)
- Dual Execution Buttons: Launch UPI App (Save Pending) & Instant Pay & Verify
"""

import urllib.parse
import flet as ft
from src.contracts import (
    build_signed_upi_uri,
    categorize_transaction,
    create_pending_txn,
    detect_spending_anomaly,
    ensure_db_ready,
    resolve_pending_txn,
)


# ============================================================================
# 1. FLET 1.0+ / 0.80+ BULLETPROOF LAYOUT HELPERS (No deprecated APIs)
# ============================================================================
def _pad(left: float = 0, top: float = 0, right: float = 0, bottom: float = 0) -> ft.Padding:
    """Returns Flet 1.0+/0.80+ ft.Padding without calling removed ft.padding.only."""
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def _border(color: str = "#334155", width: float = 1.0) -> ft.Border:
    """Returns Flet 1.0+/0.80+ 4-sided ft.Border without calling removed ft.border.all."""
    side = ft.BorderSide(width=width, color=color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def _safe_btn(
    label: str,
    on_click_handler,
    bgcolor: str = "#2563EB",
    text_color: str = "#FFFFFF",
    expand: bool = False,
) -> ft.Container:
    """Interactive dark-mode pill button compatible across Flet 0.80+ and 1.0.4."""
    return ft.Container(
        content=ft.Text(
            label,
            size=12,
            weight=ft.FontWeight.BOLD,
            color=text_color,
            text_align=ft.TextAlign.CENTER,
        ),
        bgcolor=bgcolor,
        padding=_pad(12, 9, 12, 9),
        border_radius=8,
        on_click=on_click_handler,
        expand=expand,
        alignment=getattr(ft.alignment, "center", None),
    )


def _safe_outlined_btn(
    label: str,
    on_click_handler,
    border_color: str = "#475569",
    text_color: str = "#E2E8F0",
    expand: bool = False,
) -> ft.Container:
    """Outlined preset button for simulating merchant QR scans."""
    return ft.Container(
        content=ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600,
            color=text_color,
            text_align=ft.TextAlign.CENTER,
        ),
        bgcolor="#0F172A",
        border=_border(border_color, 1.0),
        padding=_pad(10, 7, 10, 7),
        border_radius=8,
        on_click=on_click_handler,
        expand=expand,
        alignment=getattr(ft.alignment, "center", None),
    )


def _notify(page: ft.Page, message: str, bgcolor: str = "#10B981") -> None:
    """Displays a SnackBar across both Flet 1.0+ and legacy overlay."""
    if page is None:
        return
    snack = ft.SnackBar(
        content=ft.Text(message, color="#FFFFFF", size=12, weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        open=True,
    )
    try:
        page.overlay.append(snack)
        page.update()
    except Exception:
        if hasattr(page, "open"):
            page.open(snack)


def _switch_main_tab(page: ft.Page, tab_index: int) -> None:
    """Switches bottom navigation tab inside main.py shell after payment action."""
    if page is None:
        return
    try:
        root_col = page.controls[0]
        nav_bar = root_col.controls[2]
        nav_bar.selected_index = tab_index
        if callable(getattr(nav_bar, "on_change", None)):
            nav_bar.on_change(type("NavEvt", (), {"control": nav_bar})())
        else:
            page.update()
    except Exception:
        pass


# ============================================================================
# 2. PRIMARY VIEW BUILDER: build_scanner_view(page) -> ft.Control
# ============================================================================
def build_scanner_view(page: ft.Page = None) -> ft.Control:
    """
    Builds the Sprint 1 QR Scanner & UPI 2.0 Intent Payment View.
    Called dynamically by main.py: build_scanner_view(page).
    """
    ensure_db_ready()

    selected_app = ["GPay"]
    raw_qr_state = [
        "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&tid=TXN102938&tr=TR998877&sign=MEYCIQC3x...&orgid=159981&mode=02"
    ]

    vpa_tf = ft.TextField(
        label="Merchant / Payee VPA",
        value="chaipoint@icici",
        text_size=12,
        height=46,
        color="#FFFFFF",
        bgcolor="#0F172A",
        border_color="#334155",
        expand=True,
    )
    name_tf = ft.TextField(
        label="Payee Name",
        value="Chai Point",
        text_size=12,
        height=46,
        color="#FFFFFF",
        bgcolor="#0F172A",
        border_color="#334155",
        expand=True,
    )
    amt_tf = ft.TextField(
        label="Amount (INR)",
        value="250.00",
        text_size=14,
        height=46,
        color="#FFFFFF",
        bgcolor="#0F172A",
        border_color="#38BDF8",
    )

    preview_tag_txt = ft.Text("", size=11, weight=ft.FontWeight.BOLD, color="#10B981")
    preview_anom_txt = ft.Text("", size=11, color="#94A3B8")
    uri_txt = ft.Text("", size=10, color="#38BDF8", selectable=True)
    app_chips_row = ft.Row(spacing=6)

    def _parse_amount() -> float:
        try:
            val = float(amt_tf.value.strip() or 0.0)
            return max(0.0, val)
        except ValueError:
            return 0.0

    def refresh_live_preview(*_) -> None:
        amt = _parse_amount()
        vpa = (vpa_tf.value or "").strip() or "merchant@upi"
        name = (name_tf.value or "").strip() or "Merchant"

        # 1. Build Signed UPI 2.0 URI preserving mc, sign, orgid, tr, mode
        base_qr = (
            raw_qr_state[0]
            if f"pa={vpa}" in raw_qr_state[0]
            else f"upi://pay?pa={vpa}&pn={urllib.parse.quote(name)}&mc=0000&mode=02"
        )
        signed_uri = build_signed_upi_uri(base_qr, amt)
        uri_txt.value = signed_uri

        # 2. Live 3-Tier Categorization & Safe Z-Score Anomaly Preview
        tag = categorize_transaction(vpa, name)
        anom = detect_spending_anomaly(tag["category_id"], amt)

        tier_label = tag.get("tier", "Auto-Matched")
        preview_tag_txt.value = f"🏷️ Category: {tag['category_name']} • {tier_label}"
        preview_tag_txt.color = "#F59E0B" if tag.get("needs_user_tag") else "#10B981"

        if anom.get("is_anomaly"):
            preview_anom_txt.value = f"⚠️ Z-SCORE SPIKE ALERT: {anom.get('reason')} (Z={anom.get('z_score')})"
            preview_anom_txt.color = "#EF4444"
        else:
            preview_anom_txt.value = f"✓ Spend Pace Normal: {anom.get('reason')}"
            preview_anom_txt.color = "#94A3B8"

        if page is not None:
            page.update()

    def apply_preset(vpa: str, name: str, amount_str: str, raw_qr: str) -> None:
        vpa_tf.value = vpa
        name_tf.value = name
        amt_tf.value = amount_str
        raw_qr_state[0] = raw_qr
        refresh_live_preview()

    vpa_tf.on_change = refresh_live_preview
    name_tf.on_change = refresh_live_preview
    amt_tf.on_change = refresh_live_preview

    def select_upi_app(app_name: str) -> None:
        selected_app[0] = app_name
        build_app_chips()
        if page is not None:
            page.update()

    def build_app_chips() -> None:
        app_chips_row.controls.clear()
        for app_name in ("GPay", "PhonePe", "Paytm", "BHIM"):
            is_active = selected_app[0] == app_name
            app_chips_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        f"{'✓ ' if is_active else ''}{app_name}",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if is_active else "#94A3B8",
                    ),
                    bgcolor="#2563EB" if is_active else "#0F172A",
                    border=_border("#38BDF8" if is_active else "#334155", 1.0),
                    padding=_pad(10, 6, 10, 6),
                    border_radius=6,
                    on_click=lambda e, a=app_name: select_upi_app(a),
                )
            )

    def on_launch_pending_click(e) -> None:
        amt = _parse_amount()
        if amt <= 0:
            _notify(page, "Enter a valid amount > Rs. 0 before launching UPI!", "#EF4444")
            return
        vpa = vpa_tf.value.strip() or "merchant@upi"
        name = name_tf.value.strip() or "Merchant"
        pid = create_pending_txn(amt, vpa, name, uri_txt.value)
        _notify(
            page,
            f"Pending #{pid} saved & {selected_app[0]} intent launched! Verify in 1-Tap on Home tab.",
            "#F59E0B",
        )
        _switch_main_tab(page, 0)

    def on_instant_pay_click(e) -> None:
        amt = _parse_amount()
        if amt <= 0:
            _notify(page, "Enter a valid amount > Rs. 0 to simulate payment!", "#EF4444")
            return
        vpa = vpa_tf.value.strip() or "merchant@upi"
        name = name_tf.value.strip() or "Merchant"
        pid = create_pending_txn(amt, vpa, name, uri_txt.value)
        resolve_pending_txn(pid, status="RESOLVED", notes=f"Paid via {selected_app[0]}")
        _notify(page, f"Paid Rs. {amt:,.2f} to {name} via {selected_app[0]}!", "#10B981")
        _switch_main_tab(page, 0)

    build_app_chips()
    refresh_live_preview()

    controls_list = [
        # --- 0. ACTIVE LIVE MODULE BANNER ---
        ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "🟢 [LIVE MODULE] Saurabh Yadav • QR Scanner & UPI Intent UI (S1-03)",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#10B981",
                        expand=True,
                    ),
                    ft.Text("UPI 2.0 Signed", size=10, color="#38BDF8"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=_pad(10, 6, 10, 6),
            bgcolor="#0F172A",
            border=_border("#10B981", 1.0),
            border_radius=8,
        ),
        # --- 1. SIMULATED QR CAMERA VIEWFINDER & MERCHANT PRESETS ---
        ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("📷 UPI 2.0 Signed QR Viewfinder", size=13, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                            ft.Text("NPCI Cryptographic Mode", size=10, color="#10B981"),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        "Tap a preset merchant QR below to test signed parameters, Z-Score spikes, or Tier-3 tags:",
                        size=11,
                        color="#94A3B8",
                    ),
                    ft.Row(
                        [
                            _safe_outlined_btn(
                                "☕ Chai Point (Signed)",
                                lambda e: apply_preset(
                                    "chaipoint@icici",
                                    "Chai Point",
                                    "250.00",
                                    "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&tid=TXN102938&tr=TR998877&sign=MEYCIQC3x...&orgid=159981&mode=02",
                                ),
                                border_color="#10B981",
                                text_color="#10B981",
                                expand=True,
                            ),
                            _safe_outlined_btn(
                                "🍔 Zomato (Z-Spike)",
                                lambda e: apply_preset(
                                    "zomato@icici",
                                    "Zomato",
                                    "3800.00",
                                    "upi://pay?pa=zomato@icici&pn=Zomato&mc=5812&sign=ZOMATO_SIG&orgid=4001&mode=02",
                                ),
                                border_color="#EF4444",
                                text_color="#EF4444",
                                expand=True,
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Row(
                        [
                            _safe_outlined_btn(
                                "🚇 DMRC Metro",
                                lambda e: apply_preset(
                                    "dmrc.metro@axis",
                                    "Delhi Metro DMRC",
                                    "60.00",
                                    "upi://pay?pa=dmrc.metro@axis&pn=Delhi%20Metro&mc=4111&orgid=159002&mode=02",
                                ),
                                border_color="#38BDF8",
                                text_color="#38BDF8",
                                expand=True,
                            ),
                            _safe_outlined_btn(
                                "🆕 Gupta Kirana (Tier 3)",
                                lambda e: apply_preset(
                                    "guptakirana@sbi",
                                    "Gupta Store XYZ",
                                    "340.00",
                                    "upi://pay?pa=guptakirana@sbi&pn=Gupta%20Store&mc=5411&mode=02",
                                ),
                                border_color="#F59E0B",
                                text_color="#F59E0B",
                                expand=True,
                            ),
                        ],
                        spacing=6,
                    ),
                ],
                spacing=8,
            ),
            padding=_pad(12, 12, 12, 12),
            bgcolor="#1E293B",
            border=_border("#38BDF8", 1.2),
            border_radius=10,
        ),
        # --- 2. VPA, PAYEE NAME, AMOUNT & PREFERRED UPI APP FORM ---
        ft.Container(
            content=ft.Column(
                [
                    ft.Row([vpa_tf, name_tf], spacing=8),
                    amt_tf,
                    ft.Text("Select Preferred UPI App:", size=11, color="#94A3B8"),
                    app_chips_row,
                ],
                spacing=8,
            ),
            padding=_pad(12, 12, 12, 12),
            bgcolor="#1E293B",
            border=_border("#334155", 1.0),
            border_radius=10,
        ),
        # --- 3. LIVE PRE-PAYMENT INTELLIGENCE & SIGNED URI INSPECTOR ---
        ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "🔍 Pre-Payment Intelligence & Signed URI Inspector",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color="#F8FAFC",
                    ),
                    preview_tag_txt,
                    preview_anom_txt,
                    ft.Container(
                        content=uri_txt,
                        padding=_pad(8, 8, 8, 8),
                        bgcolor="#0F172A",
                        border=_border("#334155", 1.0),
                        border_radius=6,
                    ),
                ],
                spacing=5,
            ),
            padding=_pad(12, 12, 12, 12),
            bgcolor="#1E293B",
            border=_border("#334155", 1.0),
            border_radius=10,
        ),
        # --- 4. DUAL PAYMENT EXECUTION BUTTONS ---
        ft.Row(
            [
                _safe_btn(
                    "🚀 Launch UPI (Save Pending)",
                    on_launch_pending_click,
                    bgcolor="#F59E0B",
                    text_color="#0B0F19",
                    expand=True,
                ),
                _safe_btn(
                    "⚡ Instant Pay & Verify",
                    on_instant_pay_click,
                    bgcolor="#10B981",
                    text_color="#0B0F19",
                    expand=True,
                ),
            ],
            spacing=8,
        ),
    ]

    return ft.Container(
        expand=True,
        padding=_pad(14, 14, 14, 14),
        content=ft.ListView(controls=controls_list, spacing=10, expand=True),
    )


# ============================================================================
# 3. MANDATORY VALUE-VALIDATING SELF-TEST FOOTER (Rule 4)
# ============================================================================
if __name__ == "__main__":
    ensure_db_ready()

    # 1. Verify signed QR URI builder preserves cryptographic params (mc, sign, orgid)
    sample_qr = "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&sign=MEYCIQC3x...&orgid=159981&mode=02"
    built_uri = build_signed_upi_uri(sample_qr, 250.0)
    assert "mc=5411" in built_uri and "sign=MEYCIQC3x..." in built_uri, "Signed QR params must be preserved!"
    assert "am=250.00" in built_uri and "cu=INR" in built_uri, "Amount and INR currency must be injected!"

    # 2. Verify Flet control tree builds cleanly with page=None
    scanner_ctrl = build_scanner_view(None)
    assert isinstance(scanner_ctrl, ft.Control), "build_scanner_view must return an ft.Control instance!"

    print(f"[PASS] Saurabh S1-03 Scanner View Verified! Signed URI={built_uri}")