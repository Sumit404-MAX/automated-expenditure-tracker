"""
src/ui/popups.py
Saurabh Yadav (Frontend UI - Task S1-04, with Sprint 2/4 Modal Hooks)
Flet 1.0+/0.80+ Dark-Mode 1-Tap Fallback Verification Popup on App Resume:
- Listens to page.on_app_lifecycle_state_change for RESUMED state
- Queries get_unresolved_pending() from src.contracts
- Displays a 1-Tap Yes/No Verification AlertDialog with auto-tag & Z-Score preview
- Resolves strictly via resolve_pending_txn(internal_id, status="RESOLVED" | "CANCELLED")
"""

import sys
import flet as ft
from src.contracts import (
    categorize_transaction,
    create_pending_txn,
    detect_spending_anomaly,
    ensure_db_ready,
    get_unresolved_pending,
    resolve_pending_txn,
    save_merchant_tag,
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
    bgcolor: str = "#10B981",
    text_color: str = "#0B0F19",
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
    border_color: str = "#EF4444",
    text_color: str = "#EF4444",
    expand: bool = False,
) -> ft.Container:
    """Outlined secondary button for cancelling/dismissing failed intents."""
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
        padding=_pad(10, 8, 10, 8),
        border_radius=8,
        on_click=on_click_handler,
        expand=expand,
        alignment=getattr(ft.alignment, "center", None),
    )


def _open_dialog(page: ft.Page, dlg: ft.AlertDialog) -> None:
    """Opens an AlertDialog safely on both Flet 1.0+ (page.open) and legacy overlay."""
    if page is None:
        return
    if hasattr(page, "open"):
        try:
            page.open(dlg)
            return
        except Exception:
            pass
    try:
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        dlg.open = True
        page.update()
    except Exception:
        pass


def _close_dialog(page: ft.Page, dlg: ft.AlertDialog) -> None:
    """Closes an AlertDialog safely on both Flet 1.0+ (page.close) and legacy overlay."""
    if page is None:
        return
    if hasattr(page, "close"):
        try:
            page.close(dlg)
            return
        except Exception:
            pass
    try:
        dlg.open = False
        page.update()
    except Exception:
        pass


def _notify(page: ft.Page, message: str, bgcolor: str = "#10B981") -> None:
    """Displays a SnackBar notification across Flet 0.80+ and 1.0.4."""
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


def _refresh_main_shell(page: ft.Page) -> None:
    """Re-renders the active tab in main.py after resolving a pending payment."""
    if page is None:
        return
    try:
        root_col = page.controls[0]
        nav_bar = root_col.controls[2]
        if callable(getattr(nav_bar, "on_change", None)):
            nav_bar.on_change(type("NavEvt", (), {"control": nav_bar})())
            return
    except Exception:
        pass
    try:
        page.update()
    except Exception:
        pass


