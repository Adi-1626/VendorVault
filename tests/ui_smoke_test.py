"""
Headless smoke test for the VendorVault UI redesign.

Runs against a COPY of data/store.db (never the real one), instantiates every
window/dialog, drives the POS flows and saves screenshots.

Usage (from the repo root):
  QT_QPA_PLATFORM=offscreen python tests/ui_smoke_test.py
Screenshots go to $VV_SCREENSHOT_DIR (default: _dev/screenshots, git-ignored).
"""
import hashlib
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

REPO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("VV_SCREENSHOT_DIR", REPO / "_dev" / "screenshots"))
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

real_db = REPO / "data" / "store.db"
real_md5 = hashlib.md5(real_db.read_bytes()).hexdigest()
tmpdir = Path(tempfile.mkdtemp(prefix="vvtest_"))
test_db = tmpdir / "store.db"
shutil.copy(real_db, test_db)

import config  # noqa: E402
config.DATABASE_PATH = test_db
config.GENERATED_BILLS_DIR = tmpdir / "bills"
config.GENERATED_BILLS_DIR.mkdir()

from PySide6.QtCore import Qt, QTimer, QEvent  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog, QLabel  # noqa: E402

app = QApplication(sys.argv)
from src.ui.theme import apply_theme  # noqa: E402
apply_theme(app)

from src.database.connection import db  # noqa: E402
assert db.db_path == str(test_db), db.db_path
from src.database.migrations import run_migrations  # noqa: E402
run_migrations()

# Auto-answer modal boxes
answers = {"question": QMessageBox.Yes}
log_boxes = []
QMessageBox.question = staticmethod(lambda *a, **k: (log_boxes.append(("question", a[2] if len(a) > 2 else "")), answers["question"])[1])
QMessageBox.warning = staticmethod(lambda *a, **k: log_boxes.append(("warning", a[2] if len(a) > 2 else "")) or QMessageBox.Ok)
QMessageBox.information = staticmethod(lambda *a, **k: log_boxes.append(("information", a[2] if len(a) > 2 else "")) or QMessageBox.Ok)
QMessageBox.critical = staticmethod(lambda *a, **k: log_boxes.append(("critical", a[2] if len(a) > 2 else "")) or QMessageBox.Ok)
QDialog.exec = lambda self: (self.show(), 0)[1]

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def step(name, fn):
    try:
        fn()
        check(name, True)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        check(name, False, repr(e))


def activate(w):
    w.raise_()
    w.activateWindow()
    QTest.qWaitForWindowActive(w, 1000)
    app.processEvents()


def press(w, key, mod=Qt.NoModifier, target=None):
    activate(w)
    QTest.keyClick(target or w.focusWidget() or w, key, mod)
    settle()


def settle(ms=50):
    for _ in range(3):
        app.processEvents()
        QTest.qWait(ms)


def shot(widget, name, w=1440, h=900):
    widget.showNormal()
    widget.resize(w, h)
    widget.activateWindow()
    settle(120)
    path = OUT / f"{name}.png"
    widget.grab().save(str(path))
    print("saved", path)
    return path


from src.logic.employee_mgmt import EmployeeService  # noqa: E402
emps = EmployeeService().get_all_employees()
admin = next(e for e in emps if e.is_admin())
cashier = next(e for e in emps if not e.is_admin())
check("employees loaded", admin and cashier, f"{admin.emp_id}, {cashier.emp_id}")

# ---------------------------------------------------------------- login
from src.ui.login import LoginWindow  # noqa: E402
login = LoginWindow()
shot(login, "login")
got = []
login.login_successful.connect(lambda e: got.append(e))
login.employee_radio.setChecked(True)
login.emp_id_input.setText("EMP001")
login.password_input.setText("emp123")
login.handle_login()
check("login EMP001 emits employee", got and got[0].emp_id == "EMP001")
login2 = LoginWindow()
login2.admin_radio.setChecked(True)
login2.login_successful.connect(lambda e: got.append(e))
login2.emp_id_input.setText("ADM001")
login2.password_input.setText("admin123")
login2.handle_login()
check("login ADM001 as admin", len(got) == 2 and got[1].is_admin())
login3 = LoginWindow()
login3.emp_id_input.setText("EMP001")
login3.password_input.setText("wrong")
n = len(log_boxes)
login3.handle_login()
check("bad password shows error", len(log_boxes) > n and log_boxes[-1][0] == "critical")

