"""
Admin dashboard: sidebar navigation + Overview page.

The existing admin screens (invoices, inventory, brands, product types,
analytics, employees) are embedded as pages in a stacked widget; each one
is created fresh when opened, exactly like the old "open window" buttons,
so they always show current data. All data reads go through the existing
services (BillingService, AnalyticsService, InventoryService,
AnalyticsEngine) plus one read-only query for POS stock levels.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QStackedWidget, QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

import config
from src.database.connection import db
from src.logic.analytics import AnalyticsService
from src.logic.billing import BillingService
from src.logic.employee_mgmt import EmployeeService
from src.logic.inventory import InventoryService
from src.models.employee import Employee
from src.ui import theme as T
from src.ui.colors import *  # noqa: F401,F403  (legacy names)
from src.ui.widgets import (
    AreaChart, Avatar, BarRow, Card, Divider, LogoMark, StatCard, StatusBadge, make_button, make_label,
    overline,
)

# Legacy colour names used by older code paths
BG = T.BG
CARD = T.SURFACE
WHITE = T.TEXT
GRAY = T.MUTED
BLUE = T.ACCENT
GREEN = T.SUCCESS
ORANGE = T.WARNING
RED = T.DANGER
PURPLE = T.ACCENT

LOW_STOCK_THRESHOLD = 10
RANGES = ["Today", "Yesterday", "Last 7 days", "Last 30 days"]


# ---------------------------------------------------------------------------
# Data helpers (read-only)
# ---------------------------------------------------------------------------
def range_bounds(label: str, today: Optional[date] = None) -> Tuple[date, date]:
    today = today or date.today()
    if label == "Yesterday":
        d = today - timedelta(days=1)
        return d, d
    if label == "Last 7 days":
        return today - timedelta(days=6), today
    if label == "Last 30 days":
        return today - timedelta(days=29), today
    return today, today


def previous_bounds(label: str, start: date, end: date) -> Tuple[date, date]:
    """Comparison window: same weekday last week for single days, else the prior period."""
    if start == end:
        d = start - timedelta(days=7)
        return d, d
    span = (end - start).days + 1
    return start - timedelta(days=span), start - timedelta(days=1)


def local_hour(created_at: Optional[str]) -> Optional[int]:
    """Bills store SQLite CURRENT_TIMESTAMP (UTC); convert to local hour."""
    if not created_at:
        return None
    try:
        dt = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone().hour


def fmt_hour(h: int) -> str:
    suffix = "a" if h < 12 else "p"
    hh = h % 12 or 12
    return f"{hh}{suffix}"


def fmt_hour_long(h: int) -> str:
    return f"{h % 12 or 12} {'AM' if h < 12 else 'PM'}"


def pos_low_stock(threshold: int = LOW_STOCK_THRESHOLD) -> List[Dict]:
    """Low-stock items from the POS catalogue (simple_products) and the
    variant inventory (views_inventory_health / reorder levels)."""
    items: List[Dict] = []
    try:
        rows = db.execute_query(
            "SELECT name, category, stock FROM simple_products WHERE is_active = 1 AND stock <= ? ORDER BY stock ASC",
            (threshold,))
        for r in rows:
            items.append({'name': r['name'], 'category': r.get('category') or '—',
                          'stock': int(r['stock'] or 0), 'reorder': threshold})
    except Exception as e:  # noqa: BLE001
        print(f"Overview: simple_products low stock unavailable: {e}")
    try:
        from src.logic.analytics_engine import AnalyticsEngine
        for r in AnalyticsEngine().inventory.get_low_stock_items(limit=20):
            name = r.get('product_name') or ''
            if r.get('variant_name'):
                name = f"{name} {r['variant_name']}"
            items.append({'name': name, 'category': r.get('product_type') or '—',
                          'stock': int(r.get('stock_quantity') or 0), 'reorder': int(r.get('reorder_level') or 0)})
    except Exception as e:  # noqa: BLE001
        print(f"Overview: variant low stock unavailable: {e}")
    items.sort(key=lambda x: (x['stock'] / x['reorder']) if x['reorder'] else x['stock'])
    return items


def stock_status(stock: int, reorder: int) -> Tuple[str, str]:
    if stock <= 0 or (reorder and stock <= reorder * 0.3):
        return "Critical", "danger"
    return "Low", "warning"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
class NavButton(QPushButton):
    """Sidebar item with a small square indicator."""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet(
            f"QPushButton {{ background: transparent; border: none; border-radius: 8px; text-align: left;"
            f" padding: 0 0 0 40px; color: {T.MUTED}; font-size: 14px; font-weight: 500; }}"
            f"QPushButton:hover {{ color: {T.TEXT}; background: {T.SURFACE_2}; }}"
            f"QPushButton:checked {{ color: {T.TEXT}; background: {T.SURFACE_3}; }}")

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(14, (self.height() - 14) / 2, 14, 14)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(T.ACCENT))
        else:
            p.setPen(QPen(QColor(T.FAINT), 1.4))
            p.setBrush(Qt.NoBrush)
            r.adjust(0.7, 0.7, -0.7, -0.7)
        p.drawRoundedRect(r, 4, 4)


class OpenCounterButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(52)
        self.setToolTip("Switch to the billing counter")
        self.setStyleSheet(f"QPushButton {{ background: {T.SURFACE_2}; border: 1px solid {T.BORDER}; border-radius: 10px; }}"
                           f"QPushButton:hover {{ border-color: {T.BORDER_2}; background: {T.SURFACE_3}; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 6, 16, 6)
        col = QVBoxLayout()
        col.setSpacing(0)
        a = make_label("Open counter", size=13, weight=600)
        b = make_label("Switch to billing", role="faint", size=12)
        arrow = make_label("→", role="muted", size=15, weight=500)
        for w in (a, b, arrow):
            w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        col.addWidget(a)
        col.addWidget(b)
        lay.addLayout(col, 1)
        lay.addWidget(arrow)


# ---------------------------------------------------------------------------
# Overview page
# ---------------------------------------------------------------------------
class OverviewPage(QWidget):
    def __init__(self, admin: Employee, on_navigate: Callable[[str], None], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.admin = admin
        self.on_navigate = on_navigate
        self.billing_service = BillingService()
        self.analytics_service = AnalyticsService()
        self._bills_cache: List = []
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(32, 30, 32, 28)
        lay.setSpacing(16)

        # Header
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(6)
        self.greeting = make_label("", size=24, weight=600)
        f = self.greeting.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.6)
        self.greeting.setFont(f)
        self.subtitle = make_label("", role="muted", size=14)
        titles.addWidget(self.greeting)
        titles.addWidget(self.subtitle)
        head.addLayout(titles, 1)
        self.range_combo = QComboBox()
        self.range_combo.addItems(RANGES)
        self.range_combo.setFixedSize(180, 36)
        self.range_combo.currentTextChanged.connect(lambda _t: self.refresh())
        head.addWidget(self.range_combo, 0, Qt.AlignTop)
        head.addSpacing(8)
        self.export_btn = make_button("Export", variant="light")
        self.export_btn.setFixedSize(88, 36)
        self.export_btn.setToolTip("Export the bills in this range to CSV")
        self.export_btn.clicked.connect(self.export_csv)
        head.addWidget(self.export_btn, 0, Qt.AlignTop)
        lay.addLayout(head)
        lay.addSpacing(10)

        # KPI cards
        kpis = QHBoxLayout()
        kpis.setSpacing(16)
        self.kpi_revenue = StatCard("Revenue")
        self.kpi_bills = StatCard("Bills")
        self.kpi_avg = StatCard("Avg. bill")
        self.kpi_low = StatCard("Low stock", tone="warning")
        for c in (self.kpi_revenue, self.kpi_bills, self.kpi_avg, self.kpi_low):
            kpis.addWidget(c, 1)
        self.kpi_low.setCursor(Qt.PointingHandCursor)
        self.kpi_low.mousePressEvent = lambda _e: self.on_navigate("inventory")
        lay.addLayout(kpis)

        # Chart + top sellers
        mid = QHBoxLayout()
        mid.setSpacing(16)
        chart_card = Card(padding=(22, 20, 22, 16), spacing=2)
        chart_card.setMinimumHeight(360)
        self.chart_title = make_label("Sales today", size=15, weight=600)
        self.chart_sub = make_label("Hourly revenue", role="faint", size=12)
        chart_card.body.addWidget(self.chart_title)
        chart_card.body.addWidget(self.chart_sub)
        self.chart = AreaChart()
        chart_card.body.addWidget(self.chart, 1)
        mid.addWidget(chart_card, 64)

        top_card = Card(padding=(22, 20, 22, 20), spacing=0)
        th = QHBoxLayout()
        th.addWidget(make_label("Top sellers", size=15, weight=600))
        th.addStretch(1)
        view_all = make_button("View all", variant="link")
        view_all.clicked.connect(lambda: self.on_navigate("analytics"))
        th.addWidget(view_all)
        top_card.body.addLayout(th)
        top_card.body.addSpacing(18)
        self.top_list = QVBoxLayout()
        self.top_list.setSpacing(22)
        top_card.body.addLayout(self.top_list)
        top_card.body.addStretch(1)
        mid.addWidget(top_card, 36)
        lay.addLayout(mid)

        # Needs restocking
        low_card = Card(padding=(22, 18, 22, 12), spacing=0)
        lh = QHBoxLayout()
        lh.addWidget(make_label("Needs restocking", size=15, weight=600))
        lh.addStretch(1)
        inv_btn = make_button("Open inventory", size="sm")
        inv_btn.setFixedHeight(30)
        inv_btn.clicked.connect(lambda: self.on_navigate("inventory"))
        lh.addWidget(inv_btn)
        low_card.body.addLayout(lh)
        low_card.body.addSpacing(14)
        self.low_grid = QGridLayout()
        self.low_grid.setHorizontalSpacing(16)
        self.low_grid.setVerticalSpacing(0)
        low_card.body.addLayout(self.low_grid)
        lay.addWidget(low_card)
        lay.addStretch(1)

    # ------------------------------------------------------------ data
    def refresh(self) -> None:
        now = datetime.now()
        part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        first = (self.admin.first_name or self.admin.get_full_name()).strip()
        self.greeting.setText(f"Good {part}, {first}")
        label = self.range_combo.currentText()
        scope = {"Today": "today", "Yesterday": "yesterday"}.get(label, label.lower())
        self.subtitle.setText(f"{now.strftime('%A, %d %B').replace(' 0', ' ')} · Here's how the store is doing {scope}.")

        start, end = range_bounds(label)
        pstart, pend = previous_bounds(label, start, end)
        bills = self._bills(start, end)
        prev = self._bills(pstart, pend)
        self._bills_cache = bills
        rev = sum(b.total for b in bills)
        prev_rev = sum(b.total for b in prev)
        cnt, prev_cnt = len(bills), len(prev)
        avg = rev / cnt if cnt else 0.0
        prev_avg = prev_rev / prev_cnt if prev_cnt else 0.0
        vs = f"vs last {pstart.strftime('%a')}" if start == end else "vs previous period"

        self.kpi_revenue.set_value(T.money(rev, 0) if rev >= 1000 else T.money(rev))
        self.kpi_revenue.set_delta(*self._pct_delta(rev, prev_rev, vs))
        self.kpi_bills.set_value(str(cnt))
        diff = cnt - prev_cnt
        self.kpi_bills.set_delta(f"{diff:+d} {vs}" if prev_cnt or cnt else "No bills yet",
                                 "success" if diff >= 0 else "danger")
        self.kpi_avg.set_value(T.money(avg))
        self.kpi_avg.set_delta(*self._pct_delta(avg, prev_avg, ""))

        low = pos_low_stock()
        self.kpi_low.set_value(f"{len(low)} item{'s' if len(low) != 1 else ''}")
        self.kpi_low.set_delta("Restock soon" if low else "All stocked", "warning" if low else "success")

        self._fill_chart(bills, start, end)
        self._fill_top(start, end)
        self._fill_low(low)

    def _bills(self, start: date, end: date) -> List:
        try:
            return self.billing_service.search_bills(start_date=start.isoformat(), end_date=end.isoformat())
        except Exception as e:  # noqa: BLE001
            print(f"Overview: bills unavailable: {e}")
            return []

    @staticmethod
    def _pct_delta(cur: float, prev: float, vs: str) -> Tuple[str, str]:
        if prev <= 0:
            return ("New activity" if cur > 0 else "No sales yet"), ("success" if cur > 0 else "neutral")
        pct = (cur - prev) / prev * 100
        return f"{pct:+.1f}% {vs}".strip(), ("success" if pct >= 0 else "danger")

    def _fill_chart(self, bills: List, start: date, end: date) -> None:
        if start == end:
            self.chart_title.setText("Sales today" if start == date.today() else f"Sales on {start.strftime('%d %b')}")
            self.chart_sub.setText("Hourly revenue")
            per_hour: Dict[int, float] = defaultdict(float)
            for b in bills:
                h = local_hour(b.created_at)
                if h is not None:
                    per_hour[h] += b.total
            lo = min([8] + list(per_hour.keys()))
            hi = max([20] + list(per_hour.keys()))
            hours = list(range(lo, hi + 1))
            values = [per_hour.get(h, 0.0) for h in hours]
            labels = [fmt_hour(h) if (h - lo) % 2 == 0 else "" for h in hours]
            tips = [f"{fmt_hour_long(h)}|{T.money(per_hour.get(h, 0.0), 0)}" for h in hours]
            self.chart.set_data(values, labels, tips, empty_text="No sales yet today" if start == date.today() else "No sales that day")
        else:
            self.chart_title.setText("Sales")
            self.chart_sub.setText("Daily revenue")
            per_day: Dict[str, float] = defaultdict(float)
            for b in bills:
                per_day[b.date] += b.total
            days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
            values = [per_day.get(d.isoformat(), 0.0) for d in days]
            every = max(1, len(days) // 7)
            labels = [d.strftime("%d %b") if i % every == 0 or i == len(days) - 1 else "" for i, d in enumerate(days)]
            tips = [f"{d.strftime('%a %d %b')}|{T.money(per_day.get(d.isoformat(), 0.0), 0)}" for d in days]
            self.chart.set_data(values, labels, tips, empty_text="No sales in this period")

    def _fill_top(self, start: date, end: date) -> None:
        while self.top_list.count():
            it = self.top_list.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        try:
            top = self.analytics_service.get_best_selling_products(start.isoformat(), end.isoformat(), limit=5)
        except Exception as e:  # noqa: BLE001
            print(f"Overview: top sellers unavailable: {e}")
            top = []
        if not top:
            self.top_list.addWidget(make_label("No sales in this period yet.", role="muted"))
            return
        mx = max(t['quantity_sold'] for t in top) or 1
        for t in top:
            self.top_list.addWidget(BarRow(t['product_name'], f"{t['quantity_sold']} sold", t['quantity_sold'] / mx))

    def _fill_low(self, low: List[Dict]) -> None:
        while self.low_grid.count():
            it = self.low_grid.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        heads = [("Product", Qt.AlignLeft), ("Category", Qt.AlignLeft), ("In stock", Qt.AlignRight),
                 ("Reorder at", Qt.AlignRight), ("Status", Qt.AlignRight)]
        for c, (h, a) in enumerate(heads):
            lbl = overline(h)
            lbl.setAlignment(a | Qt.AlignVCenter)
            lbl.setContentsMargins(0, 0, 0, 10)
            self.low_grid.addWidget(lbl, 0, c)
        self.low_grid.addWidget(Divider(), 1, 0, 1, len(heads))
        if not low:
            empty = make_label("Nothing needs restocking right now.", role="muted")
            empty.setContentsMargins(0, 16, 0, 12)
            self.low_grid.addWidget(empty, 2, 0, 1, len(heads))
        row = 2
        for item in low[:6]:
            status, tone = stock_status(item['stock'], item['reorder'])
            cells = [
                make_label(item['name'], size=14, weight=500),
                make_label(item['category'], role="muted", size=13),
                make_label(str(item['stock']), tone="danger" if tone == "danger" else None, size=14, weight=600,
                           align=Qt.AlignRight | Qt.AlignVCenter),
                make_label(str(item['reorder']), role="muted", size=13, align=Qt.AlignRight | Qt.AlignVCenter),
            ]
            if tone == "danger":
                cells[2].setStyleSheet(f"color: {T.DANGER}; font-size: 14px; font-weight: 600;")
            for c, w in enumerate(cells):
                w.setFixedHeight(46)
                self.low_grid.addWidget(w, row, c)
            badge_box = QWidget()
            bl = QHBoxLayout(badge_box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.addStretch(1)
            bl.addWidget(StatusBadge(status, tone))
            badge_box.setFixedHeight(46)
            self.low_grid.addWidget(badge_box, row, 4)
            self.low_grid.addWidget(Divider(soft=True), row + 1, 0, 1, len(heads))
            row += 2
        self.low_grid.setColumnStretch(0, 5)
        self.low_grid.setColumnStretch(1, 3)
        self.low_grid.setColumnStretch(2, 2)
        self.low_grid.setColumnStretch(3, 2)
        self.low_grid.setColumnStretch(4, 3)

    def export_csv(self) -> None:
        label = self.range_combo.currentText()
        start, end = range_bounds(label)
        default = f"vendorvault-bills-{start.isoformat()}" + ("" if start == end else f"-to-{end.isoformat()}") + ".csv"
        path, _ = QFileDialog.getSaveFileName(self, "Export bills", default, "CSV files (*.csv)")
        if not path:
            return
        bills = self._bills(start, end)
        try:
            with open(path, "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["Bill No", "Date", "Customer", "Phone", "Subtotal", "Discount", "Tax rate", "Tax", "Total"])
                for b in bills:
                    w.writerow([b.bill_no, b.date, b.customer_name, b.customer_no, f"{b.subtotal:.2f}",
                                f"{b.discount:.2f}", b.tax_rate, f"{b.tax_amount:.2f}", f"{b.total:.2f}"])
            QMessageBox.information(self, "Export", f"Exported {len(bills)} bills to\n{path}")
        except OSError as e:
            QMessageBox.critical(self, "Export failed", str(e))


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class AdminDashboard(QMainWindow):
    """Admin dashboard with sidebar navigation."""

    NAV = [
        ("overview", "Overview"),
        ("invoices", "Sales && invoices"),
        ("inventory", "Inventory"),
        ("products", "Products && brands"),
        ("types", "Product types"),
        ("analytics", "Analytics"),
        ("team", "Team"),
    ]

    def __init__(self, admin: Employee):
        super().__init__()
        self.admin = admin
        self.inventory_service = InventoryService()
        self.employee_service = EmployeeService()
        self.billing_service = BillingService()
        self._pages: Dict[str, QWidget] = {}
        self._nav_buttons: Dict[str, NavButton] = {}
        self.current_page = "overview"

        self.setup_ui()
        self.load_statistics()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(60_000)
        self.update_time()

    # ------------------------------------------------------------ UI
    def setup_ui(self) -> None:
        self.setWindowTitle("Admin Dashboard - VendorVault")
        self.setMinimumSize(1200, 720)
        self.showMaximized()

        central = QWidget()
        central.setObjectName("qt_central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self.overview = OverviewPage(self.admin, self.navigate)
        self.stack.addWidget(self.overview)
        self._pages["overview"] = self.overview
        root.addWidget(self.stack, 1)
        self._nav_buttons["overview"].setChecked(True)
        self.statusBar().hide()

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setAttribute(Qt.WA_StyledBackground, True)
        side.setFixedWidth(232)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(12, 22, 12, 16)
        lay.setSpacing(6)
        brand = QHBoxLayout()
        brand.setContentsMargins(10, 0, 0, 0)
        brand.setSpacing(10)
        brand.addWidget(LogoMark(26))
        brand.addWidget(make_label(config.APP_NAME, size=15, weight=600))
        brand.addStretch(1)
        lay.addLayout(brand)
        lay.addSpacing(26)
        store = overline("Store")
        store.setContentsMargins(10, 0, 0, 4)
        lay.addWidget(store)
        for key, text in self.NAV:
            b = NavButton(text)
            b.clicked.connect(lambda _=False, k=key: self.navigate(k))
            self._nav_buttons[key] = b
            lay.addWidget(b)
        lay.addStretch(1)
        counter = OpenCounterButton()
        counter.clicked.connect(self.switch_to_employee_mode)
        self.open_counter_btn = counter
        lay.addWidget(counter)
        lay.addSpacing(14)

        user = QHBoxLayout()
        user.setContentsMargins(8, 0, 0, 0)
        user.setSpacing(10)
        user.addWidget(Avatar(self.admin.get_full_name(), 30))
        col = QVBoxLayout()
        col.setSpacing(0)
        first, last = (self.admin.first_name or "").strip(), (self.admin.last_name or "").strip()
        col.addWidget(make_label(f"{first} {last[:1]}." if first and last else self.admin.get_full_name(), size=13, weight=500))
        col.addWidget(make_label(self.admin.designation or self.admin.role or "Admin", role="faint", size=11))
        user.addLayout(col, 1)
        self.logout_btn = make_button("Log out", variant="ghost", size="sm")
        self.logout_btn.clicked.connect(self.handle_logout)
        user.addWidget(self.logout_btn)
        lay.addLayout(user)
        return side

    # ------------------------------------------------------------ navigation
    def navigate(self, key: str) -> None:
        openers = {
            "overview": self.show_overview,
            "invoices": self.open_invoices,
            "inventory": self.open_inventory,
            "products": self.open_brands,
            "types": self.open_product_types,
            "analytics": self.open_analytics,
            "team": self.open_employees,
        }
        openers.get(key, self.show_overview)()

    def _select_nav(self, key: str) -> None:
        self.current_page = key
        for k, b in self._nav_buttons.items():
            b.setChecked(k == key)

    def show_overview(self) -> None:
        self._select_nav("overview")
        self.stack.setCurrentWidget(self.overview)
        self.load_statistics()

    def _embed(self, key: str, window: QWidget) -> QWidget:
        """Show an existing admin window as a page inside the dashboard."""
        old = self._pages.pop(key, None)
        if old is not None:
            self.stack.removeWidget(old)
            old.deleteLater()
        window.setWindowFlags(Qt.Widget)
        window.installEventFilter(self)
        for sb in window.findChildren(QStatusBar):
            sb.setSizeGripEnabled(False)
        self.stack.addWidget(window)
        self._pages[key] = window
        self.stack.setCurrentWidget(window)
        self._select_nav(key)
        return window

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        # An embedded page asking to close (e.g. its own Close button) returns to Overview.
        if event.type() == QEvent.Close and obj in self._pages.values() and obj is not self.overview:
            event.ignore()
            QTimer.singleShot(0, self.show_overview)
            return True
        return super().eventFilter(obj, event)

    def open_inventory(self) -> None:
        from src.ui.admin.simple_inventory import SimpleInventoryWindow
        self.inv_window = self._embed("inventory", SimpleInventoryWindow(self, embedded=True))

    def open_brands(self) -> None:
        """Products & brands: product catalogue (with the product dialog) and brands."""
        from src.ui.admin.brands import BrandManagementWindow
        from src.ui.admin.inventory import InventoryWindow
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 20, 24, 20)
        tabs = QTabWidget()
        self.brands_window = BrandManagementWindow(self)
        self.products_window = InventoryWindow(self)
        for w in (self.brands_window, self.products_window):
            w.setWindowFlags(Qt.Widget)
        tabs.addTab(self.brands_window, "Brands")
        tabs.addTab(self.products_window, "Products")
        lay.addWidget(tabs)
        self.products_tabs = tabs
        self._embed("products", page)

    def open_product_types(self) -> None:
        from src.ui.admin.product_types import ProductTypeManagementWindow
        self.types_window = self._embed("types", ProductTypeManagementWindow(self))

    def open_employees(self) -> None:
        from src.ui.admin.employees import EmployeeWindow
        self.emp_window = self._embed("team", EmployeeWindow(self))

    def open_invoices(self) -> None:
        from src.ui.admin.invoices import InvoicesWindow
        self.invoices_window = self._embed("invoices", InvoicesWindow(self))

    def open_analytics(self) -> None:
        from src.ui.admin.analytics_dashboard import EnterpriseDashboard
        self.analytics_window = self._embed("analytics", EnterpriseDashboard(self, embedded=True))

    # ------------------------------------------------------------ data
    def update_time(self) -> None:
        # Greeting/date can change while the app stays open.
        if self.current_page == "overview":
            self.overview.refresh()

    def load_statistics(self) -> None:
        try:
            self.overview.refresh()
        except Exception as e:  # noqa: BLE001
            print(f"Overview refresh failed: {e}")

    # ------------------------------------------------------------ session
    def switch_to_employee_mode(self) -> None:
        self.close()
        from src.ui.employee.billing import BillingWindow
        self.billing_window = BillingWindow(self.admin)
        self.billing_window.show()

    def handle_logout(self) -> None:
        self.close()
        from src.ui.login import LoginWindow
        self.login_window = LoginWindow()

        def on_login(employee):
            if employee.is_admin():
                from src.ui.admin.dashboard import AdminDashboard
                self.next_window = AdminDashboard(employee)
            else:
                from src.ui.employee.billing import BillingWindow
                self.next_window = BillingWindow(employee)
            self.next_window.show()

        self.login_window.login_successful.connect(on_login)
        self.login_window.show()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.timer.stop()
        event.accept()