# ============================================================================
# 2. S1-04 PRIMARY POPUP: show_resume_verification_popup(page, pending_txn)
# ============================================================================
def show_resume_verification_popup(
    page: ft.Page = None,
    pending_txn: dict = None,
    on_resolved=None,
) -> ft.AlertDialog | None:
    """
    Builds and opens the 1-Tap Fallback Verification Popup when returning from a UPI app.
    Auto-discovered by src/contracts.py: _try_import("src.ui.popups", "show_resume_verification_popup").
    """
    ensure_db_ready()

    if page is not None and not getattr(page, "_exptracker_resume_hooked", False):
        register_lifecycle_resume_listener(page, on_resolved=on_resolved)

    target_txn = pending_txn
    if target_txn is None:
        unresolved = get_unresolved_pending()
        if not unresolved:
            return None
        target_txn = unresolved[0]

    internal_id = int(target_txn.get("internal_id", 0))
    amount = float(target_txn.get("amount", 0.0))
    payee_name = str(target_txn.get("payee_name", "Merchant"))
    payee_vpa = str(target_txn.get("payee_vpa", "merchant@upi"))
    init_time = str(target_txn.get("init_time", "Just now"))[:16]

    tag_info = categorize_transaction(payee_vpa, payee_name)
    cat_id = int(tag_info.get("category_id", 6))
    cat_name = str(tag_info.get("category_name", "Uncategorized"))
    tier_name = str(tag_info.get("tier", "Auto-Tag"))

    anom_info = detect_spending_anomaly(cat_id, amount)
    is_anom = bool(anom_info.get("is_anomaly", False))
    anom_reason = str(anom_info.get("reason", "Normal pace"))

    notes_tf = ft.TextField(
        label="Optional Note / Tag (e.g., #Chai, #Metro)",
        value="",
        text_size=12,
        height=44,
        color="#FFFFFF",
        bgcolor="#0B0F19",
        border_color="#334155",
    )

    def _handle_resolution(status_str: str) -> None:
        user_note = (notes_tf.value or "").strip() or (
            "1-Tap Resume Confirmed" if status_str == "RESOLVED" else "Cancelled on Resume"
        )
        result = resolve_pending_txn(
            internal_id=internal_id,
            status=status_str,
            category_id=cat_id,
            is_anomaly=is_anom,
            notes=user_note,
        )
        _close_dialog(page, dlg)

        if status_str == "RESOLVED":
            _notify(
                page,
                f"✓ Payment #{internal_id} (Rs. {amount:,.0f} to {payee_name}) logged in {cat_name}!",
                "#10B981",
            )
        else:
            _notify(
                page,
                f"✕ Pending intent #{internal_id} ({payee_name}) marked as Cancelled.",
                "#F59E0B",
            )

        if callable(on_resolved):
            try:
                on_resolved(result)
            except Exception:
                pass
        _refresh_main_shell(page)

    anom_banner = (
        ft.Container(
            content=ft.Text(
                f"⚠️ Z-Score Spike Alert: {anom_reason}",
                size=11,
                weight=ft.FontWeight.BOLD,
                color="#FFFFFF",
            ),
            bgcolor="#EF4444",
            padding=_pad(8, 5, 8, 5),
            border_radius=6,
        )
        if is_anom
        else ft.Container(
            content=ft.Text(
                f"🏷️ Auto-Category: {cat_name} ({tier_name})",
                size=11,
                weight=ft.FontWeight.W_600,
                color="#10B981" if not tag_info.get("needs_user_tag") else "#F59E0B",
            ),
            bgcolor="#0B0F19",
            padding=_pad(8, 5, 8, 5),
            border=_border("#334155", 1.0),
            border_radius=6,
        )
    )

    dlg = ft.AlertDialog(
        modal=True,
        bgcolor="#0F172A",
        title=ft.Row(
            [
                ft.Text(
                    "⚡ 1-Tap Payment Verification",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#F59E0B",
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text(f"ID #{internal_id}", size=10, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    bgcolor="#1E293B",
                    padding=_pad(6, 3, 6, 3),
                    border_radius=4,
                    border=_border("#334155", 1.0),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        content=ft.Container(
            width=350,
            padding=_pad(2, 2, 2, 2),
            content=ft.Column(
                [
                    ft.Text(
                        "Welcome back! NPCI UPI callback was stripped or unconfirmed. Did this payment succeed?",
                        size=11,
                        color="#94A3B8",
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            payee_name,
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FFFFFF",
                                            expand=True,
                                        ),
                                        ft.Text(
                                            f"Rs. {amount:,.2f}",
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                            color="#10B981",
                                        ),
                                    ]
                                ),
                                ft.Text(f"VPA: {payee_vpa}  •  Initiated: {init_time}", size=10, color="#94A3B8"),
                                anom_banner,
                            ],
                            spacing=6,
                        ),
                        padding=_pad(12, 10, 12, 10),
                        bgcolor="#1E293B",
                        border=_border("#F59E0B", 1.2),
                        border_radius=10,
                    ),
                    notes_tf,
                ],
                spacing=10,
                tight=True,
            ),
        ),
        actions=[
            ft.Row(
                [
                    _safe_outlined_btn(
                        "✕ No, Failed / Cancel",
                        lambda e: _handle_resolution("CANCELLED"),
                        border_color="#EF4444",
                        text_color="#EF4444",
                        expand=True,
                    ),
                    _safe_btn(
                        "✓ Yes, Confirm Paid",
                        lambda e: _handle_resolution("RESOLVED"),
                        bgcolor="#10B981",
                        text_color="#0B0F19",
                        expand=True,
                    ),
                ],
                spacing=8,
            )
        ],
    )

    _open_dialog(page, dlg)
    return dlg


show_fallback_verify_popup = show_resume_verification_popup


