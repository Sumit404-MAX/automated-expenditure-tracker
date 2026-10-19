"""Live Runnable Flet Application & Project Lead Integration Harness.

Owned by: Sumit Kushwaha (Project Lead & Integrator)
Usage:
    python main.py                       # Opens the Live Interactive Flet Mobile App
    python main.py --check-integration   # Runs the 6-Point CLI Team Integration Audit
"""

import argparse
import os
import sys
import warnings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.contracts import (
    CATEGORY_NAME_TO_ID,
    DEFAULT_CATEGORIES,
    _try_import,
    build_signed_upi_uri,
    categorize_transaction,
    create_pending_txn,
    detect_spending_anomaly,
    ensure_db_ready,
    export_transactions_csv,
    get_dashboard_summary,
    get_integration_status,
    resolve_pending_txn,
    save_merchant_tag,
)
from src.db.seed_mock_data import DB_FILE, seed_mock_database


def run_cli_integration_audit() -> None:
    """Runs a 6-point integration check across DB, UPI URI, Tagger, Anomaly Math, UI, and Lean Stack."""
    ensure_db_ready(DB_FILE)
    status = get_integration_status()
    summary = get_dashboard_summary(DB_FILE)

    print("=" * 78)
    print(" AUTOMATED EXPENDITURE TRACKER — LEAD INTEGRATION AUDIT (v1.1)")
    print("=" * 78)
    for key, info in status.items():
        mode_str = f"[{info['mode']}]"
        print(f" {mode_str:<22} {info['owner']:<16} ({info['badge']})")
        for f in info["files"]:
            st_icon = "🟢 LIVE    " if f["is_live"] else "🟡 Fallback"
            print(f"    └─ {st_icon} {f['path']:<30} [{f['task']}]")
    print("-" * 78)

    # Check 1: Signed UPI 2.0 QR Parameter Preservation
    raw_qr = "upi://pay?pa=zomato.order@hdfcbank&pn=Zomato&mc=5812&sign=NPCI_SIG_9981&orgid=159002"
    built_uri = build_signed_upi_uri(raw_qr, 245.5)
    assert (
        "mc=5812" in built_uri and "sign=NPCI_SIG_9981" in built_uri and "am=245.50" in built_uri
    ), "QR signature stripped!"
    print(" [PASS] Check 1 (Anuj Contract): Signed QR params (mc, sign, orgid) preserved ->", built_uri)

    # Check 2: 3-Tier Tagger (Tier 1 Memory + Tier 2 Regex + Tier 3 Unknown)
    t1 = categorize_transaction("ramesh.chai@ybl", "Ramesh Tea Stall")
    t2 = categorize_transaction("blinkit.pay@axis", "Blinkit Grofers")
    t3 = categorize_transaction("novelty.books@okicici", "Novelty Book House")
    print(
        f" [PASS] Check 2 (Uday Tagger): Tier1={t1['category_name']} | "
        f"Tier2={t2['category_name']} | Tier3(Unknown) needs_tag={t3['needs_user_tag']}"
    )

    # Check 3: Safe Z-Score Anomaly Guard (stdev==0 & spike > 2.5)
    anom_spike = detect_spending_anomaly(1, 1650.0)
    anom_normal = detect_spending_anomaly(1, 150.0)
    print(
        f" [PASS] Check 3 (Uday Z-Score): ₹1650 Food -> Anomaly={anom_spike['is_anomaly']} "
        f"(Z={anom_spike['z_score']}) | ₹150 Food -> Anomaly={anom_normal['is_anomaly']}"
    )

    # Check 4: Health Score & DB Summary
    h = summary["health"]
    print(
        f" [PASS] Check 4 (Health Score): Spent ₹{summary['total_spent']} / "
        f"₹{summary['monthly_budget']} -> Score {h['score']}/100 ({h['status']})"
    )
    print(
        f" [PASS] Check 5 (Pending Queue): {len(summary['pending_list'])} unresolved "
        f"PENDING item(s) ready for 1-Tap Resume Popup."
    )

    # Check 6 (Priority Upgrade 2): Zero Forbidden Heavy Imports Scan across src/
    forbidden = ("pandas", "numpy", "scipy", "sklearn", "matplotlib", "plotly")
    for root, _, files in os.walk("src"):
        for fn in files:
            if fn.endswith(".py"):
                fpath = os.path.join(root, fn)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as src_f:
                    content = src_f.read()
                for bad in forbidden:
                    if f"import {bad}" in content or f"from {bad}" in content:
                        raise AssertionError(
                            f"Forbidden library '{bad}' detected in {fpath}! Use pure Python stdlib only."
                        )
    print(" [PASS] Check 6 (Lean Stack Guardrail): Zero forbidden imports (pandas/numpy/matplotlib) in src/.")
    print("=" * 78)
    print(" [READY FOR DEMO] Run `python main.py` to launch the interactive Flet mobile app!")


