"""
src/ui/dashboard_view.py
Saurabh Yadav (Frontend UI - Tasks S0-04 & S3-01 Creative Analytics Charts)
Flet 1.0+/0.80+ Dark-Mode Spend Insights & Interactive Chart Dashboard:
- 3-Mode Interactive Chart Switcher:
  1. 🍩 Donut & Ring Chart (Concentric Multi-Ring Donut with centered Total Spent + Share Bar)
  2. 📊 Column Bar Chart (Vertical Spent vs. Budget Limit columns for all 6 categories)
  3. 🎯 Radial Gauge Grid (2x3 Circular Gauge Meters + Financial Health Score Gauge)
- Mockup-Style Category Breakdown Cards with Colored Icon Tiles, Mini-Gauges & Status Pills
"""

import os
import flet as ft
from src.contracts import (
    ensure_db_ready,
    export_transactions_csv,
    get_dashboard_summary,
)


# ============================================================================
# 1. FLET 1.0+ / 0.80+ BULLETPROOF LAYOUT HELPERS & PALETTE
# ============================================================================
def _pad(left: float = 0, top: float = 0, right: float = 0, bottom: float = 0) -> ft.Padding:
    """Returns Flet 1.0+/0.80+ ft.Padding without calling removed ft.padding.only."""
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def _border(color: str = "#334155", width: float = 1.0) -> ft.Border:
    """Returns Flet 1.0+/0.80+ 4-sided ft.Border without calling removed ft.border.all."""
    side = ft.BorderSide(width=width, color=color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def _center_align():
    """Version-safe center alignment for ft.Container and ft.Stack across Flet 0.80+ and 1.0.4."""
    if hasattr(ft, "Alignment"):
        try:
            return ft.Alignment(0, 0)
        except Exception:
            pass
    return getattr(ft.alignment, "center", None)


CATEGORY_META = {
    "Food & Dining": {"emoji": "🍽️", "short": "Food", "color": "#F97316", "bg": "#431407"},
    "Travel": {"emoji": "🚇", "short": "Travel", "color": "#8B5CF6", "bg": "#2E1065"},
    "Groceries": {"emoji": "🛒", "short": "Groc", "color": "#10B981", "bg": "#064E3B"},
    "Fuel": {"emoji": "⛽", "short": "Fuel", "color": "#F59E0B", "bg": "#451A03"},
    "Utilities": {"emoji": "⚡", "short": "Utils", "color": "#38BDF8", "bg": "#0C4A6E"},
    "Uncategorized": {"emoji": "📦", "short": "Other", "color": "#EC4899", "bg": "#500724"},
}


def _cat_meta(name: str) -> dict:
    return CATEGORY_META.get(
        name,
        {"emoji": "💳", "short": name[:5], "color": "#38BDF8", "bg": "#0F172A"},
    )


def _notify(page: ft.Page, message: str, bgcolor: str = "#10B981") -> None:
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


# ============================================================================
# 2. CREATIVE CHART BUILDERS (Donut Chart, Column Chart, Radial Gauge Grid)
# ============================================================================
def _build_donut_chart_view(cats: list, total_spent: float, budget: float, health_score: int, health_col: str) -> ft.Control:
    """
    Mode 1: Concentric Multi-Ring Donut Chart with centered Total Spent (matches reference UI mockup)
    + Right-side Category Share Legend + Segmented Distribution Bar.
    """
    safe_total = max(1.0, total_spent)

    # Sort categories by spend descending so top categories drive the concentric donut rings
    sorted_cats = sorted(cats, key=lambda x: float(x.get("spent", 0.0)), reverse=True)
    top4 = sorted_cats[:4]

    ring_specs = [
        (146, 13),  # Outer ring
        (114, 11),  # Second ring
        (86, 10),   # Third ring
        (62, 8),    # Inner ring
    ]

    stack_layers = []
    for idx, (diameter, stroke_w) in enumerate(ring_specs):
        if idx < len(top4):
            c = top4[idx]
            c_name = str(c.get("name", "Category"))
            c_spent = float(c.get("spent", 0.0))
            c_limit = float(c.get("limit") or c.get("budget_limit") or 1.0)
            meta = _cat_meta(c_name)
            # Ring fill shows share of total spend (or budget utilization if non-zero)
            ring_val = min(1.0, max(0.08, c_spent / safe_total)) if c_spent > 0 else 0.04
            ring_col = meta["color"]
        else:
            ring_val = 0.05
            ring_col = "#334155"

        stack_layers.append(
            ft.Container(
                width=diameter,
                height=diameter,
                alignment=_center_align(),
                content=ft.ProgressRing(
                    value=ring_val,
                    width=diameter,
                    height=diameter,
                    stroke_width=stroke_w,
                    color=ring_col,
                    bgcolor="#0F172A",
                ),
            )
        )

    # Center Donut Hole with Total Spent (matches reference UI screenshot)
    stack_layers.append(
        ft.Container(
            width=50,
            height=50,
            bgcolor="#1E293B",
            border_radius=25,
            alignment=_center_align(),
            content=ft.Column(
                [
                    ft.Text("Total", size=8, color="#94A3B8", text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        f"₹{total_spent / 1000:.1f}k" if total_spent >= 1000 else f"₹{total_spent:.0f}",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
    )

    donut_box = ft.Container(
        width=152,
        height=152,
        alignment=_center_align(),
        content=ft.Stack(controls=stack_layers, width=152, height=152),
    )

    # Right-side Category Legend with exact % share
    legend_rows = []
    for c in sorted_cats:
        c_name = str(c.get("name", "Category"))
        c_spent = float(c.get("spent", 0.0))
        share_pct = (c_spent / safe_total) * 100.0 if total_spent > 0 else 0.0
        meta = _cat_meta(c_name)
        legend_rows.append(
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=meta["color"], border_radius=5),
                    ft.Text(
                        f"{meta['emoji']} {meta['short']}",
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color="#E2E8F0",
                        expand=True,
                        no_wrap=True,
                    ),
                    ft.Text(
                        f"₹{c_spent:,.0f} ({share_pct:.0f}%)",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color=meta["color"] if c_spent > 0 else "#64748B",
                        no_wrap=True,
                    ),
                ],
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    # Multi-Segment Horizontal Spend Distribution Bar below the Donut
    seg_bars = []
    for c in sorted_cats:
        c_name = str(c.get("name", "Category"))
        c_spent = float(c.get("spent", 0.0))
        if c_spent > 0:
            meta = _cat_meta(c_name)
            flex_weight = max(1, int(round((c_spent / safe_total) * 20)))
            seg_bars.append(
                ft.Container(
                    height=8,
                    bgcolor=meta["color"],
                    border_radius=4,
                    expand=flex_weight,
                    tooltip=f"{c_name}: Rs.{c_spent:,.0f}",
                )
            )
    if not seg_bars:
        seg_bars.append(ft.Container(height=8, bgcolor="#334155", border_radius=4, expand=1))

    return ft.Column(
        [
            ft.Row(
                [
                    donut_box,
                    ft.Column(controls=legend_rows, spacing=6, expand=True),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=2),
            ft.Text("Category Spend Share Distribution", size=10, color="#94A3B8"),
            ft.Row(controls=seg_bars, spacing=3),
        ],
        spacing=6,
    )


def _build_column_chart_view(cats: list) -> ft.Control:
    """
    Mode 2: Vertical Column Bar Chart comparing Spent (colored bar) vs. Budget Limit (slate bar)
    across all 6 categories.
    """
    max_val = 1.0
    for c in cats:
        s = float(c.get("spent", 0.0))
        lim = float(c.get("limit") or c.get("budget_limit") or 1.0)
        max_val = max(max_val, s, lim)

    max_bar_height = 105.0
    col_items = []

    for c in cats:
        c_name = str(c.get("name", "Category"))
        c_spent = float(c.get("spent", 0.0))
        c_limit = max(1.0, float(c.get("limit") or c.get("budget_limit") or 1.0))
        pct = (c_spent / c_limit) * 100.0
        meta = _cat_meta(c_name)

        spent_h = max(6.0, round((c_spent / max_val) * max_bar_height, 1)) if c_spent > 0 else 4.0
        limit_h = max(6.0, round((c_limit / max_val) * max_bar_height, 1))
        bar_col = "#EF4444" if pct >= 100 else ("#F59E0B" if pct >= 85 else meta["color"])

        amt_str = f"₹{c_spent / 1000:.1f}k" if c_spent >= 1000 else f"₹{c_spent:.0f}"

        col_items.append(
            ft.Column(
                [
                    ft.Text(
                        amt_str,
                        size=9,
                        weight=ft.FontWeight.BOLD,
                        color=bar_col if c_spent > 0 else "#64748B",
                        no_wrap=True,
                    ),
                    ft.Container(
                        height=max_bar_height + 4,
                        alignment=getattr(ft.alignment, "bottom_center", _center_align()),
                        content=ft.Row(
                            [
                                ft.Container(
                                    width=15,
                                    height=spent_h,
                                    bgcolor=bar_col,
                                    border_radius=4,
                                    tooltip=f"{c_name} Spent: Rs.{c_spent:,.0f}",
                                ),
                                ft.Container(
                                    width=9,
                                    height=limit_h,
                                    bgcolor="#334155",
                                    border_radius=3,
                                    tooltip=f"{c_name} Limit: Rs.{c_limit:,.0f}",
                                ),
                            ],
                            spacing=3,
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                        ),
                    ),
                    ft.Text(meta["emoji"], size=12, text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        meta["short"],
                        size=9,
                        weight=ft.FontWeight.W_600,
                        color="#E2E8F0",
                        no_wrap=True,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                spacing=3,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(width=10, height=10, bgcolor="#38BDF8", border_radius=3),
                            ft.Text("Actual Spent", size=10, color="#E2E8F0"),
                        ],
                        spacing=4,
                    ),
                    ft.Row(
                        [
                            ft.Container(width=10, height=10, bgcolor="#334155", border_radius=3),
                            ft.Text("Category Budget Limit", size=10, color="#94A3B8"),
                        ],
                        spacing=4,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(
                padding=_pad(8, 10, 8, 8),
                bgcolor="#0F172A",
                border=_border("#334155", 1.0),
                border_radius=10,
                content=ft.Row(
                    controls=col_items,
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            ),
        ],
        spacing=6,
    )


def _build_gauge_grid_view(cats: list, health_score: int, health_status: str, health_col: str, ideal_spend: float) -> ft.Control:
    """
    Mode 3: Financial Health Radial Gauge + 2x3 Category Circular Gauge Grid.
    """
    gauge_rows = []
    for i in range(0, len(cats), 2):
        pair = cats[i : i + 2]
        row_cards = []
        for c in pair:
            c_name = str(c.get("name", "Category"))
            c_spent = float(c.get("spent", 0.0))
            c_limit = max(1.0, float(c.get("limit") or c.get("budget_limit") or 1.0))
            pct = (c_spent / c_limit) * 100.0
            meta = _cat_meta(c_name)

            ring_col = "#EF4444" if pct >= 85 else ("#F59E0B" if pct >= 60 else "#10B981")

            row_cards.append(
                ft.Container(
                    expand=True,
                    padding=_pad(10, 10, 10, 10),
                    bgcolor="#0F172A",
                    border=_border(ring_col if pct >= 85 else "#334155", 1.0),
                    border_radius=10,
                    content=ft.Row(
                        [
                            ft.Container(
                                width=52,
                                height=52,
                                alignment=_center_align(),
                                content=ft.Stack(
                                    [
                                        ft.ProgressRing(
                                            value=min(1.0, pct / 100.0),
                                            width=52,
                                            height=52,
                                            stroke_width=6,
                                            color=ring_col,
                                            bgcolor="#1E293B",
                                        ),
                                        ft.Container(
                                            width=52,
                                            height=52,
                                            alignment=_center_align(),
                                            content=ft.Text(
                                                f"{pct:.0f}%",
                                                size=9,
                                                weight=ft.FontWeight.BOLD,
                                                color="#FFFFFF",
                                            ),
                                        ),
                                    ],
                                    width=52,
                                    height=52,
                                ),
                            ),
                            ft.Column(
                                [
                                    ft.Text(
                                        f"{meta['emoji']} {meta['short']}",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",
                                        no_wrap=True,
                                    ),
                                    ft.Text(
                                        f"₹{c_spent:,.0f}",
                                        size=11,
                                        weight=ft.FontWeight.BOLD,
                                        color=ring_col,
                                        no_wrap=True,
                                    ),
                                    ft.Text(
                                        f"of ₹{c_limit:,.0f}",
                                        size=9,
                                        color="#94A3B8",
                                        no_wrap=True,
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                )
            )
        gauge_rows.append(ft.Row(controls=row_cards, spacing=8))

    return ft.Column(
        [
            ft.Container(
                padding=_pad(10, 8, 10, 8),
                bgcolor="#0F172A",
                border=_border(health_col, 1.0),
                border_radius=10,
                content=ft.Row(
                    [
                        ft.Container(
                            width=48,
                            height=48,
                            alignment=_center_align(),
                            content=ft.Stack(
                                [
                                    ft.ProgressRing(
                                        value=min(1.0, max(0.0, health_score / 100.0)),
                                        width=48,
                                        height=48,
                                        stroke_width=6,
                                        color=health_col,
                                        bgcolor="#1E293B",
                                    ),
                                    ft.Container(
                                        width=48,
                                        height=48,
                                        alignment=_center_align(),
                                        content=ft.Text(
                                            f"{health_score}",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FFFFFF",
                                        ),
                                    ),
                                ],
                                width=48,
                                height=48,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    f"Financial Health Gauge: {health_score}/100 ({health_status})",
                                    size=12,
                                    weight=ft.FontWeight.BOLD,
                                    color="#FFFFFF",
                                ),
                                ft.Text(
                                    f"Mid-Month Ideal Spend Benchmark: Rs. {ideal_spend:,.0f}",
                                    size=10,
                                    color="#94A3B8",
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                ),
            ),
            ft.Column(controls=gauge_rows, spacing=8),
        ],
        spacing=8,
    )


# ============================================================================
# 3. PRIMARY VIEW BUILDER: build_dashboard_view(page, summary) -> ft.Control
# ============================================================================
def build_dashboard_view(page: ft.Page = None, summary: dict = None) -> ft.Control:
    """
    Builds the Spend Insights & Creative Chart Analytics View.
    Auto-discovered by main.py: build_dashboard_view(page, summary).
    """
    ensure_db_ready()
    data = summary if isinstance(summary, dict) else get_dashboard_summary()

    spent = float(data.get("spent_this_month", data.get("total_spent", 0.0)))
    budget = float(data.get("monthly_budget", 12000.0))
    ideal_spend = float(data.get("ideal_spend", 0.0))
    txn_count = int(data.get("transaction_count", 0))
    anomaly_count = int(data.get("anomaly_count", 0))
    health_score = int(data.get("health_score", 100))
    health_status = str(data.get("health_status", "GREEN"))
    health_color = str(data.get("health_color", "#10B981"))
    cats = list(data.get("category_breakdown", []))

    active_chart_mode = ["DONUT"]  # "DONUT" | "COLUMN" | "GAUGE"
    chart_body_holder = ft.Container()
    mode_tabs_row = ft.Row(spacing=6)

    def select_chart_mode(mode_key: str) -> None:
        active_chart_mode[0] = mode_key
        render_chart_section()
        if page is not None:
            page.update()

    def render_chart_section() -> None:
        mode_tabs_row.controls.clear()
        for key, label in (
            ("DONUT", "🍩 Donut Chart"),
            ("COLUMN", "📊 Column Chart"),
            ("GAUGE", "🎯 Gauge Grid"),
        ):
            is_sel = active_chart_mode[0] == key
            mode_tabs_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        label,
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF" if is_sel else "#94A3B8",
                        text_align=ft.TextAlign.CENTER,
                        no_wrap=True,
                    ),
                    height=34,
                    padding=_pad(10, 0, 10, 0),
                    bgcolor="#2563EB" if is_sel else "#0F172A",
                    border=_border("#38BDF8" if is_sel else "#334155", 1.0),
                    border_radius=8,
                    alignment=_center_align(),
                    on_click=lambda e, k=key: select_chart_mode(k),
                    expand=True,
                )
            )

        if active_chart_mode[0] == "DONUT":
            chart_body_holder.content = _build_donut_chart_view(
                cats, spent, budget, health_score, health_color
            )
        elif active_chart_mode[0] == "COLUMN":
            chart_body_holder.content = _build_column_chart_view(cats)
        else:
            chart_body_holder.content = _build_gauge_grid_view(
                cats, health_score, health_status, health_color, ideal_spend
            )

    render_chart_section()

    def on_export_click(e) -> None:
        out_path = export_transactions_csv()
        _notify(page, f"Exported CSV Ledger: {os.path.basename(out_path)}", "#10B981")

    controls_list = [
        # --- 0. ACTIVE LIVE MODULE BANNER ---
        ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "🟢 [LIVE MODULE] Saurabh Yadav • Spend Insights & Charts UI",
                        size=11,
                        weight=ft.FontWeight.BOLD,
                        color="#10B981",
                        expand=True,
                    ),
                    ft.Text(
                        f"Rs.{spent:,.0f} / Rs.{budget:,.0f}",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color="#F8FAFC",
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=_pad(10, 6, 10, 6),
            bgcolor="#0F172A",
            border=_border("#10B981", 1.0),
            border_radius=8,
        ),
        # --- 1. INTERACTIVE SPENDING BREAKDOWN CHART CARD (Donut / Column / Gauge) ---
        ft.Container(
            padding=_pad(14, 12, 14, 14),
            bgcolor="#1E293B",
            border=_border("#334155", 1.2),
            border_radius=14,
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "Spending Breakdown",
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color="#FFFFFF",
                                    ),
                                    ft.Text(
                                        f"{txn_count} UPI Txns  •  {anomaly_count} Z-Spikes  •  Health {health_score}/100",
                                        size=10,
                                        color="#94A3B8",
                                    ),
                                ],
                                spacing=1,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    "This Month",
                                    size=10,
                                    weight=ft.FontWeight.BOLD,
                                    color="#38BDF8",
                                ),
                                padding=_pad(8, 4, 8, 4),
                                bgcolor="#0F172A",
                                border=_border("#38BDF8", 1.0),
                                border_radius=6,
                            ),
                        ]
                    ),
                    mode_tabs_row,
                    chart_body_holder,
                ],
                spacing=10,
            ),
        ),
        # --- 2. SECTION HEADER ---
        ft.Row(
            [
                ft.Text(
                    "Category Progress & Status",
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color="#F8FAFC",
                ),
                ft.Text(
                    "Tap any chart tab above to switch view",
                    size=10,
                    color="#94A3B8",
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    ]

    # --- 3. MOCKUP-STYLE CATEGORY PROGRESS CARDS WITH ICON TILES & MINI-GAUGES ---
    for c in cats:
        c_name = str(c.get("name", "Category"))
        c_spent = float(c.get("spent", 0.0))
        c_limit = max(1.0, float(c.get("limit") or c.get("budget_limit") or 1.0))
        c_count = c.get("count")
        pct = (c_spent / c_limit) * 100.0
        meta = _cat_meta(c_name)

        if pct >= 85.0:
            status_txt, status_col, pill_bg = "CRITICAL", "#FFFFFF", "#EF4444"
        elif pct >= 60.0:
            status_txt, status_col, pill_bg = "WATCH", "#0B0F19", "#F59E0B"
        else:
            status_txt, status_col, pill_bg = "HEALTHY", "#0B0F19", "#10B981"

        title_str = f"{c_name} ({c_count} txns)" if c_count is not None else c_name

        controls_list.append(
            ft.Container(
                padding=_pad(12, 10, 12, 10),
                bgcolor="#1E293B",
                border=_border(pill_bg if pct >= 85.0 else "#334155", 1.0),
                border_radius=12,
                content=ft.Row(
                    [
                        # Left Colored Category Icon Tile (Matches reference UI screenshot)
                        ft.Container(
                            width=42,
                            height=42,
                            bgcolor=meta["bg"],
                            border=_border(meta["color"], 1.2),
                            border_radius=10,
                            alignment=_center_align(),
                            content=ft.Text(meta["emoji"], size=18),
                        ),
                        # Middle Category Progress & Figures
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            title_str,
                                            size=13,
                                            weight=ft.FontWeight.BOLD,
                                            color="#FFFFFF",
                                            expand=True,
                                            no_wrap=True,
                                        ),
                                        ft.Container(
                                            content=ft.Text(
                                                status_txt,
                                                size=9,
                                                weight=ft.FontWeight.BOLD,
                                                color=status_col,
                                            ),
                                            bgcolor=pill_bg,
                                            padding=_pad(7, 2, 7, 2),
                                            border_radius=6,
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.ProgressBar(
                                    value=min(1.0, max(0.0, pct / 100.0)),
                                    color=pill_bg if pct >= 85.0 else meta["color"],
                                    bgcolor="#0F172A",
                                    height=7,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"Rs.{c_spent:,.0f} / Rs.{c_limit:,.0f}",
                                            size=10,
                                            weight=ft.FontWeight.W_600,
                                            color="#E2E8F0",
                                        ),
                                        ft.Text(
                                            f"{pct:.1f}% used",
                                            size=10,
                                            weight=ft.FontWeight.BOLD,
                                            color=pill_bg if pct >= 85.0 else "#94A3B8",
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                ),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

    # --- 4. PROMINENT BOTTOM EXPORT CSV BUTTON (Matches reference UI screenshot) ---
    controls_list.append(
        ft.Container(
            content=ft.Row(
                [
                    ft.Text(
                        "📥  Export Monthly CSV Ledger",
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color="#FFFFFF",
                    )
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=44,
            bgcolor="#EA580C",
            border=_border("#F97316", 1.2),
            border_radius=12,
            alignment=_center_align(),
            on_click=on_export_click,
        )
    )

    return ft.Container(
        expand=True,
        padding=_pad(14, 14, 14, 14),
        content=ft.ListView(controls=controls_list, spacing=10, expand=True),
    )


# ============================================================================
# 4. MANDATORY VALUE-VALIDATING SELF-TEST FOOTER (Rule 4)
# ============================================================================
if __name__ == "__main__":
    ensure_db_ready()
    live_summary = get_dashboard_summary()

    assert live_summary.get("spent_this_month", 0.0) > 0.0, "spent_this_month must be > 0 from tracker_dev.db!"
    cats_list = live_summary.get("category_breakdown", [])
    assert len(cats_list) >= 5, "category_breakdown must have seeded categories!"
    assert all(
        float(c.get("limit") or c.get("budget_limit") or 0.0) > 1.0 for c in cats_list
    ), "Category budget limits must be > 1.0 (no / Rs.1 fallback bug)!"

    dash_ctrl = build_dashboard_view(None, live_summary)
    assert isinstance(dash_ctrl, ft.Control), "build_dashboard_view must return an ft.Control instance!"

    print(
        f"[PASS] Saurabh Creative Analytics Dashboard Verified! "
        f"Total=Rs.{live_summary['spent_this_month']:,.0f} / Budget=Rs.{live_summary['monthly_budget']:,.0f} "
        f"| Categories={len(cats_list)} | Health={live_summary['health_score']}/100"
    )