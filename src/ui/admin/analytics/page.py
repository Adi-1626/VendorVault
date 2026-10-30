"""
Admin → Analytics page.

One outer QScrollArea, fixed-height QPainter charts, scroll-free tables and
data loaded on a pool thread. All numbers come from
:func:`src.logic.analytics_engine.build_snapshot`.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Dict, Optional, Set, Tuple

from PySide6.QtCore import QDate, QPoint, Qt, QThreadPool, QTimer
from PySide6.QtWidgets import (
    QDateEdit, QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from src.logic.analytics_engine import (
    LOW_STOCK_THRESHOLD, PRESETS, REORDER_TARGET_DAYS, VELOCITY_WINDOW_DAYS, Snapshot, build_snapshot, delta,
    preset_period,
)
from src.ui import theme as T
from src.ui.admin.analytics import export as exporter
from src.ui.admin.analytics.charts import PALETTE, Donut, Heatmap, MiniBar, TrendChart, hour_range
from src.ui.admin.analytics.components import (
    Column, DeltaPill, EmptyState, GridTable, KpiCard, ResponsiveGrid, ResponsiveRow, SectionCard,
    ToggleSwitch, clear_layout, elided_label,
)
from src.ui.admin.analytics.fmt import date_range_label, inr_smart, number, pct
from src.ui.admin.analytics.worker import SnapshotJob
from src.ui.widgets import Card, SegmentedControl, StatusBadge, make_button, make_label

BUCKET_NAME = {"hour": "Hourly", "day": "Daily", "week": "Weekly", "month": "Monthly"}
PERIOD_NOUN = {"Today": "yesterday", "This year": "same period last year"}


class DateRangePopover(QFrame):
    """Popup with two date pickers for the Custom range."""

    def __init__(self, parent: QWidget, on_apply: Callable[[date, date], None], on_cancel: Callable[[], None]):
        super().__init__(parent, Qt.Popup)
        self.on_apply, self.on_cancel = on_apply, on_cancel
        self._applied = False
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("RangePopover")
        self.setStyleSheet(f"QFrame#RangePopover {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER_2};"
                           f" border-radius: 12px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lay.addWidget(make_label("Custom range", size=13, weight=600))
        row = QHBoxLayout()
        row.setSpacing(8)
        self.start = QDateEdit()
        self.end = QDateEdit()
        for d in (self.start, self.end):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd MMM yyyy")
            d.setMaximumDate(QDate.currentDate())
            d.setFixedWidth(140)
        row.addWidget(self.start)
        row.addWidget(make_label("→", role="faint"))
        row.addWidget(self.end)
        lay.addLayout(row)
        btns = QHBoxLayout()
        btns.addStretch(1)
        cancel = make_button("Cancel", variant="ghost", size="sm")
        cancel.clicked.connect(self.close)
        apply_btn = make_button("Apply", variant="primary", size="sm")
        apply_btn.clicked.connect(self._apply)
        btns.addWidget(cancel)
        btns.addWidget(apply_btn)
        lay.addLayout(btns)

    def open_at(self, anchor: QWidget, start: date, end: date) -> None:
        self._applied = False
        self.start.setDate(QDate(start.year, start.month, start.day))
        self.end.setDate(QDate(end.year, end.month, end.day))
        self.adjustSize()
        self.move(anchor.mapToGlobal(QPoint(0, anchor.height() + 6)))
        self.show()

    def _apply(self) -> None:
        self._applied = True
        a, b = self.start.date().toPython(), self.end.date().toPython()
        self.close()
        self.on_apply(a, b)

    def hideEvent(self, e) -> None:  # noqa: N802
        super().hideEvent(e)
        if not self._applied:
            self.on_cancel()


class AnalyticsPage(QWidget):
    """Analytics deep dive (embedded in the admin dashboard)."""

    def __init__(self, parent: Optional[QWidget] = None, on_navigate: Optional[Callable[[str], None]] = None,
                 autoload: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Analytics")
        self.on_navigate = on_navigate
        self.preset = "30D"
        self._last_preset = "30D"
        self.custom: Optional[Tuple[date, date]] = None
        self.compare = True
        self.snapshot: Optional[Snapshot] = None
        self.is_loading = autoload      # first load is scheduled right away
        self._request = 0
        self._jobs: Set[SnapshotJob] = set()
        self._build()
        if autoload:
            QTimer.singleShot(0, self.refresh)

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("AnalyticsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(self.scroll)
        self.body = QWidget()
        self.body.setObjectName("AnalyticsBody")
        self.scroll.setWidget(self.body)
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(32, 28, 32, 36)
        lay.setSpacing(16)
        self.layout_main = lay

        # Header ---------------------------------------------------------
        head = QHBoxLayout()
        head.setSpacing(8)
        titles = QVBoxLayout()
        titles.setSpacing(6)
        title = make_label("Analytics", size=24, weight=600)
        self.subtitle = make_label("", role="muted", size=14)
        titles.addWidget(title)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        self.updated = make_label("", role="faint", size=12)
        head.addWidget(self.updated, 0, Qt.AlignVCenter)
        head.addSpacing(6)
        self.refresh_btn = make_button("Refresh")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setToolTip("Reload the numbers (F5)")
        self.refresh_btn.setShortcut("F5")
        self.refresh_btn.clicked.connect(self.refresh)
        head.addWidget(self.refresh_btn, 0, Qt.AlignVCenter)
        self.export_btn = make_button("Export", variant="light")
        self.export_btn.setFixedSize(92, 36)
        menu = QMenu(self.export_btn)
        menu.addAction("Export CSV…", lambda: self.export_csv())
        menu.addAction("Export PDF…", lambda: self.export_pdf())
        self.export_menu = menu
        self.export_btn.setMenu(menu)
        head.addWidget(self.export_btn, 0, Qt.AlignVCenter)
        lay.addLayout(head)

        # Controls -------------------------------------------------------
        ctl = QHBoxLayout()
        ctl.setSpacing(12)
        self.range_control = SegmentedControl(PRESETS, height=36)
        self.range_control.setFixedWidth(470)
        self.range_control.setCurrentText(self.preset)
        self.range_control.currentChanged.connect(self._on_preset)
        ctl.addWidget(self.range_control)
        self.range_chip = QPushButton("")
        self.range_chip.setCursor(Qt.PointingHandCursor)
        self.range_chip.setFixedHeight(36)
        self.range_chip.setToolTip("Pick a custom date range")
        self.range_chip.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {T.BORDER}; border-radius: 10px;"
            f" color: {T.MUTED}; padding: 0 14px; font-weight: 500; }}"
            f"QPushButton:hover {{ color: {T.TEXT}; border-color: {T.BORDER_2}; }}")
        self.range_chip.clicked.connect(self._open_custom)
        ctl.addWidget(self.range_chip)
        ctl.addStretch(1)
        self.compare_toggle = ToggleSwitch("Compare to previous period", True)
        self.compare_toggle.toggled.connect(self._on_compare)
        ctl.addWidget(self.compare_toggle)
        lay.addLayout(ctl)
        self.popover = DateRangePopover(self, self._apply_custom, self._cancel_custom)
        lay.addSpacing(4)

        # KPIs -----------------------------------------------------------
        self.kpis: Dict[str, KpiCard] = {
            "revenue": KpiCard("revenue", "Revenue", "Bill totals after discount, including GST."),
            "profit": KpiCard("profit", "Gross profit",
                              "Net sales (after discount, before GST) minus cost price × units, for items with a "
                              "cost price."),
            "bills": KpiCard("bills", "Bills"),
            "avg_bill": KpiCard("avg_bill", "Avg bill value", "Revenue ÷ bills."),
            "units": KpiCard("units", "Units sold"),
            "items_per_bill": KpiCard("items_per_bill", "Items per bill", "Units sold ÷ bills (basket size)."),
        }
        self.kpi_grid = ResponsiveGrid(min_tile=250, max_cols=4)
        self.kpi_grid.set_tiles(list(self.kpis.values()))
        lay.addWidget(self.kpi_grid)

        # Revenue chart --------------------------------------------------
        self.trend_card = SectionCard("Revenue over time")
        legend = QHBoxLayout()
        legend.setSpacing(14)
        self.legend_cur = make_label("●  This period", size=12, weight=500)
        self.legend_cur.setStyleSheet(f"color: {T.ACCENT}; font-size: 12px; font-weight: 500;")
        self.legend_prev = make_label("- -  Previous period", role="muted", size=12, weight=500)
        legend.addWidget(self.legend_cur)
        legend.addWidget(self.legend_prev)
        self.trend_card.actions.addLayout(legend)
        self.trend = TrendChart(300)
        self.trend_card.content.addWidget(self.trend)
        lay.addWidget(self.trend_card)

        # Heatmap + categories ------------------------------------------
        row1 = ResponsiveRow(980)
        self.heat_card = SectionCard("When customers buy", "Revenue by weekday and hour")
        self.heatmap = Heatmap()
        row1.add(self.heat_card, 3)
        self.cat_card = SectionCard("Sales by category", "Share of item sales")
        row1.add(self.cat_card, 2)
        lay.addWidget(row1)
        self.row_heat = row1

        # Products ------------------------------------------------------
        row2 = ResponsiveRow(1080)
        self.top_card = SectionCard("Top products", "By item sales in this period")
        row2.add(self.top_card, 3)
        self.slow_card = SectionCard("Slow movers", f"In stock, no sales in the last {VELOCITY_WINDOW_DAYS} days")
        row2.add(self.slow_card, 2)
        lay.addWidget(row2)

        # Inventory health ---------------------------------------------
        self.inv_card = SectionCard("Inventory health",
                                    f"As of today · days of cover uses the last {VELOCITY_WINDOW_DAYS} days of sales")
        inv_btn = make_button("Open inventory", size="sm")
        inv_btn.setFixedHeight(30)
        inv_btn.clicked.connect(lambda: self.on_navigate and self.on_navigate("inventory"))
        inv_btn.setVisible(self.on_navigate is not None)
        self.inv_card.actions.addWidget(inv_btn)
        lay.addWidget(self.inv_card)

        # Profitability -------------------------------------------------
        self.profit_card = SectionCard("Profitability", "Net sales after discount, before GST")
        lay.addWidget(self.profit_card)

        # Payments (only when payment records exist) ---------------------
        self.pay_card = SectionCard("Payment methods")
        self.pay_card.hide()
        lay.addWidget(self.pay_card)
        lay.addStretch(1)

        self._update_range_labels()

    # ------------------------------------------------------------- controls
    def _period(self):
        return preset_period(self.preset, date.today(), self.custom)

    def _update_range_labels(self) -> None:
        p = self._period()
        label = date_range_label(p.start, p.end)
        self.range_chip.setText(label)
        self.subtitle.setText(f"Sales, stock and margins · {label}")

    def _on_preset(self, preset: str) -> None:
        if preset == "Custom":
            self._open_custom()
            return
        self.preset = self._last_preset = preset
        self._update_range_labels()
        self.refresh()

    def _open_custom(self) -> None:
        p = self._period()
        self.popover.open_at(self.range_chip, p.start, p.end)

    def _apply_custom(self, a: date, b: date) -> None:
        self.set_custom_range(a, b)

    def _cancel_custom(self) -> None:
        if self.preset != "Custom":
            self.range_control.blockSignals(True)
            self.range_control.setCurrentText(self._last_preset)
            self.range_control.blockSignals(False)

    def set_custom_range(self, start: date, end: date, blocking: bool = False) -> None:
        self.custom = (min(start, end), max(start, end))
        self.preset = "Custom"
        self.range_control.blockSignals(True)
        self.range_control.setCurrentText("Custom")
        self.range_control.blockSignals(False)
        self._update_range_labels()
        self.refresh(blocking=blocking)

    def set_preset(self, preset: str, blocking: bool = False) -> None:
        self.range_control.blockSignals(True)
        self.range_control.setCurrentText(preset)
        self.range_control.blockSignals(False)
        self.preset = self._last_preset = preset
        self._update_range_labels()
        self.refresh(blocking=blocking)

    def _on_compare(self, on: bool) -> None:
        self.compare = on
        if self.snapshot:
            self.render(self.snapshot)

    # ----------------------------------------------------------------- data
    def refresh(self, blocking: bool = False) -> None:
        self._request += 1
        rid = self._request
        self.is_loading = True
        self.updated.setText("Updating…")
        self.refresh_btn.setEnabled(False)
        if blocking:
            try:
                self._on_done(rid, build_snapshot(self.preset, self.custom))
            except Exception as e:  # noqa: BLE001
                self._on_failed(rid, repr(e))
            return
        job = SnapshotJob(rid, self.preset, self.custom)
        job.signals.done.connect(self._on_done)
        job.signals.failed.connect(self._on_failed)
        self._jobs.add(job)
        QThreadPool.globalInstance().start(job)

    def wait_until_loaded(self, timeout_ms: int = 10000) -> bool:
        """Test helper: process events until the current load finished."""
        from PySide6.QtCore import QCoreApplication, QElapsedTimer
        t = QElapsedTimer()
        t.start()
        while self.is_loading and t.elapsed() < timeout_ms:
            QThreadPool.globalInstance().waitForDone(50)
            QCoreApplication.processEvents()
        return not self.is_loading

    def _finish_job(self, rid: int) -> None:
        self._jobs = {j for j in self._jobs if j.request_id != rid}

    def _on_done(self, rid: int, snap: Snapshot) -> None:
        self._finish_job(rid)
        if rid != self._request:
            return          # a newer request is in flight
        self.is_loading = False
        self.refresh_btn.setEnabled(True)
        self.snapshot = snap
        self.render(snap)
        self.updated.setText(f"Updated {snap.generated_at.strftime('%H:%M')}")
        self.updated.setStyleSheet(f"color: {T.FAINT}; font-size: 12px;")

    def _on_failed(self, rid: int, err: str) -> None:
        self._finish_job(rid)
        if rid != self._request:
            return
        self.is_loading = False
        self.refresh_btn.setEnabled(True)
        self.updated.setText("Couldn't load data — try Refresh")
        self.updated.setStyleSheet(f"color: {T.DANGER}; font-size: 12px;")
        print(f"Analytics: load failed\n{err}")

    # --------------------------------------------------------------- render
    def render(self, s: Snapshot) -> None:
        self._render_kpis(s)
        self._render_trend(s)
        self._render_heatmap(s)
        self._render_categories(s)
        self._render_top(s)
        self._render_slow(s)
        self._render_inventory(s)
        self._render_profit(s)
        self._render_payments(s)

    def _vs(self, s: Snapshot) -> str:
        if s.same_time:
            return "yesterday by now"
        return PERIOD_NOUN.get(s.preset, "previous period")

    def _render_kpis(self, s: Snapshot) -> None:
        cur, prev = s.summary, s.prev_summary
        prev_label = date_range_label(s.previous.start, s.previous.end)
        cmp = self.compare

        def d(a: float, b: float) -> Tuple[str, str]:
            if not cmp:
                return ("", "neutral")
            x = delta(a, b)
            return (x.text if x.text != "—" else "", x.tone)

        def cap(prev_text: str) -> str:
            if not cmp or (prev.bills == 0 and cur.bills == 0):
                return ""
            return f"vs {prev_text} {self._vs(s)}"

        def tip(prev_text: str) -> str:
            when = f"{prev_label}, up to {s.generated_at.strftime('%H:%M')}" if s.same_time else prev_label
            return f"Previous period ({when}): {prev_text}"

        sp = s.sparks
        self.kpis["revenue"].set_data(inr_smart(cur.revenue), cap(inr_smart(prev.revenue)),
                                      d(cur.revenue, prev.revenue), tip(inr_smart(prev.revenue)), sp.get("revenue", []))
        gp = cur.gross_profit
        if gp is None and cur.bills == 0:
            self.kpis["profit"].set_data("—", "", ("", "neutral"), "", [], muted=True)
        elif gp is None:
            self.kpis["profit"].set_data("—", "Add cost prices in Inventory to see profit", ("", "neutral"),
                                         "No cost prices for the items sold in this period.", [], muted=True)
        else:
            c = f"{pct(cur.gross_margin)} margin"
            if cur.cost_coverage < 0.95:
                c += f" · {cur.cost_coverage * 100:.0f}% of sales costed"
            pgp = prev.gross_profit or 0.0
            self.kpis["profit"].set_data(inr_smart(gp), c, d(gp, pgp), tip(inr_smart(pgp)), sp.get("profit", []))
        self.kpis["bills"].set_data(number(cur.bills), cap(number(prev.bills)), d(cur.bills, prev.bills),
                                    tip(number(prev.bills)), sp.get("bills", []))
        self.kpis["avg_bill"].set_data(inr_smart(cur.avg_bill),
                                       cap(inr_smart(prev.avg_bill)), d(cur.avg_bill, prev.avg_bill),
                                       tip(inr_smart(prev.avg_bill)), sp.get("avg_bill", []))
        self.kpis["units"].set_data(number(cur.units), cap(number(prev.units)), d(cur.units, prev.units),
                                    tip(number(prev.units)), sp.get("units", []))
        self.kpis["items_per_bill"].set_data(f"{cur.items_per_bill:.1f}" if cur.bills else "—",
                                             cap(f"{prev.items_per_bill:.1f}") if prev.bills else cap("—"),
                                             d(round(cur.items_per_bill, 2), round(prev.items_per_bill, 2)),
                                             tip(f"{prev.items_per_bill:.2f}"), sp.get("items_per_bill", []))

    def _render_trend(self, s: Snapshot) -> None:
        self.trend_card.set_subtitle(f"{BUCKET_NAME[s.bucket]} · bill totals incl. GST")
        empty = "No sales in this period" if s.has_any_bills else "No bills yet — sales from the counter will show here"
        self.trend.set_data(s.revenue_series, s.labels, s.long_labels, s.prev_revenue_series, s.prev_long_labels,
                            show_prev=self.compare, empty_text=empty)
        self.legend_prev.setVisible(self.trend.show_prev)

    def _empty(self, card: SectionCard, title: str, hint: str, height: int = 220) -> None:
        clear_layout(card.content)
        card.content.addWidget(EmptyState(title, hint, height=height))

    def _no_sales_hint(self, s: Snapshot) -> str:
        return "Try a longer date range." if s.has_any_bills else "Bills you ring up at the counter will show up here."

    def _render_heatmap(self, s: Snapshot) -> None:
        if s.summary.bills == 0:
            self.heat_card.set_subtitle("Revenue by weekday and hour")
            clear_layout_keep(self.heat_card.content, keep=self.heatmap)
            self.heatmap.hide()
            self.heat_card.content.addWidget(EmptyState("No sales in this period", self._no_sales_hint(s), height=250))
            return
        hrs = [h for h in range(24) if any(s.heatmap[d][h] > 0 for d in range(7))]
        lo, hi = (min(hrs + [9]), max(hrs + [20])) if hrs else (9, 20)
        self.heatmap.set_data(s.heatmap, s.heatmap_bills, (lo, hi))
        clear_layout_keep(self.heat_card.content, keep=self.heatmap)
        self.heat_card.content.addWidget(self.heatmap)
        self.heatmap.show()
        pk = self.heatmap.peak()
        if pk:
            r, h, v = pk
            self.heat_card.set_subtitle(f"Revenue by weekday and hour · busiest: {Heatmap.DAYS[r]} {hour_range(h)}")
        # legend
        leg = QHBoxLayout()
        leg.setContentsMargins(40, 12, 0, 0)
        leg.setSpacing(6)
        leg.addWidget(make_label("Less", role="faint", size=11))
        for a in (0.14, 0.35, 0.6, 0.8, 1.0):
            sw = QLabel()
            sw.setFixedSize(14, 10)
            sw.setStyleSheet(f"background: {T.rgba(T.ACCENT, a)}; border-radius: 3px;")
            leg.addWidget(sw)
        leg.addWidget(make_label("More", role="faint", size=11))
        leg.addStretch(1)
        self.heat_card.content.addLayout(leg)

    def _render_categories(self, s: Snapshot) -> None:
        clear_layout(self.cat_card.content)
        if not s.categories:
            self.cat_card.content.addWidget(EmptyState("No category data", self._no_sales_hint(s), height=250))
            return
        row = QHBoxLayout()
        row.setSpacing(20)
        donut = Donut(168)
        total = sum(c.sales for c in s.categories)
        donut.set_data([c.sales for c in s.categories], PALETTE, inr_smart(total), f"{len(s.categories)} categories")
        row.addWidget(donut, 0, Qt.AlignTop)
        legend = QVBoxLayout()
        legend.setSpacing(10)
        for i, c in enumerate(s.categories):
            line = QHBoxLayout()
            line.setSpacing(8)
            dot = QLabel()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet(f"background: {PALETTE[i % len(PALETTE)]}; border-radius: 3px;")
            line.addWidget(dot)
            name = elided_label(c.category, 13, 500)
            line.addWidget(name, 1)
            line.addWidget(make_label(pct(c.share, 0), size=13, weight=600))
            col = QVBoxLayout()
            col.setSpacing(2)
            col.addLayout(line)
            sub = make_label(f"{inr_smart(c.sales)} · {number(c.units)} units", role="faint", size=11)
            sub.setContentsMargins(18, 0, 0, 0)
            col.addWidget(sub)
            legend.addLayout(col)
        legend.addStretch(1)
        holder = QWidget()
        holder.setLayout(legend)
        holder.setMaximumWidth(420)
        row.addWidget(holder, 1)
        row.addStretch(0)
        self.cat_card.content.addLayout(row)

    def _render_top(self, s: Snapshot) -> None:
        clear_layout(self.top_card.content)
        if not s.top_products:
            self.top_card.content.addWidget(EmptyState("No products sold", self._no_sales_hint(s), height=240))
            return
        cols = [Column("#", 0, Qt.AlignHCenter, 24), Column("Product", 5), Column("Units", 2, Qt.AlignRight),
                Column("Sales", 2, Qt.AlignRight), Column("Share", 3)]
        if self.compare:
            cols.append(Column("vs prev", 2, Qt.AlignRight))
        table = GridTable(cols, row_height=46)
        rows = []
        for t in s.top_products:
            name_box = QWidget()
            nb = QVBoxLayout(name_box)
            nb.setContentsMargins(0, 0, 0, 0)
            nb.setSpacing(1)
            nb.addWidget(elided_label(t.name, 13, 500))
            nb.addWidget(elided_label(t.category, 11, 400, role="faint"))
            name_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            share = QWidget()
            sl = QHBoxLayout(share)
            sl.setContentsMargins(0, 0, 0, 0)
            sl.setSpacing(8)
            sl.addWidget(MiniBar(t.share / max(x.share for x in s.top_products)), 1)
            pl = make_label(pct(t.share, 0), role="muted", size=12)
            pl.setFixedWidth(34)
            pl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            sl.addWidget(pl)
            share.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cells = [(str(t.rank), "faint"), name_box, number(t.units), (inr_smart(t.sales), "strong"), share]
            if self.compare:
                pill = DeltaPill()
                pill.set_delta(t.trend.text, t.trend.tone)
                cells.append(pill)
            rows.append(cells)
        table.set_rows(rows)
        self.top_card.content.addWidget(table)

    def _render_slow(self, s: Snapshot) -> None:
        clear_layout(self.slow_card.content)
        if not s.slow_movers:
            self.slow_card.content.addWidget(EmptyState(
                "Everything is moving", f"Every product in stock sold at least once in the last {VELOCITY_WINDOW_DAYS} days.",
                tone="success", height=240))
            return
        total = sum(m.value for m in s.slow_movers)
        self.slow_card.set_subtitle(f"In stock, no sales in {VELOCITY_WINDOW_DAYS} days · {inr_smart(total)} tied up")
        table = GridTable([Column("Product", 5), Column("Stock", 2, Qt.AlignRight),
                           Column("Value", 3, Qt.AlignRight), Column("Last sold", 3, Qt.AlignRight)], row_height=46)
        rows = []
        today = date.today()
        for m in s.slow_movers:
            if m.last_sold is None:
                last = ("Never", "faint")
            else:
                days = (today - m.last_sold).days
                last = (f"{days}d ago" if days < 365 else ">1 year", "muted")
            rows.append([m.name, number(m.stock), (inr_smart(m.value), "strong"), last])
        table.set_rows(rows)
        self.slow_card.content.addWidget(table)
        self.slow_card.content.addSpacing(16)
        tip = make_label(f"Tip: a discount or combo offer on these frees up {inr_smart(total)} of cash.",
                         role="muted", size=12)
        tip.setWordWrap(True)
        tip.setContentsMargins(10, 0, 10, 0)
        self.slow_card.content.addWidget(tip)

    def _render_inventory(self, s: Snapshot) -> None:
        clear_layout(self.inv_card.content)
        inv = s.inventory
        if inv.products == 0:
            self.inv_card.content.addWidget(EmptyState("No products yet", "Add products in Inventory to track stock.",
                                                       height=200))
            return
        tiles = ResponsiveGrid(min_tile=200, max_cols=4, spacing=12)
        stats = [
            ("Stock value (cost)", inr_smart(inv.stock_value_cost),
             f"{inv.missing_cost} item{'s' if inv.missing_cost != 1 else ''} without cost price" if inv.missing_cost
             else f"{inv.products} active products", "neutral"),
            ("Stock value (MRP)", inr_smart(inv.stock_value_mrp), "Retail value of stock on hand", "neutral"),
            ("Low stock", number(inv.low_stock), f"At or below {LOW_STOCK_THRESHOLD} units",
             "warning" if inv.low_stock else "success"),
            ("Out of stock", number(inv.out_of_stock), "Can't be sold right now",
             "danger" if inv.out_of_stock else "success"),
        ]
        cards = []
        for title, value, sub, tone in stats:
            c = Card(inset=True, padding=(16, 14, 16, 14), spacing=4)
            c.setFixedHeight(96)
            c.body.addWidget(make_label(title, role="muted", size=12, weight=500))
            v = make_label(value, size=20, weight=600)
            if tone in ("warning", "danger") and value != "0":
                v.setStyleSheet(f"color: {T.WARNING if tone == 'warning' else T.DANGER}; font-size: 20px; font-weight: 600;")
            c.body.addWidget(v)
            sl = make_label(sub, role="faint", size=11)
            sl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            c.body.addWidget(sl)
            cards.append(c)
        tiles.set_tiles(cards)
        self.inv_card.content.addWidget(tiles)
        self.inv_card.content.addSpacing(20)
        head = QHBoxLayout()
        head.addWidget(make_label("Restock suggestions", size=13, weight=600))
        head.addSpacing(6)
        head.addWidget(make_label(f"Suggested quantity covers {REORDER_TARGET_DAYS} days of sales", role="faint", size=12))
        head.addStretch(1)
        self.inv_card.content.addLayout(head)
        self.inv_card.content.addSpacing(8)
        if not inv.attention:
            self.inv_card.content.addWidget(EmptyState("Stock levels look healthy",
                                                       "Nothing is out of stock, low, or about to run out.",
                                                       tone="success", height=150))
            return
        table = GridTable([Column("Product", 5), Column("Category", 3), Column("In stock", 2, Qt.AlignRight),
                           Column("Sold / day", 2, Qt.AlignRight), Column("Days of cover", 2, Qt.AlignRight),
                           Column("Reorder", 2, Qt.AlignRight), Column("Status", 3, Qt.AlignRight)], row_height=44)
        rows = []
        for r in inv.attention:
            if r.days_cover is None:
                cover = "—"
            elif r.days_cover < 1:
                cover = "< 1 day"
            else:
                cover = f"{r.days_cover:.0f} day{'s' if round(r.days_cover) != 1 else ''}"
            stock_cell = (number(r.stock), "danger") if r.stock <= 0 else (number(r.stock), "strong")
            rows.append([r.name, (r.category, "muted"), stock_cell,
                         (f"{r.avg_daily:.1f}" if r.avg_daily else "—", "muted"),
                         (cover, "warning" if r.days_cover is not None and r.days_cover < 7 else "muted"),
                         (f"+{number(r.reorder_qty)}" if r.reorder_qty else "—", "accent" if r.reorder_qty else "faint"),
                         StatusBadge(r.status, r.tone)])
        table.set_rows(rows)
        self.inv_card.content.addWidget(table)

    def _render_profit(self, s: Snapshot) -> None:
        clear_layout(self.profit_card.content)
        if s.summary.bills == 0:
            self.profit_card.content.addWidget(EmptyState("No sales in this period", self._no_sales_hint(s), height=180))
            return
        if s.summary.gross_profit is None:
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.addWidget(EmptyState("Margins need cost prices",
                                    "Add a cost price to products in Inventory and profit, margin by product and "
                                    "items sold below cost will appear here.", height=190))
            if self.on_navigate:
                b = make_button("Add cost prices", variant="primary", size="sm")
                b.clicked.connect(lambda: self.on_navigate("inventory"))
                bl.addWidget(b, 0, Qt.AlignHCenter)
            self.profit_card.content.addWidget(box)
            return
        cov = s.summary.cost_coverage
        self.profit_card.set_subtitle("Net sales after discount, before GST"
                                      + (f" · {cov * 100:.0f}% of sales have a cost price" if cov < 0.95 else ""))
        row = ResponsiveRow(1000, spacing=28)
        # by category
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(14)
        ll.addWidget(make_label("Margin by category", size=13, weight=600))
        mx = max((abs(m.margin) for m in s.margin_by_category), default=1) or 1
        for m in s.margin_by_category:
            grp = QVBoxLayout()
            grp.setSpacing(7)
            top = QHBoxLayout()
            top.addWidget(elided_label(m.name, 13, 500), 1)
            top.addWidget(make_label(inr_smart(m.profit), role="muted", size=12))
            top.addSpacing(10)
            ml = make_label(pct(m.margin), size=13, weight=600)
            ml.setFixedWidth(52)
            ml.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if m.margin < 0:
                ml.setStyleSheet(f"color: {T.DANGER}; font-size: 13px; font-weight: 600;")
            top.addWidget(ml)
            grp.addLayout(top)
            grp.addWidget(MiniBar(abs(m.margin) / mx, T.DANGER if m.margin < 0 else T.SUCCESS, 5))
            ll.addLayout(grp)
        ll.addStretch(1)
        row.add(left, 2)
        # by product
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        rl.addWidget(make_label("Most profitable products", size=13, weight=600))
        table = GridTable([Column("Product", 5), Column("Net sales", 2, Qt.AlignRight),
                           Column("Profit", 2, Qt.AlignRight), Column("Margin", 2, Qt.AlignRight)], row_height=42)
        table.set_rows([[m.name, (inr_smart(m.sales), "muted"),
                         (inr_smart(m.profit), "danger" if m.profit < 0 else "strong"),
                         (pct(m.margin), "danger" if m.margin < 0 else "success")] for m in s.margin_by_product])
        rl.addWidget(table)
        rl.addStretch(1)
        row.add(right, 3)
        self.profit_card.content.addWidget(row)
        if s.below_cost:
            self.profit_card.content.addSpacing(18)
            warn = QFrame()
            warn.setObjectName("BelowCost")
            warn.setAttribute(Qt.WA_StyledBackground, True)
            warn.setStyleSheet(f"QFrame#BelowCost {{ background: {T.DANGER_SOFT}; border: 1px solid "
                               f"{T.rgba(T.DANGER, 0.3)}; border-radius: 10px; }}")
            wl = QHBoxLayout(warn)
            wl.setContentsMargins(16, 12, 16, 12)
            names = ", ".join(f"{m.name} ({inr_smart(m.profit)})" for m in s.below_cost[:4])
            more = f" and {len(s.below_cost) - 4} more" if len(s.below_cost) > 4 else ""
            t = make_label(f"Selling below cost: {names}{more}. Check the MRP or cost price in Inventory.", size=13)
            t.setWordWrap(True)
            t.setStyleSheet(f"color: {T.DANGER}; font-size: 13px;")
            wl.addWidget(t, 1)
            self.profit_card.content.addWidget(warn)

    def _render_payments(self, s: Snapshot) -> None:
        clear_layout(self.pay_card.content)
        if not s.payments:
            self.pay_card.hide()
            return
        self.pay_card.show()
        total = sum(a for _m, a, _n in s.payments) or 1
        for i, (m, a, n) in enumerate(s.payments):
            line = QHBoxLayout()
            line.addWidget(make_label(m.title(), size=13, weight=500), 1)
            line.addWidget(make_label(f"{n} payments", role="faint", size=12))
            line.addSpacing(12)
            line.addWidget(make_label(inr_smart(a), size=13, weight=600))
            self.pay_card.content.addLayout(line)
            self.pay_card.content.addSpacing(6)
            self.pay_card.content.addWidget(MiniBar(a / total, PALETTE[i % len(PALETTE)], 5))
            self.pay_card.content.addSpacing(12)

    # --------------------------------------------------------------- export
    def _default_name(self, ext: str) -> str:
        p = self.snapshot.period if self.snapshot else self._period()
        tail = p.start.isoformat() if p.start == p.end else f"{p.start.isoformat()}-to-{p.end.isoformat()}"
        return f"vendorvault-analytics-{tail}.{ext}"

    def export_csv(self, path: Optional[str] = None) -> Optional[str]:
        return self._export("csv", path)

    def export_pdf(self, path: Optional[str] = None) -> Optional[str]:
        return self._export("pdf", path)

    def _export(self, kind: str, path: Optional[str]) -> Optional[str]:
        if self.snapshot is None:
            return None
        if path is None:
            flt = "CSV files (*.csv)" if kind == "csv" else "PDF files (*.pdf)"
            path, _ = QFileDialog.getSaveFileName(self, f"Export analytics ({kind.upper()})", self._default_name(kind), flt)
            if not path:
                return None
        try:
            (exporter.write_csv if kind == "csv" else exporter.write_pdf)(self.snapshot, path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Export failed", str(e))
            return None
        QMessageBox.information(self, "Export", f"Saved analytics to\n{path}")
        return path


def clear_layout_keep(lay, keep: QWidget) -> None:
    """Clear ``lay`` but keep (re-parentable) ``keep`` alive."""
    while lay.count():
        it = lay.takeAt(0)
        w = it.widget()
        if w is keep:
            continue
        if w is not None:
            w.hide()
            w.deleteLater()
        elif it.layout() is not None:
            clear_layout(it.layout())
