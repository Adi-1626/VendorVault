"""
Inventory – the POS catalogue (``simple_products``).

This is the only inventory screen: the POS sells from ``simple_products`` and
billing deducts stock from it. Layout: stat tiles on top, the scan/edit form
(natural height) with a "needs restocking" list beneath it on the left, and
the searchable, filterable product table on the right.

The SQL that writes products is unchanged from the previous version.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from src.database.connection import db
from src.ui import theme as T
from src.ui.widgets import Card, StatusBadge, make_button, make_label

DEFAULT_CATEGORIES = ['Namkeen', 'Biscuits', 'Chips', 'Sweets', 'Dry Fruits', 'Beverages', 'Other']
LOW_STOCK_THRESHOLD = 10
ALL_CATEGORIES = "All categories"


def merge_categories(defaults: List[str], existing: List[str]) -> List[str]:
    """Defaults first (in order), then categories already used in the catalogue,
    de-duplicated case-insensitively and sorted."""
    seen = {c.lower() for c in defaults}
    extra = sorted({c.strip() for c in existing if c and c.strip() and c.strip().lower() not in seen},
                   key=str.lower)
    return list(defaults) + extra


def money(v: float) -> str:
    return f"₹{v:,.2f}"


class _Stat(Card):
    def __init__(self, title: str, tone: str = "neutral"):
        super().__init__(inset=True, padding=(16, 12, 16, 12), spacing=2)
        self.setFixedHeight(76)
        self.tone = tone
        self.body.addWidget(make_label(title, role="muted", size=12, weight=500))
        self.value = make_label("—", size=20, weight=600)
        self.body.addWidget(self.value)

    def set_value(self, text: str, alert: bool = False) -> None:
        self.value.setText(text)
        color = {"warning": T.WARNING, "danger": T.DANGER}.get(self.tone, T.TEXT) if alert else T.TEXT
        self.value.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 600;")


class SimpleInventoryWindow(QMainWindow):
    """Barcode-based inventory for the POS catalogue."""

    def __init__(self, parent=None, embedded: bool = False):
        super().__init__(parent)
        self.embedded = embedded  # True when shown inside the admin dashboard
        self.current_product_id: Optional[int] = None
        self._all_rows: List[Dict] = []
        self.setup_ui()
        self.load_products()
        QTimer.singleShot(100, lambda: self.barcode_input.setFocus())

    # ------------------------------------------------------------------ UI
    def setup_ui(self) -> None:
        self.setWindowTitle("Inventory")
        self.setMinimumSize(1100, 700)
        central = QWidget()
        central.setObjectName("qt_central")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 28, 32, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(6)
        titles.addWidget(make_label("Inventory", size=24, weight=600))
        self.subtitle = make_label("", role="muted", size=14)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        close_btn = make_button("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setVisible(not self.embedded)
        header.addWidget(close_btn, 0, Qt.AlignTop)
        layout.addLayout(header)

        # Stat tiles
        stats = QHBoxLayout()
        stats.setSpacing(12)
        self.stat_products = _Stat("Products")
        self.stat_value = _Stat("Stock value (cost)")
        self.stat_low = _Stat(f"Low stock (≤ {LOW_STOCK_THRESHOLD})", "warning")
        self.stat_out = _Stat("Out of stock", "danger")
        for s in (self.stat_products, self.stat_value, self.stat_low, self.stat_out):
            stats.addWidget(s, 1)
        self.stat_low.setCursor(Qt.PointingHandCursor)
        self.stat_low.setToolTip("Show low-stock products")
        self.stat_low.mousePressEvent = lambda _e: self.stock_filter.setCurrentText("Low stock")
        self.stat_out.setCursor(Qt.PointingHandCursor)
        self.stat_out.setToolTip("Show out-of-stock products")
        self.stat_out.mousePressEvent = lambda _e: self.stock_filter.setCurrentText("Out of stock")
        layout.addLayout(stats)

        content = QHBoxLayout()
        content.setSpacing(16)

        # Left column: form (natural height) + restock list
        left = QVBoxLayout()
        left.setSpacing(16)
        form = Card(padding=(22, 20, 22, 20), spacing=12)
        form.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.form_title = make_label("Add or edit a product", size=15, weight=600)
        form.body.addWidget(self.form_title)
        form.body.addWidget(make_label("Scan a barcode (or double-click a product) to load it.", role="faint", size=12))
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan barcode here…")
        self.barcode_input.setProperty("size", "lg")
        self.barcode_input.returnPressed.connect(self.lookup_barcode)
        form.body.addWidget(self.barcode_input)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Haldiram Aloo Bhujia 400g")
        self.mrp_input = QDoubleSpinBox()
        self.cost_input = QDoubleSpinBox()
        for sp in (self.mrp_input, self.cost_input):
            sp.setMaximum(99999)
            sp.setDecimals(2)
            sp.setPrefix("₹ ")
            sp.valueChanged.connect(self._update_margin_hint)
        self.stock_input = QSpinBox()
        self.stock_input.setMaximum(99999)
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.category_input.setInsertPolicy(QComboBox.NoInsert)
        self.category_input.addItems(DEFAULT_CATEGORIES)
        self.category_input.setToolTip("Pick a category or type a new one")

        def cap(text: str) -> QLabel:
            return make_label(text, role="muted", size=12, weight=500)

        grid.addWidget(cap("Product name"), 0, 0, 1, 2)
        grid.addWidget(self.name_input, 1, 0, 1, 2)
        grid.addWidget(cap("MRP"), 2, 0)
        grid.addWidget(cap("Cost price"), 2, 1)
        grid.addWidget(self.mrp_input, 3, 0)
        grid.addWidget(self.cost_input, 3, 1)
        grid.addWidget(cap("Stock"), 4, 0)
        grid.addWidget(cap("Category"), 4, 1)
        grid.addWidget(self.stock_input, 5, 0)
        grid.addWidget(self.category_input, 5, 1)
        for r in (2, 4):
            grid.setRowMinimumHeight(r, 22)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        form.body.addLayout(grid)

        self.margin_hint = make_label("", role="faint", size=12)
        form.body.addWidget(self.margin_hint)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)
        quick_row.addWidget(make_label("Quick stock", role="muted", size=12, weight=500))
        quick_row.addStretch(1)
        for qty in [1, 5, 10, 50]:
            btn = make_button(f"+{qty}", size="sm")
            btn.clicked.connect(lambda _, q=qty: self.quick_add_stock(q))
            quick_row.addWidget(btn)
        form.body.addLayout(quick_row)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {T.SUCCESS}; font-size: 13px; font-weight: 500;")
        self.status_label.setWordWrap(True)
        form.body.addWidget(self.status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        save_btn = make_button("Save product", variant="primary")
        save_btn.clicked.connect(self.save_product)
        new_btn = make_button("New")
        new_btn.clicked.connect(self.clear_form)
        self.del_btn = make_button("Delete", variant="danger")
        self.del_btn.clicked.connect(self.delete_product)
        self.del_btn.setEnabled(False)
        btn_row.addWidget(save_btn, 2)
        btn_row.addWidget(new_btn, 1)
        btn_row.addWidget(self.del_btn, 1)
        form.body.addLayout(btn_row)
        left.addWidget(form)

        restock = Card(padding=(22, 18, 22, 14), spacing=0)
        rh = QHBoxLayout()
        rh.addWidget(make_label("Needs restocking", size=15, weight=600))
        rh.addStretch(1)
        self.restock_count = StatusBadge("0", "warning")
        rh.addWidget(self.restock_count)
        restock.body.addLayout(rh)
        restock.body.addSpacing(10)
        self.restock_list = QVBoxLayout()
        self.restock_list.setSpacing(0)
        restock.body.addLayout(self.restock_list)
        restock.body.addStretch(1)
        left.addWidget(restock, 1)

        left_box = QWidget()
        left_box.setLayout(left)
        left_box.setFixedWidth(384)
        left.setContentsMargins(0, 0, 0, 0)
        content.addWidget(left_box)

        # Right: product table
        list_card = Card(padding=(20, 18, 20, 18), spacing=12)
        lh = QHBoxLayout()
        lh.setSpacing(8)
        self.list_title = make_label("All products", size=15, weight=600)
        lh.addWidget(self.list_title)
        lh.addStretch(1)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name or barcode…")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.search_products)
        lh.addWidget(self.search_input)
        self.category_filter = QComboBox()
        self.category_filter.setFixedWidth(170)
        self.category_filter.currentTextChanged.connect(lambda _t: self._apply_filters())
        lh.addWidget(self.category_filter)
        self.stock_filter = QComboBox()
        self.stock_filter.addItems(["All stock", "Low stock", "Out of stock"])
        self.stock_filter.setFixedWidth(130)
        self.stock_filter.currentTextChanged.connect(lambda _t: self._apply_filters())
        lh.addWidget(self.stock_filter)
        list_card.body.addLayout(lh)

        self.product_table = QTableWidget()
        self.product_table.setProperty("flat", True)
        cols = ['Barcode', 'Name', 'Category', 'MRP', 'Cost', 'Margin', 'Stock']
        self.product_table.setColumnCount(len(cols))
        for c, name in enumerate(cols):
            hi = QTableWidgetItem(name.upper())
            hi.setTextAlignment((Qt.AlignRight if c >= 3 else Qt.AlignLeft) | Qt.AlignVCenter)
            self.product_table.setHorizontalHeaderItem(c, hi)
        hh = self.product_table.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for c, w in ((0, 136), (2, 104), (3, 80), (4, 80), (5, 68), (6, 62)):
            self.product_table.setColumnWidth(c, w)
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.setSelectionMode(QTableWidget.SingleSelection)
        self.product_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.product_table.verticalHeader().setVisible(False)
        self.product_table.verticalHeader().setDefaultSectionSize(40)
        self.product_table.setShowGrid(False)
        self.product_table.doubleClicked.connect(self.load_selected)
        list_card.body.addWidget(self.product_table, 1)
        content.addWidget(list_card, 1)
        layout.addLayout(content, 1)

        self._set_status("", T.SUCCESS)
        self.margin_hint.hide()
        self.statusBar().showMessage("Scan barcode to add/edit products")
        self.statusBar().hide()

    # ------------------------------------------------------------ helpers
    def _categories_in_use(self) -> List[str]:
        rows = db.execute_query("SELECT DISTINCT category FROM simple_products WHERE category IS NOT NULL")
        return [r['category'] for r in rows]

    def refresh_categories(self) -> None:
        """Category choices = defaults + DISTINCT categories already in the catalogue."""
        cats = merge_categories(DEFAULT_CATEGORIES, self._categories_in_use())
        current = self.category_input.currentText()
        self.category_input.blockSignals(True)
        self.category_input.clear()
        self.category_input.addItems(cats)
        self.category_input.setCurrentText(current or cats[0])
        self.category_input.blockSignals(False)
        used = sorted({(c or '').strip() for c in self._categories_in_use() if (c or '').strip()}, key=str.lower)
        sel = self.category_filter.currentText() or ALL_CATEGORIES
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItems([ALL_CATEGORIES] + used)
        self.category_filter.setCurrentText(sel if sel in used else ALL_CATEGORIES)
        self.category_filter.blockSignals(False)

    def _update_margin_hint(self) -> None:
        mrp, cost = self.mrp_input.value(), self.cost_input.value()
        if mrp <= 0 or cost <= 0:
            self.margin_hint.setText("Add a cost price to see the margin (used by Analytics)." if mrp > 0 else "")
            self.margin_hint.setStyleSheet(f"color: {T.FAINT}; font-size: 12px;")
            self.margin_hint.setVisible(mrp > 0)
            return
        m = (mrp - cost) / mrp * 100
        color = T.DANGER if m < 0 else T.MUTED
        txt = f"Margin {m:.1f}% · {money(mrp - cost)} per unit"
        if m < 0:
            txt += " — selling below cost"
        self.margin_hint.setText(txt)
        self.margin_hint.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.margin_hint.setVisible(True)

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 500;")
        self.status_label.setVisible(bool(text))

    # ---------------------------------------------------------------- actions
    def lookup_barcode(self):
        """Look up barcode."""
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return
        query = "SELECT * FROM simple_products WHERE barcode = ?"
        results = db.execute_query(query, (barcode,))
        if results:
            p = results[0]
            self.current_product_id = p['id']
            self.name_input.setText(p['name'])
            self.mrp_input.setValue(p['mrp'] or 0)
            self.cost_input.setValue(p['cost_price'] or 0)
            self.stock_input.setValue(p['stock'] or 0)
            cat = p.get('category', '') or ''
            idx = self.category_input.findText(cat)
            if idx >= 0:
                self.category_input.setCurrentIndex(idx)
            else:
                self.category_input.setCurrentText(cat)
            self.form_title.setText("Edit product")
            self._set_status(f"✓ Found: {p['name']}", T.SUCCESS)
            self.name_input.setFocus()
        else:
            self.current_product_id = None
            self.name_input.clear()
            self.mrp_input.setValue(0)
            self.cost_input.setValue(0)
            self.stock_input.setValue(0)
            self.category_input.setCurrentIndex(0)
            self.form_title.setText("New product")
            self._set_status(f"New barcode: {barcode}", T.ACCENT)
            self.name_input.setFocus()
        self.del_btn.setEnabled(self.current_product_id is not None)

    def save_product(self):
        """Save product."""
        barcode = self.barcode_input.text().strip()
        name = self.name_input.text().strip()
        if not barcode:
            QMessageBox.warning(self, "Required", "Scan barcode first")
            return
        if not name:
            QMessageBox.warning(self, "Required", "Enter product name")
            return
        mrp = self.mrp_input.value()
        cost = self.cost_input.value()
        stock = self.stock_input.value()
        category = self.category_input.currentText()
        try:
            if self.current_product_id:
                query = """
                    UPDATE simple_products 
                    SET name = ?, mrp = ?, cost_price = ?, stock = ?, category = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                """
                db.execute_update(query, (name, mrp, cost, stock, category, self.current_product_id))
                msg = f"✓ Updated: {name}"
            else:
                query = """
                    INSERT INTO simple_products (barcode, name, mrp, cost_price, stock, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                db.execute_insert(query, (barcode, name, mrp, cost, stock, category))
                msg = f"✓ Added: {name}"
            self.load_products()
            self.clear_form()
            self._set_status(msg, T.SUCCESS)
            self.statusBar().showMessage(msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Save failed: {e}")

    def delete_product(self):
        """Delete product."""
        if not self.current_product_id:
            return
        name = self.name_input.text()
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.Yes:
            query = "DELETE FROM simple_products WHERE id = ?"
            db.execute_update(query, (self.current_product_id,))
            self.load_products()
            self.clear_form()
            self._set_status(f"Deleted: {name}", T.MUTED)
            self.statusBar().showMessage(f"Deleted: {name}")

    def quick_add_stock(self, qty):
        """Quick add stock."""
        self.stock_input.setValue(self.stock_input.value() + qty)

    def clear_form(self):
        """Clear form."""
        self.current_product_id = None
        self.barcode_input.clear()
        self.name_input.clear()
        self.mrp_input.setValue(0)
        self.cost_input.setValue(0)
        self.stock_input.setValue(0)
        self.category_input.setCurrentIndex(0)
        self.form_title.setText("Add or edit a product")
        self._set_status("", T.SUCCESS)
        self.del_btn.setEnabled(False)
        self.barcode_input.setFocus()

    # ------------------------------------------------------------------- data
    def load_products(self, search_text=None):
        """Load products (all rows are cached; search and filters apply locally)."""
        query = "SELECT * FROM simple_products ORDER BY name"
        self._all_rows = db.execute_query(query)
        self.refresh_categories()
        self._update_stats()
        self._fill_restock()
        if search_text is not None:
            self.search_input.blockSignals(True)
            self.search_input.setText(search_text)
            self.search_input.blockSignals(False)
        self._apply_filters()
        self.statusBar().showMessage(f"Loaded {len(self._all_rows)} products")

    def _update_stats(self) -> None:
        rows = [r for r in self._all_rows if r.get('is_active', 1)]
        value = sum(max(0, r['stock'] or 0) * (r['cost_price'] or 0) for r in rows)
        low = [r for r in rows if 0 < (r['stock'] or 0) <= LOW_STOCK_THRESHOLD]
        out = [r for r in rows if (r['stock'] or 0) <= 0]
        missing = sum(1 for r in rows if not (r['cost_price'] or 0))
        self.stat_products.set_value(f"{len(rows)}")
        self.stat_value.set_value(f"₹{value:,.0f}")
        self.stat_low.set_value(str(len(low)), alert=bool(low))
        self.stat_out.set_value(str(len(out)), alert=bool(out))
        sub = f"{len(rows)} products in the POS catalogue"
        if missing:
            sub += f" · {missing} without a cost price"
        self.subtitle.setText(sub)

    def _fill_restock(self) -> None:
        while self.restock_list.count():
            it = self.restock_list.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        items = sorted((r for r in self._all_rows if r.get('is_active', 1) and (r['stock'] or 0) <= LOW_STOCK_THRESHOLD),
                       key=lambda r: (r['stock'] or 0, r['name']))
        self.restock_count.setText(str(len(items)))
        self.restock_count.setVisible(bool(items))
        if not items:
            self.restock_list.addWidget(make_label("All products are above the reorder level.", role="muted", size=13))
            return
        for r in items[:6]:
            row = QPushButton()
            row.setCursor(Qt.PointingHandCursor)
            row.setFixedHeight(40)
            row.setToolTip("Load into the form")
            row.setStyleSheet(f"QPushButton {{ background: transparent; border: none; border-radius: 8px; padding: 0; }}"
                              f"QPushButton:hover {{ background: {T.SURFACE_2}; }}")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 0, 8, 0)
            name = make_label(r['name'], size=13, weight=500)
            name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            stock = int(r['stock'] or 0)
            badge = StatusBadge("Out" if stock <= 0 else f"{stock} left", "danger" if stock <= 0 else "warning")
            for w in (name, badge):
                w.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            rl.addWidget(name, 1)
            rl.addWidget(badge)
            row.clicked.connect(lambda _=False, bc=r['barcode']: self._load_barcode(bc))
            self.restock_list.addWidget(row)
        if len(items) > 6:
            more = make_button(f"Show all {len(items)}", variant="link")
            more.clicked.connect(lambda: self.stock_filter.setCurrentText("Low stock"))
            self.restock_list.addSpacing(6)
            self.restock_list.addWidget(more, 0, Qt.AlignLeft)

    def _apply_filters(self) -> None:
        text = (self.search_input.text() or "").strip().lower()
        cat = self.category_filter.currentText()
        stock_mode = self.stock_filter.currentText()
        rows = []
        for p in self._all_rows:
            if text and text not in (p['name'] or '').lower() and text not in (p['barcode'] or '').lower():
                continue
            if cat and cat != ALL_CATEGORIES and (p.get('category') or '').strip() != cat:
                continue
            s = p['stock'] or 0
            if stock_mode == "Low stock" and not s <= LOW_STOCK_THRESHOLD:
                continue
            if stock_mode == "Out of stock" and s > 0:
                continue
            rows.append(p)
        self._fill_table(rows)

    def _fill_table(self, results: List[Dict]) -> None:
        self.product_table.setRowCount(len(results))
        right = Qt.AlignRight | Qt.AlignVCenter
        for i, p in enumerate(results):
            mrp, cost, stock = p['mrp'] or 0, p['cost_price'] or 0, p['stock'] or 0
            cells = [
                QTableWidgetItem(p['barcode']),
                QTableWidgetItem(p['name']),
                QTableWidgetItem(p.get('category') or '—'),
                QTableWidgetItem(f"₹{mrp:.2f}"),
                QTableWidgetItem(f"₹{cost:.2f}" if cost else "—"),
                QTableWidgetItem(f"{(mrp - cost) / mrp * 100:.0f}%" if cost and mrp else "—"),
                QTableWidgetItem(str(stock)),
            ]
            cells[0].setForeground(QColor(T.FAINT))
            cells[2].setForeground(QColor(T.MUTED))
            for c in (3, 4, 5, 6):
                cells[c].setTextAlignment(right)
            if not cost:
                cells[4].setForeground(QColor(T.FAINT))
                cells[5].setForeground(QColor(T.FAINT))
            elif cost > mrp:
                cells[5].setForeground(QColor(T.DANGER))
            if stock <= 0:
                cells[6].setForeground(QColor(T.DANGER))
            elif stock <= LOW_STOCK_THRESHOLD:
                cells[6].setForeground(QColor(T.WARNING))
            for c, it in enumerate(cells):
                self.product_table.setItem(i, c, it)
            self.product_table.item(i, 0).setData(Qt.UserRole, p['id'])
        total = len(self._all_rows)
        self.list_title.setText("All products" if len(results) == total else f"{len(results)} of {total} products")

    def search_products(self, text):
        """Search products."""
        self._apply_filters()

    def _load_barcode(self, barcode: str) -> None:
        self.barcode_input.setText(barcode)
        self.lookup_barcode()

    def load_selected(self):
        """Load selected."""
        row = self.product_table.currentRow()
        if row < 0:
            return
        self._load_barcode(self.product_table.item(row, 0).text())
