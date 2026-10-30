"""
Seed a COPY of store.db with realistic synthetic sales for analytics tests
and screenshots. Never point this at data/store.db.

Usage:  python tests/analytics_seed.py /tmp/some/store.db [days]
"""
from __future__ import annotations

import random
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# (barcode, name, mrp, cost, stock, category, popularity weight)
CATALOGUE = [
    ("8904063201011", "Haldiram Aloo Bhujia 400g", 99, 75, 49, "Namkeen", 9),
    ("8904063201028", "Haldiram Sev 200g", 45, 35, 99, "Namkeen", 6),
    ("8904063201035", "Jaylaxmi Special Mix 500g", 120, 85, 75, "Namkeen", 5),
    ("8904063201042", "Haldiram Moong Dal 200g", 55, 41, 6, "Namkeen", 5),
    ("8901063010017", "Parle-G Biscuit 800g", 55, 45, 200, "Biscuits", 10),
    ("8901063010024", "Britannia Good Day 250g", 40, 32, 150, "Biscuits", 7),
    ("8901063010031", "Britannia Marie Gold 250g", 35, 28, 0, "Biscuits", 4),
    ("8901063010048", "Sunfeast Dark Fantasy 75g", 40, 31, 60, "Biscuits", 4),
    ("8901491101011", "Lay's Classic Salted 52g", 20, 15.5, 140, "Chips", 9),
    ("8901491101028", "Kurkure Masala Munch 90g", 20, 15, 8, "Chips", 8),
    ("8901491101035", "Bingo Mad Angles 66g", 20, 15.2, 90, "Chips", 5),
    ("8906001200017", "Kaju Katli 250g", 320, 240, 18, "Sweets", 3),
    ("8906001200024", "Soan Papdi 500g", 150, 105, 25, "Sweets", 3),
    ("8906001200031", "Gulab Jamun Tin 1kg", 260, 0, 12, "Sweets", 2),
    ("8906012300017", "Almonds 250g", 299, 230, 30, "Dry Fruits", 3),
    ("8906012300024", "Cashew W320 250g", 349, 270, 4, "Dry Fruits", 2),
    ("8906012300031", "Raisins 200g", 110, 78, 40, "Dry Fruits", 2),
    ("8901030700017", "Thums Up 750ml", 40, 32, 72, "Beverages", 7),
    ("8901030700024", "Frooti 600ml", 35, 27, 3, "Beverages", 6),
    ("8901030700031", "Bisleri 1L", 20, 13, 120, "Beverages", 8),
    ("8901262010017", "Amul Butter 100g", 58, 52, 20, "Dairy", 6),
    ("8901262010024", "Amul Taaza 500ml", 27, 24, 36, "Dairy", 8),
    ("8909106056268", "Vaseline", 75, 80, 89, "Skin Care", 2),
    ("8901030812345", "Dove Soap 100g", 62, 50, 28, "Personal Care", 3),
    ("8901030898765", "Colgate MaxFresh 150g", 110, 88, 22, "Personal Care", 3),
    # never/rarely sold → slow movers
    ("8906099900011", "Pista Salted 200g", 260, 205, 15, "Dry Fruits", 0),
    ("8906099900028", "Chyawanprash 500g", 245, 190, 9, "Health", 0),
    ("8906099900035", "Rose Sharbat 750ml", 160, 118, 14, "Beverages", 0),
]

# Relative traffic by local hour (shop open 8:00–22:00)
HOUR_WEIGHTS = {8: 2, 9: 4, 10: 6, 11: 8, 12: 9, 13: 7, 14: 4, 15: 3, 16: 4, 17: 7, 18: 10, 19: 12, 20: 10, 21: 5}
DAY_WEIGHTS = [0.85, 0.8, 0.85, 0.9, 1.05, 1.35, 1.25]   # Mon..Sun
IST = timezone(timedelta(hours=5, minutes=30))


def seed(db_path: str | Path, days: int = 90, today: date | None = None, rng_seed: int = 42,
         with_payments: bool = False) -> int:
    """Insert products (if missing) and ``days`` of bills. Returns bills inserted."""
    rng = random.Random(rng_seed)
    today = today or date.today()
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    for bc, name, mrp, cost, stock, cat, _w in CATALOGUE:
        row = cur.execute("SELECT id FROM simple_products WHERE name = ?", (name,)).fetchone()
        if row:
            cur.execute("UPDATE simple_products SET mrp=?, cost_price=?, stock=?, category=? WHERE id=?",
                        (mrp, cost, stock, cat, row[0]))
        else:
            cur.execute("INSERT INTO simple_products (barcode, name, mrp, cost_price, stock, category) "
                        "VALUES (?,?,?,?,?,?)", (bc, name, mrp, cost, stock, cat))
    sellable = [c for c in CATALOGUE if c[6] > 0]
    weights = [c[6] for c in sellable]
    hours, hweights = list(HOUR_WEIGHTS), list(HOUR_WEIGHTS.values())
    n = 0
    for back in range(days, -1, -1):
        d = today - timedelta(days=back)
        growth = 0.75 + 0.5 * (1 - back / max(days, 1))           # gentle upward trend
        count = int(rng.gauss(26, 5) * DAY_WEIGHTS[d.weekday()] * growth)
        if back == 0:
            count = max(4, count // 2)      # today is still in progress
        times = sorted(rng.choices(hours, hweights, k=max(0, count)))
        for seq, h in enumerate(times, 1):
            local = datetime(d.year, d.month, d.day, h, rng.randint(0, 59), rng.randint(0, 59), tzinfo=IST)
            created = local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            lines = rng.choices(sellable, weights, k=rng.choices([1, 2, 3, 4, 5], [30, 30, 20, 12, 8])[0])
            agg: dict = {}
            for c in lines:
                agg[c[1]] = (c, agg.get(c[1], (c, 0))[1] + rng.choices([1, 2, 3], [70, 22, 8])[0])
            details, subtotal = [], 0.0
            for name, (c, q) in agg.items():
                amt = c[2] * q
                subtotal += amt
                details.append(f"{name}\t\t{q}\t\t{amt:.2f}")
            discount = round(subtotal * 0.05, 2) if subtotal > 400 and rng.random() < 0.4 else 0.0
            tax = round((subtotal - discount) * 0.18, 2)
            total = round(subtotal - discount + tax, 2)
            bill_no = f"SEED-{d.strftime('%Y%m%d')}-{seq:04d}"
            cur.execute(
                "INSERT INTO bill (bill_no, date, customer_name, customer_no, subtotal, discount, tax_rate, "
                "tax_amount, total, bill_details, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (bill_no, d.isoformat(), "Walk-in", "", subtotal, discount, 18.0, tax, total,
                 "\n".join(details), created))
            if with_payments:
                method = rng.choices(["UPI", "CASH", "CARD"], [55, 35, 10])[0]
                cur.execute("INSERT INTO payment_transactions (bill_id, payment_method, amount, payment_status, "
                            "payment_timestamp) VALUES (?,?,?,?,?)",
                            (cur.lastrowid, method, total, "COMPLETED", local.strftime("%Y-%m-%dT%H:%M:%S")))
            n += 1
    conn.commit()
    conn.close()
    return n


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve()
    real = (Path(__file__).resolve().parents[1] / "data" / "store.db").resolve()
    if target == real:
        sys.exit("Refusing to seed the real data/store.db")
    print(seed(target, int(sys.argv[2]) if len(sys.argv) > 2 else 90), "bills inserted")