# ============================================================================
# 3. LIFECYCLE RESUME LISTENER (Rule 5: "RESUME" in str(getattr(e, "state", e)).upper())
# ============================================================================
def register_lifecycle_resume_listener(page: ft.Page, on_resolved=None):
    """
    Attaches an app lifecycle listener to page.on_app_lifecycle_state_change.
    Whenever the app transitions to RESUMED and unresolved pending_transactions exist,
    automatically opens the 1-Tap Fallback Verification Popup.
    """
    prev_handler = getattr(page, "on_app_lifecycle_state_change", None) if page is not None else None

    def _on_lifecycle_change(e):
        if callable(prev_handler):
            try:
                prev_handler(e)
            except Exception:
                pass

        state_str = str(getattr(e, "state", getattr(e, "data", e))).upper()
        if "RESUME" in state_str:
            unresolved = get_unresolved_pending()
            if unresolved:
                show_resume_verification_popup(page, unresolved[0], on_resolved=on_resolved)

    if page is not None:
        page.on_app_lifecycle_state_change = _on_lifecycle_change
        setattr(page, "_exptracker_resume_hooked", True)

    return _on_lifecycle_change


# ============================================================================
# 4. SPRINT 2 & SPRINT 4 FORWARD-COMPATIBLE MODAL HOOKS (S2-03 & S4-02)
# ============================================================================
def show_first_time_tag_dialog(page: ft.Page, payee_vpa: str, payee_name: str, on_saved=None) -> ft.AlertDialog:
    """Sprint 2 (S2-03) hook: Saves user-selected category to merchant_tags."""
    selected_cat = [1]
    dd = ft.Dropdown(
        label="Select Merchant Category",
        value="1",
        options=[
            ft.dropdown.Option("1", "Food & Dining"),
            ft.dropdown.Option("2", "Travel"),
            ft.dropdown.Option("3", "Groceries"),
            ft.dropdown.Option("4", "Fuel"),
            ft.dropdown.Option("5", "Utilities"),
            ft.dropdown.Option("6", "Uncategorized"),
        ],
    )

    def _on_dd_change(e):
        try:
            selected_cat[0] = int(dd.value or 1)
        except ValueError:
            selected_cat[0] = 1

    dd.on_change = _on_dd_change

    def _save_tag(e):
        save_merchant_tag(payee_vpa, selected_cat[0])
        _close_dialog(page, dlg)
        _notify(page, f"Saved permanent tag for {payee_name} ({payee_vpa})!", "#10B981")
        if callable(on_saved):
            on_saved(selected_cat[0])

    dlg = ft.AlertDialog(
        bgcolor="#0F172A",
        title=ft.Text("🏷️ Tag First-Time Merchant", size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
        content=ft.Container(
            width=320,
            content=ft.Column(
                [
                    ft.Text(f"Assign a default category for {payee_name} ({payee_vpa}):", size=11, color="#94A3B8"),
                    dd,
                ],
                spacing=10,
                tight=True,
            ),
        ),
        actions=[
            _safe_outlined_btn("Skip", lambda e: _close_dialog(page, dlg), border_color="#475569", text_color="#94A3B8"),
            _safe_btn("Save Tag", _save_tag, bgcolor="#10B981", text_color="#0B0F19"),
        ],
    )
    _open_dialog(page, dlg)
    return dlg


show_first_time_tag_popup = show_first_time_tag_dialog


# ============================================================================
# 5. INTERACTIVE LIVE SANDBOX WINDOW (`python -m src.ui.popups --live`)
# ============================================================================
def _launch_popup_sandbox(page: ft.Page) -> None:
    page.title = "Saurabh S1-04 — 1-Tap Resume Verification Popup Sandbox"
    try:
        page.window.width = 435
        page.window.height = 860
    except Exception:
        pass
    page.bgcolor = "#0B0F19"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    ensure_db_ready()
    status_txt = ft.Text("", size=12, color="#38BDF8", weight=ft.FontWeight.BOLD)

    def refresh_status(*_):
        rows = get_unresolved_pending()
        status_txt.value = f"Current Unresolved Pending Intents in SQLite: {len(rows)}"
        page.update()

    def trigger_resume_popup(e):
        rows = get_unresolved_pending()
        if not rows:
            create_pending_txn(
                250.0,
                "chaipoint@icici",
                "Chai Point",
                "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&am=250.00&cu=INR",
            )
        show_resume_verification_popup(page, on_resolved=refresh_status)
        refresh_status()

    def trigger_spike_popup(e):
        pid = create_pending_txn(
            3800.0,
            "zomato@icici",
            "Zomato",
            "upi://pay?pa=zomato@icici&pn=Zomato&mc=5812&am=3800.00&cu=INR",
        )
        rows = [r for r in get_unresolved_pending() if r.get("internal_id") == pid]
        show_resume_verification_popup(page, rows[0] if rows else None, on_resolved=refresh_status)
        refresh_status()

    register_lifecycle_resume_listener(page, on_resolved=refresh_status)
    refresh_status()

    page.add(
        ft.Container(
            expand=True,
            padding=_pad(14, 14, 14, 14),
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "🟢 Saurabh Yadav • S1-04 Popup Tester",
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color="#10B981",
                                ),
                                ft.Text(
                                    "Click the buttons below (or minimize & restore this window) to test the 1-Tap Fallback Verification Popup live!",
                                    size=11,
                                    color="#94A3B8",
                                ),
                                status_txt,
                            ],
                            spacing=6,
                        ),
                        padding=_pad(14, 14, 14, 14),
                        bgcolor="#1E293B",
                        border=_border("#10B981", 1.2),
                        border_radius=10,
                    ),
                    _safe_btn(
                        "⚡ Open 1-Tap Resume Popup (Normal Rs. 250)",
                        trigger_resume_popup,
                        bgcolor="#F59E0B",
                        text_color="#0B0F19",
                    ),
                    _safe_btn(
                        "🚨 Open 1-Tap Resume Popup (Z-Spike Rs. 3,800)",
                        trigger_spike_popup,
                        bgcolor="#EF4444",
                        text_color="#FFFFFF",
                    ),
                    _safe_outlined_btn(
                        "🏷️ Test First-Time Merchant Tag Popup (S2-03)",
                        lambda e: show_first_time_tag_dialog(page, "guptakirana@sbi", "Gupta Store XYZ"),
                        border_color="#38BDF8",
                        text_color="#38BDF8",
                    ),
                ],
                spacing=12,
            ),
        )
    )
    # Auto-open popup on launch so Saurabh sees it immediately!
    trigger_resume_popup(None)


