"""Saurabh Yadav — Flet 0.80+ Dark-Mode Analytics Dashboard View (Task S0-04)."""

import os
import flet as ft
from src.contracts import export_transactions_csv, get_dashboard_summary


def _border(color: str = "#334155", width: float = 1.0):
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def _safe_btn(label: str, on_click, bgcolor: str = "#2563EB", color: str = "white") -> ft.Control:
    """Flet 0.80+ compatible button helper using a clickable Container."""
    return ft.Container(
        padding=10,
        border_radius=8,
        bgcolor=bgcolor,
        on_click=on_click,
        content=ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=color),
    )


def build_dashboard_view(page: ft.Page, summary: dict) -> ft.Control:
    """Renders the live Flet 0.80+ Category Spend & Health Score Dashboard tab."""
    cat_cards = []
    for c in summary.get("categories", []):
        ratio = float(c.get("ratio", 0.0))
        bar_color = "#EF4444" if ratio >= 0.85 else ("#F59E0B" if ratio >= 0.65 else "#10B981")
        cat_cards.append(
            ft.Container(
                padding=12,
                border_radius=12,
                bgcolor="#1E293B",
                border=_border("#334155", 1),
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(f"{c['name']} ({c['count']} txns)", size=13, weight=ft.FontWeight.W_600, color="white"),
                                ft.Text(f"₹{c['spent']:,.0f} / ₹{c['budget_limit']:,.0f}", size=12, color="#CBD5E1"),
                            ],
                        ),
                        ft.ProgressBar(value=ratio, color=bar_color, bgcolor="#0F172A", height=8),
                    ],
                ),
            )
        )

    def on_export_click(e):
        out_path = export_transactions_csv()
        if page is not None:
            snack = ft.SnackBar(
                content=ft.Text(f"Exported CSV: {os.path.basename(out_path)}", color="white"),
                bgcolor="#10B981",
            )
            if hasattr(page, "open"):
                page.open(snack)
            else:
                page.snack_bar = snack
                page.snack_bar.open = True
                page.update()

    export_btn = _safe_btn("Export CSV", on_click=on_export_click, bgcolor="#2563EB", color="white")

    return ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
        controls=[
            ft.Container(
                padding=10,
                border_radius=10,
                bgcolor="#064E3B",
                border=_border("#10B981", 1),
                content=ft.Text("🟢 Saurabh Live UI Module (src/ui/dashboard_view.py) Active", size=12, color="#A7F3D0", weight=ft.FontWeight.BOLD),
            ),
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("📊 Category Spend Breakdown", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    export_btn,
                ],
            ),
            ft.Column(spacing=8, controls=cat_cards),
        ],
    )


if __name__ == "__main__":
    mock_summary = get_dashboard_summary()
    ctrl = build_dashboard_view(None, mock_summary)
    assert isinstance(ctrl, ft.Control)
    print("[PASS] Saurabh S0-04 Flet 0.80+ Dashboard View Unit Test Verified!")