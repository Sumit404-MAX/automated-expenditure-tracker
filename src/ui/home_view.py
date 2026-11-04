"""
src/ui/home_view.py
Saurabh Yadav (Frontend UI - Task S1-03 & S1-04 Popup Integration)
Flet 1.0+/0.80+ Dark-Mode Home View:
- Monthly Budget Hero Card + Quick Budget Setup Dialog (Onboarding/Edit)
- Dynamic Financial Health Score Badge (GREEN / YELLOW / RED)
- 2x2 Uniform Action Pill Grid (Scan & Pay, Set Budget, Verify Popup, Export CSV)
- Auto-wires S1-04 show_resume_verification_popup & RESUMED lifecycle listener into main.py
- 1-Tap Pending UPI Transaction Verification Banner + Recent UPI Passbook Feed
"""

import os
import sqlite3
import flet as ft
from src.db.seed_mock_data import DB_FILE
from src.contracts import (
    _try_import,
    create_pending_txn,
    ensure_db_ready,
    export_transactions_csv,
    get_dashboard_summary,
    get_unresolved_pending,
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
    height: float = 38,
) -> ft.Container:
    """Fixed-height single-line interactive pill button (prevents uneven wrapping)."""
    return ft.Container(
        content=ft.Text(
            label,
            size=12,
            weight=ft.FontWeight.BOLD,
            color=text_color,
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
        ),
        bgcolor=bgcolor,
        height=height,
        padding=_pad(12, 0, 12, 0),
        border_radius=10,
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
    height: float = 38,
) -> ft.Container:
    """Fixed-height single-line outlined button (prevents uneven wrapping)."""
    return ft.Container(
        content=ft.Text(
            label,
            size=11,
            weight=ft.FontWeight.W_600,
            color=text_color,
            text_align=ft.TextAlign.CENTER,
            no_wrap=True,
        ),
        bgcolor="#0F172A",
        border=_border(border_color, 1.0),
        height=height,
        padding=_pad(10, 0, 10, 0),
        border_radius=10,
        on_click=on_click_handler,
        expand=expand,
        alignment=getattr(ft.alignment, "center", None),
    )


def _action_tile(
    icon_text: str,
    title: str,
    subtitle: str,
    on_click_handler,
    tile_bg: str = "#1E293B",
    icon_bg: str = "#0F172A",
    border_col: str = "#334155",
    title_col: str = "#FFFFFF",
    sub_col: str = "#94A3B8",
) -> ft.Container:
    """
    Uniform 2x2 Mockup-Style Action Pill Button with left icon badge + right label.
    Fixed height=50 and expand=True guarantees 100% identical button dimensions.
    """
    return ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Text(icon_text, size=14, text_align=ft.TextAlign.CENTER),
                    width=32,
                    height=32,
                    bgcolor=icon_bg,
                    border_radius=9,
                    alignment=getattr(ft.alignment, "center", None),
                ),
                ft.Column(
                    [
                        ft.Text(
                            title,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=title_col,
                            no_wrap=True,
                        ),
                        ft.Text(
                            subtitle,
                            size=9,
                            color=sub_col,
                            no_wrap=True,
                        ),
                    ],
                    spacing=1,
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True,
                ),
            ],
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=50,
        padding=_pad(10, 6, 10, 6),
        bgcolor=tile_bg,
        border=_border(border_col, 1.2),
        border_radius=12,
        on_click=on_click_handler,
        expand=True,
    )


def _notify(page: ft.Page, message: str, bgcolor: str = "#10B981") -> None:
    """Displays a SnackBar across both Flet 1.0+ (page.open) and legacy overlay."""
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
    """Switches bottom navigation tab inside main.py shell when running live."""
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


