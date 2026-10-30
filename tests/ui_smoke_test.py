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

real_db = REPO / "data" / "store.db"
real_md5 = hashlib.md5(real_db.read_bytes()).hexdigest()
tmpdir = Path(tempfile.mkdtemp(prefix="vvtest_"))
test_db = tmpdir / "store.db"
shutil.copy(real_db, test_db)

import config  # noqa: E402
config.DATABASE_PATH = test_db
config.GENERATED_BILLS_DIR = tmpdir / "bills"
config.GENERATED_BILLS_DIR.mkdir()

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtGui import QKeyEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog  # noqa: E402

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
for key in ["invoices", "inventory", "products", "types", "analytics", "team"]:
    def go(k=key):
        dash.navigate(k)
        settle(200)
        assert dash.stack.currentWidget() is dash._pages[k]
        if k == "analytics":
            QTest.qWait(600)
            settle(200)
        shot(dash, f"admin_{k}")
    step(f"admin page {key}", go)
# embedded close button returns to overview
dash.navigate("inventory")
settle()
dash._pages["inventory"].close()
settle()
check("embedded close returns to overview", dash.current_page == "overview")
for rng in ["Yesterday", "Last 7 days", "Last 30 days", "Today"]:
    step(f"overview range {rng}", lambda r=rng: dash.overview.range_combo.setCurrentText(r))
dash.overview.range_combo.setCurrentText("Last 30 days")
settle()
shot(dash, "admin_overview_30d")
dash.overview.range_combo.setCurrentText("Today")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(tmpdir / "export.csv"), ""))
dash.overview.export_csv()
check("export csv", (tmpdir / "export.csv").exists())

# dialogs
def dialogs():
    from src.ui.admin.brands import BrandDialog
    from src.ui.admin.employees import EmployeeDialog
    from src.ui.admin.product_types import ProductTypeDialog
    from src.ui.admin.product_dialog import ProductDialog, VariantDialog
    from src.ui.admin.invoices import BillViewDialog
    from src.logic.billing import BillingService
    for name, d in [("brand_dialog", BrandDialog(dash)), ("employee_dialog", EmployeeDialog(dash)),
                    ("product_type_dialog", ProductTypeDialog(dash)), ("product_dialog", ProductDialog(dash)),
                    ("variant_dialog", VariantDialog(dash, "Test")),
                    ("bill_view_dialog", BillViewDialog(dash, BillingService().search_bills()[0]))]:
        d.show()
        settle()
        d.grab().save(str(OUT / f"{name}.png"))
        d.close()
step("all admin dialogs instantiate", dialogs)

def legacy_analytics():
    from src.ui.admin.analytics import ModernAnalyticsWindow
    w = ModernAnalyticsWindow()
    w.close()
step("legacy ModernAnalyticsWindow still instantiates", legacy_analytics)

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

check("real store.db untouched", hashlib.md5(real_db.read_bytes()).hexdigest() == real_md5)
fails = [r for r in results if not r[1]]
print(f"\n{len(results) - len(fails)}/{len(results)} checks passed")
for f in fails:
    print("FAILED:", f)
print("test db:", test_db)
sys.exit(1 if fails else 0)