# ---------------------------------------------------------------- billing
from src.ui.employee.billing import BillingWindow, cash_suggestions  # noqa: E402
from src.logic.smart_search import SmartSearch  # noqa: E402

check("cash chips 758.74", cash_suggestions(758.74) == [760, 800, 1000, 2000], str(cash_suggestions(758.74)))
check("cash chips 99.12", cash_suggestions(99.12) == [100, 200, 500, 2000], str(cash_suggestions(99.12)))

pos = BillingWindow(cashier)
pos.showNormal()
pos.resize(1440, 900)
pos.activateWindow()
QTest.qWaitForWindowActive(pos, 1000)
settle(150)
products = SmartSearch().get_all_products()
by_name = {p['product_name']: p for p in products}
check("quick add populated", len(pos._quick_products) > 0, f"{len(pos._quick_products)} tiles: {pos.quick_caption.text()}")
check("invoice preview", pos.invoice_label.text().startswith("INV-"), pos.invoice_label.text())

# scan a barcode (typed like a keyboard-wedge scanner)
bc = products[0]['barcode']
pos.search_input.setFocus()
pos.search_input.setText(bc)
settle()
check("barcode scan adds line", len(pos.cart_items) == 1 and pos.cart_items[0].product_name == products[0]['product_name'])
pos.search_input.setText(bc)
settle()
check("second scan merges qty", len(pos.cart_items) == 1 and pos.cart_items[0].quantity == 2)

# search + Enter
pos.search_input.setText("Parle")
settle()
check("search shows results", pos.search_results.isVisible() and pos.search_results.count() >= 1)
pos.on_search_enter()
check("enter adds search result", any("Parle" in i.product_name for i in pos.cart_items))

# quick add via number key (focus off search)
pos.cart_table.setFocus()
settle()
before = sum(i.quantity for i in pos.cart_items)
press(pos, Qt.Key_3, target=pos.cart_table)
check("number key quick-adds", sum(i.quantity for i in pos.cart_items) == before + 1)
pos.quick_add(1)
pos.quick_add(1)

# qty stepper
row = 0
q0 = pos.cart_items[0].quantity
st = pos._stepper(row)
st.plus.click()
settle()
check("stepper + increments", pos.cart_items[0].quantity == q0 + 1, str(pos.cart_items[0].quantity))
st = pos._stepper(row)
st.minus.click()
check("stepper - decrements", pos.cart_items[0].quantity == q0)

# stock limit
low = min(products, key=lambda p: p['stock'])
n_before = len(pos.cart_items)
pos.add_product(dict(low, stock=1), 5)
check("stock limit blocks over-add", len(pos.cart_items) == n_before and pos.notice.isVisible())

# undo
pos.add_product(by_name.get("Britannia Good Day 250g", products[1]), 4)
q_before = sum(i.quantity for i in pos.cart_items)
pos.search_input.setFocus()
press(pos, Qt.Key_Z, Qt.ControlModifier, target=pos.search_input)
check("Ctrl+Z undoes last add", sum(i.quantity for i in pos.cart_items) == q_before - 4)
pos.add_product(by_name.get("Britannia Good Day 250g", products[1]), 4)

# discount / tax / totals
pos.discount_input.setValue(0)
sub = sum(i.get_total() for i in pos.cart_items)
expected = sub * 1.18
check("total = subtotal + 18% GST", abs(pos.get_total() - expected) < 0.01, f"{pos.get_total():.2f} vs {expected:.2f}")
check("charge button shows total", pos.print_btn.text().endswith(f"{expected:,.2f}"), pos.print_btn.text())

# cash chips & change
pos.payment_mode.setCurrentText("Cash")
chips = cash_suggestions(pos.get_total())
pos._apply_cash_chip(chips[1])
settle()
check("change due computed", pos.change_caption.text() == "Change due" and pos.change_label.text() == f"₹{chips[1] - pos.get_total():,.2f}",
      pos.change_label.text())