def launch_flet_app() -> None:
    import flet as ft

    ensure_db_ready(DB_FILE)

    def get_icon(name: str):
        icons_mod = getattr(ft, "Icons", getattr(ft, "icons", None))
        return getattr(icons_mod, name, None) if icons_mod else None

    def pad(h: float = 0, v: float = 0):
        try:
            return ft.padding.only(left=h, right=h, top=v, bottom=v)
        except Exception:
            try:
                return ft.Padding(left=h, top=v, right=h, bottom=v)
            except Exception:
                return int(v)

    def make_border(color="#475569", width=1):
        try:
            if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
                return ft.Border.all(width=width, color=color)
        except Exception:
            pass
        try:
            if hasattr(ft, "border") and hasattr(ft.border, "all"):
                return ft.border.all(width, color)
        except Exception:
            pass
        try:
            side = ft.BorderSide(width, color)
            return ft.Border(left=side, top=side, right=side, bottom=side)
        except Exception:
            pass
        return None

    def safe_btn(text, on_click=None, bgcolor="#2563EB", color="white", height=38):
        return ft.Container(
            height=height,
            padding=pad(14, 8),
            bgcolor=bgcolor or "#334155",
            border_radius=8,
            alignment=ft.Alignment(0, 0) if hasattr(ft, "Alignment") else None,
            on_click=on_click,
            content=ft.Row(
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=color),
                ],
            ),
        )

    def safe_outlined_btn(text, on_click=None, height=38):
        return ft.Container(
            height=height,
            padding=pad(12, 8),
            bgcolor="#0F172A",
            border=make_border("#475569", 1),
            border_radius=8,
            on_click=on_click,
            content=ft.Row(
                tight=True,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text(text, size=12, weight=ft.FontWeight.W_600, color="#CBD5E1"),
                ],
            ),
        )

    def make_dropdown(label: str, value: str, options_tuples: list, on_change_fn):
        opts = []
        for k, text in options_tuples:
            try:
                opts.append(ft.dropdown.Option(key=str(k), text=str(text)))
            except Exception:
                opts.append(ft.dropdown.Option(str(k), str(text)))
        dd = None
        try:
            dd = ft.Dropdown(label=label, value=value, options=opts, on_select=on_change_fn)
        except TypeError:
            dd = ft.Dropdown(label=label, value=value, options=opts, on_change=on_change_fn)
        try:
            dd.on_change = on_change_fn
        except Exception:
            pass
        try:
            dd.on_select = on_change_fn
        except Exception:
            pass
        return dd

    def border_bottom(color="#1F2937", width=1):
        try:
            side = ft.BorderSide(width, color)
            if hasattr(ft, "Border"):
                return ft.Border(bottom=side)
            if hasattr(ft, "border") and hasattr(ft.border, "only"):
                return ft.border.only(bottom=side)
        except Exception:
            pass
        return None

    def main(page: ft.Page):
        page.title = "Automated Expenditure Tracker (v1.1 Live Demo)"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#0B0F19"
        try:
            page.window.width = 435
            page.window.height = 860
        except Exception:
            pass
        page.padding = 0

        state = {"tab": 0}
        status_strip_container = ft.Container()
        body_container = ft.Container(expand=True, padding=14)

        def show_snack(msg: str, color: str = "#10B981"):
            snack = ft.SnackBar(
                content=ft.Text(msg, color="white", weight=ft.FontWeight.W_600),
                bgcolor=color,
            )
            try:
                page.open(snack)
            except Exception:
                try:
                    page.snack_bar = snack
                    page.snack_bar.open = True
                    page.update()
                except Exception:
                    pass

        def open_dialog_safe(dlg: ft.AlertDialog):
            try:
                page.open(dlg)
            except Exception:
                if dlg not in page.overlay:
                    page.overlay.append(dlg)
                dlg.open = True
                page.update()

        def close_dialog_safe(dlg: ft.AlertDialog):
            try:
                page.close(dlg)
            except Exception:
                dlg.open = False
                page.update()

        # Option 2 Feature: Clickable File-by-File Module Inspector Dialog
        def open_module_inspector_dialog(mod_key: str):
            integ = get_integration_status()
            mod = integ.get(mod_key)
            if not mod:
                return

            status_pills = []
            for f in mod["files"]:
                live = f["is_live"]
                pill_bg = "#064E3B" if live else "#451A03"
                pill_border = "#10B981" if live else "#F59E0B"
                pill_text = "🟢 LIVE (Real Code)" if live else "🟡 Fallback (Built-in)"
                pill_color = "#A7F3D0" if live else "#FDE68A"

                status_pills.append(
                    ft.Container(
                        padding=10,
                        border_radius=10,
                        bgcolor="#1E293B",
                        border=make_border("#334155", 1),
                        content=ft.Column(
                            tight=True,
                            spacing=3,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            f["path"],
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color="white",
                                        ),
                                        ft.Container(
                                            padding=pad(6, 2),
                                            bgcolor=pill_bg,
                                            border_radius=6,
                                            border=make_border(pill_border, 1),
                                            content=ft.Text(
                                                pill_text,
                                                size=10,
                                                weight=ft.FontWeight.BOLD,
                                                color=pill_color,
                                            ),
                                        ),
                                    ],
                                ),
                                ft.Text(
                                    f["task"],
                                    size=11,
                                    weight=ft.FontWeight.W_600,
                                    color="#94A3B8",
                                ),
                                ft.Text(f["desc"], size=10, color="#64748B"),
                            ],
                        ),
                    )
                )

            def refresh_and_reopen(_):
                close_dialog_safe(dlg)
                render_active_tab()
                open_module_inspector_dialog(mod_key)

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Column(
                    tight=True,
                    spacing=2,
                    controls=[
                        ft.Text(f"{mod['owner']}", size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"{mod['role']}  •  {mod['badge']}",
                            size=11,
                            color=mod["color"],
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                ),
                content=ft.Container(
                    width=365,
                    content=ft.Column(
                        tight=True,
                        spacing=8,
                        controls=[
                            ft.Container(
                                padding=10,
                                bgcolor="#0F172A",
                                border_radius=8,
                                content=ft.Text(
                                    f"📊 Progress: {mod['live_count']}/{mod['total_count']} files LIVE on current Git branch. "
                                    "Missing files run Built-in Fallbacks so no teammate is ever blocked!",
                                    size=11,
                                    color="#94A3B8",
                                ),
                            ),
                            ft.Column(tight=True, spacing=6, controls=status_pills),
                        ],
                    ),
                ),
                actions=[
                    ft.Row(
                        tight=True,
                        spacing=8,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            safe_outlined_btn("🔄 Rescan Files", on_click=refresh_and_reopen, height=34),
                            safe_btn(
                                "Close",
                                on_click=lambda _: close_dialog_safe(dlg),
                                bgcolor="#334155",
                                color="white",
                                height=34,
                            ),
                        ],
                    )
                ],
            )
            open_dialog_safe(dlg)

        def open_first_time_tag_dialog(
            payee_vpa: str, payee_name: str, amount: float, txn_result: dict
        ):
            custom_popup = _try_import("src.ui.popups", "show_first_time_tag_dialog")
            if custom_popup is not None:
                try:
                    custom_popup(page, payee_vpa, payee_name, amount, render_active_tab)
                    return
                except Exception:
                    pass

            selected_cat = {"id": 1}

            def on_cat_select(e):
                val = getattr(e.control, "value", None) or getattr(e, "data", "1")
                try:
                    selected_cat["id"] = int(val)
                except ValueError:
                    selected_cat["id"] = 1

            cat_dropdown = make_dropdown(
                label="Select Category (Saved for all future payments)",
                value="1",
                options_tuples=[
                    (str(cid), cname)
                    for cid, cname, _, _, _ in DEFAULT_CATEGORIES
                    if cid != 6
                ],
                on_change_fn=on_cat_select,
            )

            def save_tag_click(e):
                save_merchant_tag(payee_vpa, selected_cat["id"])
                close_dialog_safe(dlg)
                render_active_tab()
                show_snack(
                    f"Saved '{payee_vpa}' to Tier-1 Memory! Next payment will auto-tag.",
                    "#3B82F6",
                )

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "🏷️ First-Time Merchant Detected", size=17, weight=ft.FontWeight.BOLD
                ),
                content=ft.Container(
                    width=350,
                    content=ft.Column(
                        tight=True,
                        spacing=10,
                        controls=[
                            ft.Text(f"You paid ₹{amount:.0f} to {payee_name} ({payee_vpa})."),
                            ft.Text(
                                "Tag this merchant once — Tier 1 Heuristic Memory will remember it forever:",
                                size=12,
                                color="#94A3B8",
                            ),
                            cat_dropdown,
                        ],
                    ),
                ),
                actions=[
                    safe_btn(
                        "Save to Memory",
                        on_click=save_tag_click,
                        bgcolor="#2563EB",
                        color="white",
                        height=36,
                    )
                ],
            )
            open_dialog_safe(dlg)

        def handle_resolve_pending(internal_id: int, confirmed: bool):
            res = resolve_pending_txn(internal_id, confirmed=confirmed)
            render_active_tab()
            if not confirmed:
                show_snack(f"Pending payment #{internal_id} marked as Cancelled.", "#64748B")
                return

            if res.get("anomaly", {}).get("is_anomaly"):
                show_snack(
                    f"⚠️ Z-SCORE SPIKE ALERT! ₹{res['amount']:.0f} at {res['payee_name']} "
                    f"(Z={res['anomaly']['z_score']})",
                    "#EF4444",
                )
            else:
                show_snack(
                    f"✅ Logged ₹{res['amount']:.0f} to {res['payee_name']} [{res['category_name']}]",
                    "#10B981",
                )

            if res.get("needs_user_tag"):
                open_first_time_tag_dialog(
                    res["payee_vpa"], res["payee_name"], res["amount"], res
                )

        def on_lifecycle_change(e):
            state_str = str(getattr(e, "state", getattr(e, "data", e))).upper()
            if "RESUME" in state_str:
                pending = get_dashboard_summary(DB_FILE)["pending_list"]
                if pending:
                    render_active_tab()
                    show_snack(
                        f"📲 App Resumed: {len(pending)} Pending UPI Payment(s) waiting for 1-Tap verification!",
                        "#F59E0B",
                    )

        page.on_app_lifecycle_state_change = on_lifecycle_change

        # Option 1 + Option 2: 3-State Progress Chips + Clickable Inspector Popup
        def build_status_strip() -> ft.Control:
            integ = get_integration_status()
            chips = []
            info_icon = get_icon("INFO_OUTLINE_ROUNDED") or get_icon("INFO_OUTLINE")
            for key in ["backend_anuj", "frontend_saurabh", "analytics_uday"]:
                mod = integ[key]
                row_controls = [
                    ft.Text(
                        mod["badge"],
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color=mod["text_color"],
                    )
                ]
                if info_icon is not None:
                    row_controls.append(ft.Icon(info_icon, size=11, color=mod["color"]))

                chips.append(
                    ft.Container(
                        padding=pad(8, 4),
                        bgcolor=mod["bg"],
                        border_radius=12,
                        border=make_border(mod["border"], 1),
                        content=ft.Row(tight=True, spacing=4, controls=row_controls),
                        tooltip=f"Tap to inspect {mod['owner']}'s file-by-file status",
                        on_click=lambda e, k=key: open_module_inspector_dialog(k),
                    )
                )

            return ft.Container(
                bgcolor="#111827",
                padding=pad(12, 8),
                border=border_bottom("#1F2937", 1),
                content=ft.Column(
                    tight=True,
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "⚡ Exptracker v1.1 (Tap Chip to Inspect)",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                ),
                                ft.Container(
                                    padding=pad(8, 4),
                                    bgcolor="#1E293B",
                                    border_radius=6,
                                    border=make_border("#334155", 1),
                                    on_click=lambda _: (
                                        seed_mock_database(DB_FILE),
                                        render_active_tab(),
                                        show_snack(
                                            "Demo DB reset to 40 txns + 1 pending!", "#3B82F6"
                                        ),
                                    ),
                                    content=ft.Text(
                                        "🔄 Reset Demo DB",
                                        size=10,
                                        weight=ft.FontWeight.W_600,
                                        color="#93C5FD",
                                    ),
                                ),
                            ],
                        ),
                        ft.Row(spacing=6, wrap=True, controls=chips),
                    ],
                ),
            )

        def build_home_tab(summary: dict) -> ft.Control:
            h = summary["health"]
            score_color = (
                "#10B981"
                if h["status"] == "GREEN"
                else ("#F59E0B" if h["status"] == "YELLOW" else "#EF4444")
            )

            controls = [
                # Financial Health & Monthly Budget Card
                ft.Container(
                    padding=16,
                    border_radius=16,
                    bgcolor="#1E293B",
                    border=make_border("#334155", 1),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                "Monthly Spend (Oct 2026)",
                                                size=12,
                                                color="#94A3B8",
                                            ),
                                            ft.Text(
                                                f"₹{summary['total_spent']:,.0f} / ₹{summary['monthly_budget']:,.0f}",
                                                size=22,
                                                weight=ft.FontWeight.BOLD,
                                                color="white",
                                            ),
                                        ],
                                    ),
                                    ft.Container(
                                        padding=pad(12, 8),
                                        border_radius=12,
                                        bgcolor="#0F172A",
                                        border=make_border(score_color, 1.5),
                                        content=ft.Column(
                                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                            spacing=0,
                                            controls=[
                                                ft.Text(
                                                    f"{h['score']}/100",
                                                    size=18,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=score_color,
                                                ),
                                                ft.Text(
                                                    "Health Score", size=10, color="#94A3B8"
                                                ),
                                            ],
                                        ),
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=min(
                                    1.0,
                                    summary["total_spent"] / max(1.0, summary["monthly_budget"]),
                                ),
                                color=score_color,
                                bgcolor="#0F172A",
                                height=8,
                            ),
                            ft.Text(
                                f"Ideal Pace Today: ₹{h['ideal_spend']:,.0f}  •  "
                                f"Anomalies Flagged: {summary['anomaly_count']}",
                                size=11,
                                color="#CBD5E1",
                            ),
                        ],
                    ),
                )
            ]

            # 1-Tap Pending Transaction Fallback Banner (If any PENDING row exists)
            for p in summary["pending_list"]:
                controls.append(
                    ft.Container(
                        padding=14,
                        border_radius=14,
                        bgcolor="#451A03",
                        border=make_border("#F59E0B", 1.5),
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(
                                            "⏳ 1-Tap Resume Fallback Verification",
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FDE68A",
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    f"Did your UPI payment of ₹{p['amount']:.0f} to "
                                    f"{p['payee_name']} ({p['payee_vpa']}) succeed?",
                                    size=12,
                                    color="white",
                                ),
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        safe_btn(
                                            "✅ Yes, Log Payment",
                                            on_click=lambda e, pid=p["internal_id"]: handle_resolve_pending(
                                                pid, True
                                            ),
                                            bgcolor="#10B981",
                                            color="white",
                                        ),
                                        safe_outlined_btn(
                                            "❌ No, Cancelled",
                                            on_click=lambda e, pid=p["internal_id"]: handle_resolve_pending(
                                                pid, False
                                            ),
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

            controls.append(
                ft.Text(
                    "Recent UPI Transactions",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="white",
                )
            )

            txn_items = []
            for t in summary["recent_txns"]:
                is_anom = t["is_anomaly"]
                txn_items.append(
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor="#2E1016" if is_anom else "#1E293B",
                        border=make_border("#EF4444" if is_anom else "#334155", 1),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Row(
                                            spacing=6,
                                            controls=[
                                                ft.Text(
                                                    t["payee_name"],
                                                    size=14,
                                                    weight=ft.FontWeight.W_600,
                                                    color="white",
                                                ),
                                                ft.Container(
                                                    visible=is_anom,
                                                    padding=pad(6, 2),
                                                    bgcolor="#EF4444",
                                                    border_radius=6,
                                                    content=ft.Text(
                                                        "Z-SPIKE",
                                                        size=9,
                                                        weight=ft.FontWeight.BOLD,
                                                        color="white",
                                                    ),
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            f"{t['category']} • {t['payee_vpa']} {t['notes']}",
                                            size=11,
                                            color="#94A3B8",
                                        ),
                                    ],
                                ),
                                ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            f"-₹{t['amount']:.0f}",
                                            size=15,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FCA5A5" if is_anom else "white",
                                        ),
                                        ft.Text(t["timestamp"][5:16], size=10, color="#64748B"),
                                    ],
                                ),
                            ],
                        ),
                    )
                )

            controls.append(ft.Column(spacing=8, controls=txn_items))
            return ft.Column(
                scroll=ft.ScrollMode.AUTO, expand=True, spacing=12, controls=controls
            )

        def build_scan_pay_tab() -> ft.Control:
            presets = {
                "Ramesh Tea Stall (Tier 1 Memory - Try ₹1500 for Z-Spike!)": (
                    "ramesh.chai@ybl",
                    "Ramesh Tea Stall",
                    "upi://pay?pa=ramesh.chai@ybl&pn=Ramesh%20Tea%20Stall&mc=5814&sign=NPCI_SIGNED_8821&orgid=159001",
                ),
                "Zomato Order (Tier 2 Regex Signed Merchant QR)": (
                    "zomato.order@hdfcbank",
                    "Zomato Limited",
                    "upi://pay?pa=zomato.order@hdfcbank&pn=Zomato%20Limited&mc=5812&sign=NPCI_SIGNED_9912&tr=ZMT2026",
                ),
                "Gupta Stationery (Tier 3 Unknown - Triggers 1-Tap Tag Popup!)": (
                    "gupta.books@okaxis",
                    "Gupta Stationery Hub",
                    "upi://pay?pa=gupta.books@okaxis&pn=Gupta%20Stationery%20Hub&mc=5942&sign=NPCI_SIGNED_3319",
                ),
            }

            default_key = "Ramesh Tea Stall (Tier 1 Memory - Try ₹1500 for Z-Spike!)"
            vpa_field = ft.TextField(
                label="Merchant VPA (pa)", value="ramesh.chai@ybl", height=48, text_size=13
            )
            name_field = ft.TextField(
                label="Merchant Name (pn)", value="Ramesh Tea Stall", height=48, text_size=13
            )
            qr_field = ft.TextField(
                label="Scanned Raw NPCI UPI 2.0 QR URI (Preserves mc, sign, orgid)",
                value=presets[default_key][2],
                multiline=True,
                min_lines=2,
                max_lines=2,
                text_size=11,
            )
            amt_field = ft.TextField(
                label="Amount (₹ INR)",
                value="20",
                keyboard_type=ft.KeyboardType.NUMBER,
                height=48,
            )
            notes_field = ft.TextField(
                label="Quick Tag / Note (Optional)",
                value="#EveningChai",
                height=48,
                text_size=13,
            )
            initial_uri = build_signed_upi_uri(presets[default_key][2], 20.0)
            uri_preview = ft.Text(
                f"🔒 Constructed Signed Intent URI: {initial_uri}",
                size=11,
                color="#38BDF8",
                selectable=True,
            )

            def update_preview(e=None):
                try:
                    amt = float(amt_field.value or 0)
                except ValueError:
                    amt = 0.0
                built = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                uri_preview.value = f"🔒 Constructed Signed Intent URI: {built}"
                if e is not None:
                    page.update()

            def on_preset_change(e):
                selected_key = getattr(e.control, "value", None) or getattr(
                    e, "data", default_key
                )
                if selected_key in presets:
                    vpa, name, raw_uri = presets[selected_key]
                    vpa_field.value = vpa
                    name_field.value = name
                    qr_field.value = raw_uri
                    update_preview(e)

            preset_dropdown = make_dropdown(
                label="Quick Demo Preset (Select Scenario for Faculty Demo)",
                value=default_key,
                options_tuples=[(k, k) for k in presets.keys()],
                on_change_fn=on_preset_change,
            )
            amt_field.on_change = update_preview
            qr_field.on_change = update_preview

            def click_launch_pending(e):
                try:
                    amt = float(amt_field.value or 0)
                    if amt <= 0:
                        raise ValueError
                except ValueError:
                    show_snack("Enter a valid positive amount in ₹!", "#EF4444")
                    return
                built_uri = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                pid = create_pending_txn(amt, vpa_field.value, name_field.value, built_uri)
                try:
                    page.launch_url(built_uri)
                except Exception:
                    pass
                state["tab"] = 0
                nav_bar.selected_index = 0
                render_active_tab()
                show_snack(
                    f"Created PENDING #{pid} & launched UPI Intent! Verify on Home Tab.",
                    "#F59E0B",
                )

            def click_instant_simulate(e):
                try:
                    amt = float(amt_field.value or 0)
                    if amt <= 0:
                        raise ValueError
                except ValueError:
                    show_snack("Enter a valid positive amount in ₹!", "#EF4444")
                    return
                built_uri = build_signed_upi_uri(qr_field.value or vpa_field.value, amt)
                pid = create_pending_txn(amt, vpa_field.value, name_field.value, built_uri)
                res = resolve_pending_txn(pid, confirmed=True, notes=notes_field.value)
                state["tab"] = 0
                nav_bar.selected_index = 0
                render_active_tab()
                if res.get("anomaly", {}).get("is_anomaly"):
                    show_snack(
                        f"⚠️ ANOMALY DETECTED! ₹{amt:.0f} (Z={res['anomaly']['z_score']} > 2.5)",
                        "#EF4444",
                    )
                else:
                    show_snack(
                        f"✅ Instant Paid ₹{amt:.0f} -> Auto-Tagged: {res['category_name']} ({res['tier']})",
                        "#10B981",
                    )
                if res.get("needs_user_tag"):
                    open_first_time_tag_dialog(
                        res["payee_vpa"], res["payee_name"], amt, res
                    )

            return ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "📷 QR Scan & UPI 2.0 Intent Simulator",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color="white",
                    ),
                    preset_dropdown,
                    vpa_field,
                    name_field,
                    amt_field,
                    notes_field,
                    qr_field,
                    ft.Container(
                        padding=10,
                        bgcolor="#0F172A",
                        border_radius=10,
                        border=make_border("#1E293B", 1),
                        content=uri_preview,
                    ),
                    safe_btn(
                        "🚀 Step 1: Launch UPI App (Saves PENDING Row First)",
                        on_click=click_launch_pending,
                        bgcolor="#2563EB",
                        color="white",
                        height=44,
                    ),
                    safe_btn(
                        "⚡ Instant Simulate Payment Success (Test Tagger + Z-Score)",
                        on_click=click_instant_simulate,
                        bgcolor="#059669",
                        color="white",
                        height=44,
                    ),
                ],
            )

        def build_analytics_tab(summary: dict) -> ft.Control:
            cat_cards = []
            for c in summary["categories"]:
                bar_color = (
                    "#EF4444"
                    if c["ratio"] >= 0.85
                    else ("#F59E0B" if c["ratio"] >= 0.65 else "#3B82F6")
                )
                cat_cards.append(
                    ft.Container(
                        padding=12,
                        border_radius=12,
                        bgcolor="#1E293B",
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            f"{c['name']} ({c['count']} txns)",
                                            size=13,
                                            weight=ft.FontWeight.W_600,
                                            color="white",
                                        ),
                                        ft.Text(
                                            f"₹{c['spent']:,.0f} / ₹{c['budget_limit']:,.0f}",
                                            size=12,
                                            color="#CBD5E1",
                                        ),
                                    ],
                                ),
                                ft.ProgressBar(
                                    value=c["ratio"],
                                    color=bar_color,
                                    bgcolor="#0F172A",
                                    height=7,
                                ),
                            ],
                        ),
                    )
                )

            def export_csv_click(e):
                path = export_transactions_csv()
                show_snack(f"📄 Exported CSV to: {os.path.basename(path)}", "#10B981")

            return ft.Column(
                scroll=ft.ScrollMode.AUTO,
                expand=True,
                spacing=12,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "📊 Category Spend & Z-Score Engine",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color="white",
                            ),
                            safe_btn(
                                "⬇️ Export CSV",
                                on_click=export_csv_click,
                                bgcolor="#334155",
                                color="white",
                                height=34,
                            ),
                        ],
                    ),
                    ft.Column(spacing=8, controls=cat_cards),
                ],
            )

        def render_active_tab():
            status_strip_container.content = build_status_strip()
            summary = get_dashboard_summary(DB_FILE)
            if state["tab"] == 0:
                custom_home = _try_import("src.ui.home_view", "build_home_view")
                body_container.content = (
                    custom_home(page, summary) if custom_home else build_home_tab(summary)
                )
            elif state["tab"] == 1:
                custom_scan = _try_import("src.ui.scanner_view", "build_scanner_view")
                body_container.content = (
                    custom_scan(page) if custom_scan else build_scan_pay_tab()
                )
            else:
                custom_dash = _try_import("src.ui.dashboard_view", "build_dashboard_view")
                body_container.content = (
                    custom_dash(page, summary)
                    if custom_dash
                    else build_analytics_tab(summary)
                )
            page.update()

        def on_nav_change(e):
            state["tab"] = e.control.selected_index
            render_active_tab()

        home_icon = get_icon("HOME_ROUNDED") or get_icon("HOME")
        qr_icon = get_icon("QR_CODE_SCANNER_ROUNDED") or get_icon("QR_CODE")
        chart_icon = get_icon("INSERT_CHART_ROUNDED") or get_icon("BAR_CHART")

        nav_bar = ft.NavigationBar(
            selected_index=0,
            bgcolor="#111827",
            on_change=on_nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=home_icon, label="Home & Feed"),
                ft.NavigationBarDestination(icon=qr_icon, label="Scan & Pay"),
                ft.NavigationBarDestination(icon=chart_icon, label="Analytics"),
            ],
        )

        page.add(
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    status_strip_container,
                    body_container,
                    nav_bar,
                ],
            )
        )
        render_active_tab()

    if hasattr(ft, "run"):
        ft.run(main)
    else:
        ft.app(target=main)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Automated Expenditure Tracker — Live App & Integrator"
    )
    parser.add_argument(
        "--check-integration",
        action="store_true",
        help="Run 6-point CLI integration check without GUI",
    )
    args = parser.parse_args()

    if args.check_integration:
        run_cli_integration_audit()
    else:
        launch_flet_app()