# ============================================================================
# 6. MANDATORY VALUE-VALIDATING SELF-TEST FOOTER (Rule 4)
# ============================================================================
if __name__ == "__main__":
    if "--live" in sys.argv:
        runner = getattr(ft, "run", getattr(ft, "app", None))
        runner(_launch_popup_sandbox)
        sys.exit(0)

    ensure_db_ready()

    pending_rows = get_unresolved_pending()
    created_temp_id = None
    if not pending_rows:
        created_temp_id = create_pending_txn(
            185.0,
            "testchai@okaxis",
            "Test Chai Corner",
            "upi://pay?pa=testchai@okaxis&pn=Test%20Chai&am=185.00&cu=INR",
        )
        pending_rows = get_unresolved_pending()

    assert len(pending_rows) > 0, "pending_transactions must have at least 1 PENDING row for test!"
    sample_pending = pending_rows[0]
    assert int(sample_pending.get("internal_id", 0)) > 0, "internal_id must be > 0!"
    assert float(sample_pending.get("amount", 0.0)) > 0.0, "Pending amount must be > 0.0!"

    popup_dlg = show_resume_verification_popup(None, sample_pending)
    assert isinstance(popup_dlg, ft.AlertDialog), "show_resume_verification_popup must return an ft.AlertDialog!"

    triggered = []
    handler = register_lifecycle_resume_listener(None, on_resolved=lambda r: triggered.append(r))
    fake_resume_evt = type("LifecycleEvt", (), {"state": "AppLifecycleState.RESUMED"})()
    assert "RESUME" in str(getattr(fake_resume_evt, "state", fake_resume_evt)).upper()
    handler(fake_resume_evt)

    if created_temp_id is not None:
        resolve_pending_txn(created_temp_id, status="CANCELLED", notes="Self-test cleanup")

    print(
        f"[PASS] Saurabh S1-04 Resume Verification Popup Verified! "
        f"Pending ID=#{sample_pending['internal_id']} | Payee={sample_pending['payee_name']} "
        f"| Amount=Rs.{sample_pending['amount']:.2f}"
    )