# customer popover
press(pos, Qt.Key_F4)
check("F4 opens customer popover", pos.customer_popover.isVisible())
pos.customer_name.setText("Rahul Kulkarni")
pos.customer_phone.setText("9876500000")
shot_cust = shot(pos, "pos_customer_popover")
pos.close_customer_popover()
check("customer button shows name", "Rahul" in pos.customer_btn.text())
pos.customer_name.clear(); pos.customer_phone.clear()

# select a row so the remove button shows, then screenshot
pos.cart_table.selectRow(len(pos.cart_items) - 1)
pos.add_product(by_name.get("Britannia Good Day 250g", products[1]), 0) if False else None
pos.notice.show_message(f"Added 4 × {pos.cart_items[-1].product_name}", action="Undo  Ctrl+Z", timeout_ms=0)
pos.search_input.clearFocus()
pos.cash_input.setFocus()
shot(pos, "pos_with_items")

# search dropdown screenshot
pos.search_input.setFocus()
pos.search_input.setText("ha")
settle()
shot(pos, "pos_search")
pos.clear_selection()

# hold / recall
items_before = [(i.product_name, i.quantity) for i in pos.cart_items]
pos.save_pending()
settle()
check("hold clears cart", len(pos.cart_items) == 0)
check("pending pill shows 1", pos.pending_btn._text == "1 on hold", pos.pending_btn._text)
shot(pos, "pos_empty")
pos.show_pending_bills()
dlg = pos._pending_dialog
settle()
dlg.grab().save(str(OUT / "pending_dialog.png"))
pending = pos.pending_bills_mgr.get_pending_bills(1)
pos._recall_pending(pending[0], dlg)
check("recall restores cart", [(i.product_name, i.quantity) for i in pos.cart_items] == items_before)
check("pending pill back to 0", pos.pending_btn._text == "0 on hold")

# discount
pos.discount_input.setValue(10)
sub = sum(i.get_total() for i in pos.cart_items)
check("discount applied", abs(pos.get_total() - (sub - 10) * 1.18) < 0.01)

# insufficient cash blocks
pos.cash_input.setText("1")
n_bills = len(db.execute_query("SELECT bill_no FROM bill"))
pos.finalize_bill(print_pdf=False)
check("insufficient cash blocks save", len(db.execute_query("SELECT bill_no FROM bill")) == n_bills and log_boxes[-1][1].startswith("Cash Received"))

# save only (F9)
stock_before = {p['product_name']: p['stock'] for p in SmartSearch().get_all_products()}
pos.cash_input.setText(str(int(pos.get_total()) + 100))
cart_snapshot = [(i.product_name, i.quantity) for i in pos.cart_items]
total_expected = round(pos.get_total(), 2)
press(pos, Qt.Key_F9)
rows = db.execute_query("SELECT * FROM bill ORDER BY rowid DESC LIMIT 1")
check("F9 saves bill", len(db.execute_query("SELECT bill_no FROM bill")) == n_bills + 1)
check("saved total matches", abs(rows[0]['total'] - total_expected) < 0.01, f"{rows[0]['total']} vs {total_expected}")
check("saved discount", abs(rows[0]['discount'] - 10) < 0.001)
stock_after = {p['product_name']: p['stock'] for p in SmartSearch().get_all_products()}
check("stock decremented", all(stock_after[n] == stock_before[n] - q for n, q in cart_snapshot if n in stock_before),
      str([(n, stock_before.get(n), stock_after.get(n), q) for n, q in cart_snapshot]))
check("cart reset after save", len(pos.cart_items) == 0 and pos.discount_input.value() == 0 and pos.cash_input.text() == "")
check("invoice preview advanced", pos.invoice_label.text().endswith(f"{int(rows[0]['bill_no'][-4:]) + 1:04d}"), pos.invoice_label.text())