def _save_monthly_budget(new_budget: float, db_path: str = DB_FILE) -> None:
    """Updates monthly_budget using Anuj's database module if available, else SQLite."""
    live_update = _try_import("src.db.database", "update_monthly_budget")
    if live_update:
        try:
            live_update(new_budget, db_path=db_path)
            return
        except Exception:
            pass
    ensure_db_ready(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE user_profile SET monthly_budget = ?", (float(new_budget),))


# ============================================================================
# 2. PRIMARY VIEW BUILDER: build_home_view(page, summary) -> ft.Control
# ============================================================================
def build_home_view(page: ft.Page, summary: dict = None) -> ft.Control:
    """
    Builds the Sprint 1 Home Screen & Monthly Budget Onboarding UI,
    and connects S1-04 1-Tap Resume Verification Popup into main.py.
    """
    ensure_db_ready()
    root_holder = ft.Container(expand=True, padding=_pad(14, 14, 14, 14))

    popup_fn = _try_import("src.ui.popups", "show_resume_verification_popup")
    listener_fn = _try_import("src.ui.popups", "register_lifecycle_resume_listener")

    def open_s104_popup(target_pending: dict = None) -> None:
        """Opens the S1-04 1-Tap Verification Popup inside main.py."""
        if page is None or not callable(popup_fn):
            _notify(page, "src/ui/popups.py not found!", "#EF4444")
            return
        rows = get_unresolved_pending()
        if not rows and target_pending is None:
            create_pending_txn(
                250.0,
                "chaipoint@icici",
                "Chai Point",
                "upi://pay?pa=chaipoint@icici&pn=Chai%20Point&mc=5411&am=250.00&cu=INR",
            )
            rows = get_unresolved_pending()
        popup_fn(
            page,
            target_pending or (rows[0] if rows else None),
            on_resolved=lambda _: render_home_content(get_dashboard_summary()),
        )

    if page is not None and callable(listener_fn):
        listener_fn(page, on_resolved=lambda _: render_home_content(get_dashboard_summary()))

    def render_home_content(curr_summary: dict = None) -> None:
        data = curr_summary if isinstance(curr_summary, dict) else get_dashboard_summary()

        spent = float(data.get("spent_this_month", data.get("total_spent", 0.0)))
        budget = float(data.get("monthly_budget", 12000.0))
        remaining = float(data.get("remaining_budget", max(0.0, budget - spent)))
        daily_safe = float(data.get("daily_safe_spend", 0.0))
        txn_count = int(data.get("transaction_count", 0))
        anomaly_count = int(data.get("anomaly_count", 0))
        health_score = int(data.get("health_score", 100))
        health_status = str(data.get("health_status", "GREEN"))
        health_color = str(data.get("health_color", "#10B981"))
        recent_txns = list(data.get("recent_transactions", []))

        pending_list = get_unresolved_pending()
        ratio = min(1.0, max(0.0, spent / max(1.0, budget)))

        controls_list = []

        # --- 0. ACTIVE LIVE MODULE BANNER ---
        controls_list.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            "🟢 [LIVE MODULE] Saurabh Yadav • Home & Popup UI (S1-03 / S1-04)",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#10B981",
                            expand=True,
                        ),
                        ft.Text(f"{txn_count} Txns", size=10, color="#94A3B8"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=_pad(10, 6, 10, 6),
                bgcolor="#0F172A",
                border=_border("#10B981", 1.0),
                border_radius=8,
            )
        )

        # --- 1. MONTHLY BUDGET ONBOARDING / EDIT DIALOG ---
        def open_budget_dialog(e):
            if page is None:
                return
            budget_tf = ft.TextField(
                label="Monthly Budget Limit (INR)",
                value=f"{budget:.0f}",
                text_size=14,
                color="#FFFFFF",
                bgcolor="#0B0F19",
                border_color="#38BDF8",
            )

            def close_dlg(dlg_obj):
                if hasattr(page, "close"):
                    page.close(dlg_obj)
                else:
                    dlg_obj.open = False
                    page.update()

            def on_save_budget(ev):
                try:
                    val = float(budget_tf.value.strip())
                    if val <= 0:
                        raise ValueError
                except ValueError:
                    _notify(page, "Please enter a valid budget amount > Rs. 0", "#EF4444")
                    return
                _save_monthly_budget(val)
                close_dlg(dlg)
                render_home_content(get_dashboard_summary())
                _notify(page, f"Monthly budget updated to Rs. {val:,.0f}!", "#10B981")

            dlg = ft.AlertDialog(
                bgcolor="#1E293B",
                title=ft.Text("🎯 Set Monthly UPI Budget", size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                content=ft.Container(
                    width=320,
                    content=ft.Column(
                        [
                            ft.Text(
                                "Configure your monthly spending cap for Health Score & daily safe-spend tracking:",
                                size=11,
                                color="#94A3B8",
                            ),
                            budget_tf,
                        ],
                        spacing=10,
                        tight=True,
                    ),
                ),
                actions=[
                    _safe_outlined_btn("Cancel", lambda ev: close_dlg(dlg)),
                    _safe_btn("Save Budget", on_save_budget, bgcolor="#10B981", text_color="#0B0F19"),
                ],
            )
            if hasattr(page, "open"):
                page.open(dlg)
            else:
                page.overlay.append(dlg)
                dlg.open = True
                page.update()

        # --- 2. HERO WALLET & MONTHLY BUDGET CARD ---
        controls_list.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        ft.Text("Hi, Saurabh 👋", size=15, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                        ft.Text("saurabh@okaxis  •  UPI 2.0 Verified", size=11, color="#94A3B8"),
                                    ],
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        f"Health {health_score}/100 ({health_status})",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color="#0B0F19",
                                    ),
                                    bgcolor=health_color,
                                    padding=_pad(8, 4, 8, 4),
                                    border_radius=6,
                                ),
                            ]
                        ),
                        ft.Container(height=2),
                        ft.Row(
                            [
                                ft.Text("TOTAL SPENT THIS MONTH", size=10, weight=ft.FontWeight.BOLD, color="#38BDF8", expand=True),
                                ft.Text(f"{ratio * 100:.0f}% of budget", size=10, color="#94A3B8"),
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Text(f"Rs. {spent:,.2f}", size=26, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                ft.Text(f"/ Rs. {budget:,.0f}", size=13, color="#94A3B8"),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                        ft.ProgressBar(value=ratio, color=health_color, bgcolor="#0F172A", height=8),
                        ft.Row(
                            [
                                ft.Text(f"Left: Rs. {remaining:,.0f}", size=11, weight=ft.FontWeight.W_600, color="#10B981"),
                                ft.Text(f"Safe Pace: Rs. {daily_safe:,.0f}/day", size=11, color="#E2E8F0"),
                                ft.Text(
                                    f"Spikes: {anomaly_count}",
                                    size=11,
                                    weight=ft.FontWeight.BOLD,
                                    color="#EF4444" if anomaly_count > 0 else "#94A3B8",
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=6,
                ),
                padding=_pad(14, 14, 14, 14),
                bgcolor="#1E293B",
                border=_border("#334155", 1.2),
                border_radius=14,
            )
        )

        # --- 3. 2x2 UNIFORM ACTION PILL GRID (Matches UI Reference Mockup) ---
        def on_export_csv(e):
            path = export_transactions_csv()
            _notify(page, f"CSV Exported: {os.path.basename(path)}", "#10B981")

        controls_list.append(
            ft.Column(
                [
                    ft.Row(
                        [
                            _action_tile(
                                "📷",
                                "Scan & Pay",
                                "QR / UPI Intent",
                                lambda e: _switch_main_tab(page, 1),
                                tile_bg="#2563EB",
                                icon_bg="#1D4ED8",
                                border_col="#3B82F6",
                                title_col="#FFFFFF",
                                sub_col="#DBEAFE",
                            ),
                            _action_tile(
                                "🎯",
                                "Edit Budget",
                                f"Cap: Rs.{budget:,.0f}",
                                open_budget_dialog,
                                tile_bg="#1E293B",
                                icon_bg="#0F172A",
                                border_col="#38BDF8",
                                title_col="#38BDF8",
                                sub_col="#94A3B8",
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            _action_tile(
                                "⚡",
                                "Verify Popup",
                                f"{len(pending_list)} Pending Intent",
                                lambda e: open_s104_popup(),
                                tile_bg="#1E293B",
                                icon_bg="#0F172A",
                                border_col="#F59E0B",
                                title_col="#F59E0B",
                                sub_col="#94A3B8",
                            ),
                            _action_tile(
                                "📥",
                                "Export CSV",
                                f"{txn_count} Ledger Rows",
                                on_export_csv,
                                tile_bg="#1E293B",
                                icon_bg="#0F172A",
                                border_col="#475569",
                                title_col="#E2E8F0",
                                sub_col="#94A3B8",
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=8,
            )
        )

        # --- 4. 1-TAP IN-FLIGHT PENDING TRANSACTION VERIFICATION BANNER ---
        if pending_list:
            p = pending_list[0]
            p_id = p.get("internal_id")
            p_amt = float(p.get("amount", 0.0))
            p_name = str(p.get("payee_name", "Merchant"))
            p_vpa = str(p.get("payee_vpa", "merchant@upi"))

            def on_confirm_paid(e, pid=p_id, amt=p_amt, name=p_name):
                resolve_pending_txn(pid, status="RESOLVED", notes="1-Tap Home Verified")
                render_home_content(get_dashboard_summary())
                _notify(page, f"Verified & logged Rs. {amt:,.0f} paid to {name}!", "#10B981")

            def on_cancel_pending(e, pid=p_id):
                resolve_pending_txn(pid, status="CANCELLED", notes="Cancelled by User")
                render_home_content(get_dashboard_summary())
                _notify(page, f"Pending intent #{pid} marked as Cancelled.", "#F59E0B")

            controls_list.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "⚡ 1-Tap Pending UPI Verification",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color="#F59E0B",
                                        expand=True,
                                    ),
                                    ft.Text(
                                        f"#{p_id} ({len(pending_list)} pending)",
                                        size=10,
                                        color="#94A3B8",
                                    ),
                                ]
                            ),
                            ft.Text(
                                f"Did your UPI payment of Rs. {p_amt:,.2f} to {p_name} ({p_vpa}) succeed?",
                                size=12,
                                color="#FFFFFF",
                            ),
                            ft.Row(
                                [
                                    _safe_btn(
                                        "✓ Confirm Paid",
                                        on_confirm_paid,
                                        bgcolor="#10B981",
                                        text_color="#0B0F19",
                                        expand=True,
                                    ),
                                    _safe_outlined_btn(
                                        "✕ Cancel",
                                        on_cancel_pending,
                                        border_color="#EF4444",
                                        text_color="#EF4444",
                                        expand=True,
                                    ),
                                    _safe_outlined_btn(
                                        "🔔 Popup",
                                        lambda e, row=p: open_s104_popup(row),
                                        border_color="#F59E0B",
                                        text_color="#F59E0B",
                                        expand=True,
                                    ),
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=6,
                    ),
                    padding=_pad(12, 12, 12, 12),
                    bgcolor="#1E293B",
                    border=_border("#F59E0B", 1.5),
                    border_radius=12,
                )
            )

        # --- 5. RECENT UPI PASSBOOK TRANSACTIONS FEED ---
        controls_list.append(
            ft.Row(
                [
                    ft.Text("Recent Transactions", size=14, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                    ft.Text(f"Showing {len(recent_txns)} of {txn_count}", size=11, color="#94A3B8"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

        for txn in recent_txns:
            t_name = str(txn.get("name", "Merchant"))
            t_vpa = str(txn.get("vpa", "merchant@upi"))
            t_amt = float(txn.get("amount", 0.0))
            t_cat = str(txn.get("category") or "Uncategorized")
            t_date = str(txn.get("date", ""))[:10]
            is_anom = bool(txn.get("anomaly", False))

            anom_chip = (
                ft.Container(
                    content=ft.Text("⚠️ Z-Spike", size=9, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                    bgcolor="#EF4444",
                    padding=_pad(5, 2, 5, 2),
                    border_radius=4,
                )
                if is_anom
                else ft.Container()
            )

            controls_list.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                content=ft.Text(
                                    t_name[:1].upper() if t_name else "U",
                                    size=13,
                                    weight=ft.FontWeight.BOLD,
                                    color="#38BDF8",
                                ),
                                width=38,
                                height=38,
                                bgcolor="#0F172A",
                                border_radius=19,
                                border=_border("#334155", 1.0),
                                alignment=getattr(ft.alignment, "center", None),
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Text(t_name, size=13, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
                                            anom_chip,
                                        ],
                                        spacing=6,
                                    ),
                                    ft.Text(f"{t_cat} • {t_vpa} • {t_date}", size=10, color="#94A3B8"),
                                ],
                                spacing=2,
                                expand=True,
                            ),
                            ft.Text(
                                f"-Rs. {t_amt:,.0f}",
                                size=13,
                                weight=ft.FontWeight.BOLD,
                                color="#EF4444" if is_anom else "#F8FAFC",
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=_pad(10, 9, 10, 9),
                    bgcolor="#1E293B",
                    border=_border("#EF4444" if is_anom else "#334155", 1.0),
                    border_radius=10,
                )
            )

        root_holder.content = ft.ListView(controls=controls_list, spacing=10, expand=True)
        if page is not None:
            page.update()

        if page is not None and pending_list and callable(popup_fn):
            latest_id = pending_list[0].get("internal_id")
            if getattr(page, "_last_popped_pending_id", None) != latest_id:
                setattr(page, "_last_popped_pending_id", latest_id)
                open_s104_popup(pending_list[0])

    render_home_content(summary)
    return root_holder


# ============================================================================
# 3. MANDATORY VALUE-VALIDATING SELF-TEST FOOTER (Rule 4)
# ============================================================================
if __name__ == "__main__":
    ensure_db_ready()
    live_summary = get_dashboard_summary()

    assert live_summary.get("spent_this_month", 0.0) > 0.0, "spent_this_month must be > 0 from tracker_dev.db!"
    assert live_summary.get("monthly_budget", 0.0) > 1.0, "monthly_budget must be > 1.0!"
    assert len(live_summary.get("recent_transactions", [])) > 0, "recent_transactions must not be empty!"

    view_ctrl = build_home_view(None, live_summary)
    assert isinstance(view_ctrl, ft.Control), "build_home_view must return an ft.Control instance!"

    print(
        f"[PASS] Saurabh S1-03 Home View Verified! "
        f"Spent=Rs.{live_summary['spent_this_month']:,.2f} / Budget=Rs.{live_summary['monthly_budget']:,.0f} "
        f"| Health={live_summary['health_score']}/100 | Recent={len(live_summary['recent_transactions'])} txns"
    )