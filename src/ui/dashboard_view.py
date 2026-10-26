"""
Saurabh Yadav (Frontend UI) — Task S0-04
Flet 0.80+ / 1.0+ Dark-Mode Analytics Dashboard View (src/ui/dashboard_view.py)
Plugs into the 3-Tab Bottom Navigation Shell (Home / Scan & Pay / Analytics) in main.py.
"""

import flet as ft
from src.contracts import (
    ensure_db_ready,
    export_transactions_csv,
    get_dashboard_summary,
)


def _pad(left: float = 0, top: float = 0, right: float = 0, bottom: float = 0) -> ft.Padding:
    """Flet 1.0+/0.80+ compatible padding helper using ft.Padding class directly."""
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def _border(color: str = "#334155", width: float = 1.0) -> ft.Border:
    """Flet 1.0+/0.80+ compatible 4-sided border helper using ft.Border and ft.BorderSide."""
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def _safe_btn(label: str, on_click_handler, bgcolor: str = "#2563EB") -> ft.Container:
    """Flet 1.0+/0.80+ compatible button built with ft.Container."""
    return ft.Container(
        content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color="#FFFFFF"),
        bgcolor=bgcolor,
        border_radius=8,
        padding=_pad(left=12, top=8, right=12, bottom=8),
        on_click=on_click_handler,
        ink=True,
    )


def build_dashboard_view(page: ft.Page, summary: dict) -> ft.Control:
    """
    Builds the Analytics tab content for the 3-tab mobile navigation shell.
    Receives pre-aggregated category metrics from src.contracts.get_dashboard_summary().
    """
    if not isinstance(summary, dict):
        summary = {}
    categories = summary.get("categories") or summary.get("category_breakdown") or []
    total_spent = float(summary.get("total_spent", 0.0))
    monthly_budget = float(summary.get("monthly_budget", 15000.0))

    def on_export_click(e):
        out_path = export_transactions_csv("expenditure_export.csv")
        if page is not None:
            snack = ft.SnackBar(
                content=ft.Text(f"CSV exported: {out_path}", color="#FFFFFF"),
                bgcolor="#10B981",
            )
            if hasattr(page, "open"):
                page.open(snack)
            else:
                page.snack_bar = snack
                snack.open = True
                page.update()

    category_cards = []
    for cat in categories:
        name = cat.get("name") or cat.get("category_name") or "Uncategorized"
        count = int(cat.get("count") or cat.get("txn_count") or 0)
        spent = float(cat.get("spent") or cat.get("total_spent") or 0.0)
        limit = float(cat.get("budget_limit") or 1.0)
        ratio = float(cat.get("ratio", spent / max(1.0, limit)))
        clamped_ratio = max(0.0, min(1.0, ratio))

        if ratio >= 0.85:
            bar_color = "#EF4444"
            status_tag = "CRITICAL (>=85%)"
        elif ratio >= 0.65:
            bar_color = "#F59E0B"
            status_tag = "WATCH (>=65%)"
        else:
            bar_color = "#10B981"
            status_tag = "HEALTHY"

        card = ft.Container(
            bgcolor="#1E293B",
            border=_border("#334155", 1.0),
            border_radius=12,
            padding=_pad(left=14, top=12, right=14, bottom=12),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                f"{name} ({count} txns)",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color="#F8FAFC",
                            ),
                            ft.Text(
                                f"Rs.{spent:,.0f} / Rs.{limit:,.0f}",
                                size=12,
                                weight=ft.FontWeight.W_600,
                                color=bar_color,
                            ),
                        ],
                    ),
                    ft.ProgressBar(
                        value=clamped_ratio,
                        color=bar_color,
                        bgcolor="#0F172A",
                        height=7,
                        border_radius=4,
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                f"{ratio * 100:.1f}% of category budget used",
                                size=11,
                                color="#94A3B8",
                            ),
                            ft.Text(
                                status_tag,
                                size=10,
                                weight=ft.FontWeight.BOLD,
                                color=bar_color,
                            ),
                        ],
                    ),
                ],
            ),
        )
        category_cards.append(card)

    if not category_cards:
        category_cards.append(
            ft.Container(
                bgcolor="#1E293B",
                border=_border("#334155", 1.0),
                border_radius=12,
                padding=_pad(left=14, top=16, right=14, bottom=16),
                content=ft.Text(
                    "No category transactions available yet.",
                    size=13,
                    color="#94A3B8",
                ),
            )
        )

    return ft.Column(
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                bgcolor="#0F172A",
                border=_border("#10B981", 1.0),
                border_radius=10,
                padding=_pad(left=12, top=8, right=12, bottom=8),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "[LIVE MODULE] Saurabh Yadav — Flet 0.80+ Analytics UI",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#10B981",
                        ),
                        ft.Text(
                            f"Total: Rs.{total_spent:,.0f} / Rs.{monthly_budget:,.0f}",
                            size=11,
                            color="#94A3B8",
                        ),
                    ],
                ),
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(
                                "Category Spend Breakdown",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color="#F8FAFC",
                            ),
                            ft.Text(
                                "30-day SQLite v1.1 category utilization & pace",
                                size=11,
                                color="#94A3B8",
                            ),
                        ],
                    ),
                    _safe_btn("Export CSV", on_export_click, bgcolor="#2563EB"),
                ],
            ),
            *category_cards,
        ],
    )


if __name__ == "__main__":
    ensure_db_ready()
    mock_summary = get_dashboard_summary()
    ctrl = build_dashboard_view(None, mock_summary)
    assert isinstance(ctrl, ft.Control), "build_dashboard_view must return an ft.Control"
    assert isinstance(ctrl, ft.Column), "Dashboard root control must be an ft.Column"
    empty_ctrl = build_dashboard_view(None, {})
    assert isinstance(empty_ctrl, ft.Control), "Empty summary fallback failed"
    print("[PASS] Saurabh S0-04 Flet 0.80+ Dashboard View Unit Test Verified!")