# print bill (F12) with UPI → PDF generated; patch opener
import src.ui.employee.billing as billing_mod  # noqa: E402
opened = []
billing_mod.open_file = lambda p: opened.append(p)
pos.quick_add(0)
pos.payment_mode.setCurrentText("UPI")
check("UPI hides cash fields", not pos.cash_container.isVisibleTo(pos))
press(pos, Qt.Key_F12)
check("F12 charges + generates PDF", opened and Path(opened[0]).exists(), str(opened))
pos.payment_mode.setCurrentText("Cash")

# legacy keys F5/F7/F10/F2/Esc
pos.quick_add(0)
pos.search_input.setFocus()
press(pos, Qt.Key_F2)
check("F2 focuses qty", app.focusWidget() is pos._stepper(pos._selected_row).edit)
press(pos, Qt.Key_F1)
check("F1 focuses search", app.focusWidget() is pos.search_input)
pos.search_input.setText("xyz")
press(pos, Qt.Key_Escape, target=pos.search_input)
check("Esc clears search text first", pos.search_input.text() == "" and len(pos.cart_items) == 1)
press(pos, Qt.Key_Escape, target=pos.search_input)
check("Esc again clears sale (confirm)", len(pos.cart_items) == 0)
pos.quick_add(0)
press(pos, Qt.Key_F8)
check("F8 holds", len(pos.cart_items) == 0 and pos.pending_btn._text == "1 on hold")
press(pos, Qt.Key_F10)
check("F10 opens held bills", pos._pending_dialog.isVisible())
pos._recall_pending(pos.pending_bills_mgr.get_pending_bills(1)[0], pos._pending_dialog)
pos.cart_table.setFocus()
press(pos, Qt.Key_Delete, target=pos.cart_table)
check("Del removes selected line", len(pos.cart_items) == 0)
check("user menu has logout", any(a.text() == "Log out" for a in pos.user_menu.actions()))

admin_pos = BillingWindow(admin)
check("admin POS menu has switch", any("admin" in a.text().lower() for a in admin_pos.user_menu.actions()))
admin_pos.close()

# ---------------------------------------------------------------- admin
from src.ui.admin.dashboard import AdminDashboard  # noqa: E402
dash = AdminDashboard(admin)
dash.showNormal()
dash.resize(1440, 900)
settle(200)
check("overview KPIs", dash.overview.kpi_bills.value.text().isdigit(), dash.overview.kpi_bills.value.text())
shot(dash, "admin_overview")
for key in ["invoices", "inventory", "analytics", "team"]:
    def go(k=key):
        dash.navigate(k)
        settle(200)
        assert dash.stack.currentWidget() is dash._pages[k]
        if k == "analytics":
            assert dash._pages[k].wait_until_loaded()
            settle(200)
        shot(dash, f"admin_{k}")
    step(f"admin page {key}", go)
# embedded close button returns to overview
dash.navigate("inventory")
settle()
dash._pages["inventory"].close()
settle()
check("embedded close returns to overview", dash.current_page == "overview")
check("nav has one inventory, no legacy catalogue pages",
      list(dash._nav_buttons) == ["overview", "invoices", "inventory", "analytics", "team"], str(list(dash._nav_buttons)))
check("overview is a today snapshot (no range picker)", not hasattr(dash.overview, "range_combo"))
dash.overview.analytics_btn.click()
settle()
check("overview 'Open analytics' navigates", dash.current_page == "analytics")
dash.navigate("invoices")
settle()
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(tmpdir / "export.csv"), ""))
dash._pages["invoices"].export_csv()
check("invoices export csv", (tmpdir / "export.csv").exists() and
      len((tmpdir / "export.csv").read_text().splitlines()) == len(db.execute_query("SELECT bill_no FROM bill")) + 1)

# dialogs
def dialogs():
    from src.ui.admin.employees import EmployeeDialog
    from src.ui.admin.invoices import BillViewDialog
    from src.logic.billing import BillingService
    for name, d in [("employee_dialog", EmployeeDialog(dash)),
                    ("bill_view_dialog", BillViewDialog(dash, BillingService().search_bills()[0]))]:
        d.show()
        settle()
        d.grab().save(str(OUT / f"{name}.png"))
        d.close()
step("all admin dialogs instantiate", dialogs)

# ---------------------------------------------------------------- inventory page
def inventory_page():
    dash.navigate("inventory")
    settle()
    inv = dash._pages["inventory"]
    cats = [inv.category_input.itemText(i) for i in range(inv.category_input.count())]
    db_cats = {r["category"] for r in db.execute_query("SELECT DISTINCT category FROM simple_products") if r["category"]}
    assert db_cats <= set(cats), (db_cats, cats)
    assert cats[:3] == ["Namkeen", "Biscuits", "Chips"], cats
    assert len(cats) == len({c.lower() for c in cats}), cats
    n_all = inv.product_table.rowCount()
    inv.stock_filter.setCurrentText("Low stock")
    low = inv.product_table.rowCount()
    inv.stock_filter.setCurrentText("All stock")
    assert low <= n_all and inv.product_table.rowCount() == n_all
    inv.search_input.setText("Parle")
    assert inv.product_table.rowCount() >= 1 and "Parle" in inv.product_table.item(0, 1).text()
    inv.search_input.setText("")
    inv.barcode_input.setText(inv.product_table.item(0, 0).text())
    inv.lookup_barcode()
    assert inv.current_product_id is not None and inv.del_btn.isEnabled()
    inv.clear_form()
step("inventory: categories from DB + filters + lookup", inventory_page)
shot(dash, "admin_inventory")

# switch modes
def switch():
    dash.switch_to_employee_mode()
    settle()
    assert dash.billing_window.isVisible()
    dash.billing_window.switch_to_admin()
    settle()
    assert dash.billing_window.admin_window.isVisible()
    dash.billing_window.admin_window.close()
    dash.billing_window.handle_logout()
    settle()
    assert dash.billing_window.login_window.isVisible()
step("switch admin<->POS and logout", switch)

# ---------------------------------------------------------------- analytics
from datetime import date as _date, timedelta as _td  # noqa: E402
from src.logic import analytics_engine as AE  # noqa: E402
from src.ui.admin.analytics.fmt import inr, inr_compact  # noqa: E402

check("engine: delta prev=0 → New/—", AE.delta(5, 0).text == "New" and AE.delta(0, 0).text == "—"
      and AE.delta(110, 100).text == "+10.0%" and AE.delta(90, 100).tone == "danger")
check("fmt: Indian grouping", inr(123456) == "₹1,23,456" and inr(1234567.5, 2) == "₹12,34,567.50"
      and inr(999) == "₹999" and inr_compact(250000) == "₹2.5L", f"{inr(123456)} {inr(1234567.5, 2)} {inr_compact(250000)}")
check("engine: parse bill_details", [(i.name, i.qty, i.amount) for i in AE.parse_bill_details("A\t\t2\t\t10.00\nbad\nB C\t\t1\t\t5")]
      == [("A", 2, 10.0), ("B C", 1, 5.0)])
_p = AE.preset_period("30D", _date(2026, 3, 31))
check("engine: periods & buckets", _p.days == 30 and AE.previous_period(_p).end == _date(2026, 3, 1)
      and AE.bucket_for(AE.preset_period("Today")) == "hour" and AE.bucket_for(AE.preset_period("This year", _date(2026, 10, 30))) == "week"
      and AE.previous_period(AE.preset_period("This year", _date(2026, 10, 30)), "This year").start == _date(2025, 1, 1))
_cat = {"A": AE.CatalogItem(1, "1", "A", "X", 10, 0, 5, True)}
_b = [AE.BillRow("b1", _date.today(), None, 11.8, 10, 0, 1.8, [AE.LineItem("A", 1, 10)])]
check("engine: no cost price → gross profit None", AE.summarize(_b, _cat).gross_profit is None)
_cat["A"] = AE.CatalogItem(1, "1", "A", "X", 10, 6, 5, True)
check("engine: gross profit with cost", abs(AE.summarize(_b, _cat).gross_profit - 4) < 1e-9)

from PySide6.QtWidgets import QAbstractScrollArea  # noqa: E402
from src.ui.admin.analytics import AnalyticsPage  # noqa: E402
from analytics_seed import seed  # noqa: E402

base_db_path = db.db_path


def use_db(path):
    db.db_path = str(path)


def nested_scrolls(page):
    """Scroll areas inside the page other than the outer one (popups excluded)."""
    bad = []
    for sa in page.findChildren(QAbstractScrollArea):
        if sa is page.scroll or sa.window() is not page.window():
            continue
        bad.append(type(sa).__name__)
    return bad


AN_OUT = Path(os.environ.get("VV_ANALYTICS_SHOTS", OUT))
AN_OUT.mkdir(parents=True, exist_ok=True)

# Empty DB (no bills) → empty states
empty_db = tmpdir / "empty.db"
shutil.copy(real_db, empty_db)
import sqlite3  # noqa: E402
_c = sqlite3.connect(empty_db); _c.execute("DELETE FROM bill"); _c.commit(); _c.close()
use_db(empty_db)
ep = AnalyticsPage()
ep.showNormal(); ep.resize(1208, 900)
check("analytics empty: loads", ep.wait_until_loaded() and ep.snapshot is not None)
settle(100)
check("analytics empty: KPIs zero, profit —", ep.kpis["revenue"].value.text() == "₹0" and ep.kpis["profit"].value.text() == "—",
      f"{ep.kpis['revenue'].value.text()} {ep.kpis['profit'].value.text()}")
check("analytics empty: no '100%' growth or margin anywhere",
      not any("100.0%" in l.text() for l in ep.findChildren(QLabel)))
ep.grab().save(str(AN_OUT / "analytics_empty.png"))
ep.close()

# Seeded copy (~90 days of synthetic bills) → meaningful charts
seeded_db = tmpdir / "seeded.db"
shutil.copy(real_db, seeded_db)
n_seed = seed(seeded_db, 90)
use_db(seeded_db)
ap = AnalyticsPage()
ap.showNormal(); ap.resize(1208, 900)
check("analytics seeded: async load", ap.wait_until_loaded() and ap.snapshot.summary.bills > 500, f"{n_seed} seeded")
settle(100)
s30 = ap.snapshot
check("analytics: revenue = sum of bill totals", abs(s30.summary.revenue - sum(s30.revenue_series)) < 0.01)
check("analytics: gross profit shown", ap.kpis["profit"].value.text().startswith("₹"), ap.kpis["profit"].value.text())
check("analytics: 30D daily buckets", s30.bucket == "day" and len(s30.revenue_series) == 30)
check("analytics: categories from simple_products", {c.category for c in s30.categories} - {"Other"} <= 
      {r["category"] for r in db.execute_query("SELECT category FROM simple_products")})
check("analytics: no legacy catalogue names", not any(t.name in ("Shev", "d1", "Test Product") for t in s30.top_products))
check("analytics: heatmap has a peak", ap.heatmap.peak() is not None)
check("analytics: restock + slow movers", len(s30.inventory.attention) > 0 and len(s30.slow_movers) > 0)
check("analytics: below-cost item flagged", any(m.name == "Vaseline" for m in s30.below_cost))
for preset in AE.PRESETS[:-1]:
    def run(pr=preset):
        ap.set_preset(pr, blocking=True)
        settle(20)
        sn = ap.snapshot
        assert sn.preset == pr and len(sn.revenue_series) == len(sn.labels) == len(sn.prev_revenue_series)
        assert sn.bucket == {"Today": "hour", "7D": "day", "30D": "day", "90D": "day", "This year": "week"}[pr]
        assert not nested_scrolls(ap), nested_scrolls(ap)
    step(f"analytics range {preset}", run)
ap.set_preset("Today", blocking=True); settle(50)
ap.grab().save(str(AN_OUT / "analytics_today.png"))
def custom_range():
    ap.set_custom_range(_date.today() - _td(days=13), _date.today() - _td(days=7), blocking=True)
    assert ap.snapshot.period.days == 7, ap.snapshot.period
    assert ap.preset == "Custom" and ap.range_control.currentText() == "Custom"
    assert ap.snapshot.previous.end == _date.today() - _td(days=14)
step("analytics custom range", custom_range)
ap.set_custom_range(_date.today(), _date.today() - _td(days=400), blocking=True)
check("analytics custom >400 days → monthly, swapped bounds", ap.snapshot.bucket == "month"
      and ap.snapshot.period.start < ap.snapshot.period.end, ap.snapshot.bucket)
ap.set_preset("30D", blocking=True)
ap.compare_toggle.setChecked(False)
check("compare off hides deltas & overlay", not ap.kpis["revenue"].pill.isVisible() and not ap.trend.show_prev)
ap.compare_toggle.setChecked(True)
check("compare on shows deltas", ap.kpis["revenue"].pill.isVisibleTo(ap) and ap.trend.show_prev)
csv_path = ap.export_csv(str(tmpdir / "analytics.csv"))
txt = Path(csv_path).read_text(encoding="utf-8") if csv_path else ""
check("analytics export CSV", "Top products" in txt and "Restock suggestions" in txt and "Summary" in txt)
pdf_path = ap.export_pdf(str(tmpdir / "analytics.pdf"))
check("analytics export PDF", pdf_path and Path(pdf_path).read_bytes()[:4] == b"%PDF")

# scrolling: single outer scroll area that actually moves the content
settle(50)
sb = ap.scroll.verticalScrollBar()
check("scroll: outer scrollbar has range", sb.maximum() > 0, f"max={sb.maximum()}")
check("scroll: no nested scroll areas", not nested_scrolls(ap), str(nested_scrolls(ap)))
y0 = ap.body.mapTo(ap.scroll.viewport(), ap.body.rect().topLeft()).y()
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtCore import QPoint, QPointF  # noqa: E402
target = ap.trend
pos = QPointF(target.width() / 2, target.height() / 2)


def wheel(widget):
    e = QWheelEvent(pos, QPointF(widget.mapToGlobal(pos.toPoint())), QPoint(0, 0), QPoint(0, -360),
                    Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, e)
    return e


# Real wheel events are spontaneous and bubble up when ignored; sendEvent does not
# bubble, so check both halves: charts/cards ignore the wheel, the viewport scrolls.
ignored = all(not wheel(w).isAccepted() for w in (ap.trend, ap.heatmap, ap.kpis["revenue"].spark))
check("scroll: charts don't swallow wheel events", ignored)
wheel(ap.scroll.viewport())
settle(30)
y1 = ap.body.mapTo(ap.scroll.viewport(), ap.body.rect().topLeft()).y()
check("scroll: wheel scrolls the page content", sb.value() > 0 and y1 < y0, f"value={sb.value()} y0={y0} y1={y1}")
sb.setValue(sb.maximum())
settle(20)
check("scroll: can reach the bottom", sb.value() == sb.maximum())
sb.setValue(0)

# (i) info markers show their explanation on click and hide on leave
from src.ui.admin.analytics.components import InfoDot  # noqa: E402
dots = ap.findChildren(InfoDot)
if dots:
    QTest.mouseClick(dots[0], Qt.LeftButton)
    settle(30)
    bub = InfoDot._popover
    check("info (i) shows its explanation on click", bub is not None and bub.isVisible() and bool(bub.text()),
          "" if bub is None else bub.text())
    QApplication.sendEvent(dots[0], QEvent(QEvent.Leave))
    check("info (i) hides on mouse leave", not bub.isVisible())
else:
    check("info (i) markers present on KPI cards", False)

# responsive KPI grid
g = ap.kpi_grid
check("responsive KPI grid (2-4 cols)", g.columns_for(640) == 2 and g.columns_for(900) == 3 and g.cols == 3
      and g.columns_for(2400) in (2, 3), f"{g.columns_for(640)} {g.columns_for(900)} {g.cols}")
ap.resize(1208, 900); settle(80)
ap.grab().save(str(AN_OUT / "analytics_seeded_viewport.png"))
ap.close()
use_db(base_db_path)

check("real store.db untouched", hashlib.md5(real_db.read_bytes()).hexdigest() == real_md5)
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
for f in fails:
    print("FAILED:", f)
print("test db:", test_db)
sys.exit(1 if fails else 0)
