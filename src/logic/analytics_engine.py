"""
Analytics engine for the admin Analytics page.

Everything here reads the tables the POS actually uses:

* ``bill``             – one row per sale; line items live in ``bill_details``
                         as tab-separated ``name\\t\\tqty\\t\\tamount`` lines.
* ``simple_products``  – the POS catalogue (category, MRP, cost price, stock).
* ``payment_transactions`` – optional; only used when it has rows.

The module is split in two layers:

1. **Fetchers** (``fetch_*``) – small, parameterised, read-only SELECTs.
2. **Pure functions** – take plain dataclasses / lists and return results.
   They never touch the database or Qt, so they are trivially unit-testable.

``build_snapshot`` glues both together and is what the UI calls (off the UI
thread). Nothing in this module writes to the database.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from src.database.connection import db

# Presets shown in the UI, in order.
PRESETS: Tuple[str, ...] = ("Today", "7D", "30D", "90D", "This year", "Custom")

LOW_STOCK_THRESHOLD = 10        # same threshold the Overview page uses
REORDER_TARGET_DAYS = 14        # suggested reorder brings cover up to this
VELOCITY_WINDOW_DAYS = 30       # window for "avg units / day" and dead stock
UNCATEGORISED = "Uncategorised"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Period:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end


@dataclass(frozen=True)
class LineItem:
    name: str
    qty: int
    amount: float           # line total before bill discount and tax


@dataclass
class BillRow:
    bill_no: str
    day: date
    local_dt: Optional[datetime]     # local time the bill was created, if known
    total: float                     # what the customer paid (after discount, incl. tax)
    subtotal: float
    discount: float
    tax: float
    items: List[LineItem] = field(default_factory=list)

    @property
    def units(self) -> int:
        return sum(i.qty for i in self.items)

    @property
    def net_factor(self) -> float:
        """Share of each line amount kept after the bill-level discount."""
        if self.subtotal <= 0:
            return 1.0
        return max(0.0, (self.subtotal - self.discount) / self.subtotal)


@dataclass(frozen=True)
class CatalogItem:
    id: int
    barcode: str
    name: str
    category: str
    mrp: float
    cost: float              # 0 = unknown
    stock: int
    active: bool

    @property
    def has_cost(self) -> bool:
        return self.cost > 0


@dataclass(frozen=True)
class Delta:
    text: str                # "+12.4%", "-3.0%", "New", "—"
    tone: str                # success | danger | neutral
    pct: Optional[float]     # None when not computable


@dataclass
class Summary:
    revenue: float = 0.0
    bills: int = 0
    units: int = 0
    net_sales: float = 0.0          # line totals after discount, before tax
    covered_net: float = 0.0        # net sales of items with a known cost price
    covered_cost: float = 0.0

    @property
    def avg_bill(self) -> float:
        return self.revenue / self.bills if self.bills else 0.0

    @property
    def items_per_bill(self) -> float:
        return self.units / self.bills if self.bills else 0.0

    @property
    def cost_coverage(self) -> float:
        """Fraction (0-1) of net sales whose cost price is known."""
        return self.covered_net / self.net_sales if self.net_sales > 0 else 0.0

    @property
    def gross_profit(self) -> Optional[float]:
        if self.covered_net <= 0:
            return None
        return self.covered_net - self.covered_cost

    @property
    def gross_margin(self) -> Optional[float]:
        gp = self.gross_profit
        if gp is None or self.covered_net <= 0:
            return None
        return gp / self.covered_net


@dataclass
class ProductStat:
    name: str
    category: str
    units: int = 0
    sales: float = 0.0          # line totals (before discount/tax)
    net: float = 0.0            # after bill discount, before tax
    cost: Optional[float] = None  # None when cost price unknown

    @property
    def profit(self) -> Optional[float]:
        return None if self.cost is None else self.net - self.cost

    @property
    def margin(self) -> Optional[float]:
        p = self.profit
        return None if p is None or self.net <= 0 else p / self.net


@dataclass
class TopProduct:
    rank: int
    name: str
    category: str
    units: int
    sales: float
    share: float                 # of total line sales in the period
    trend: Delta


@dataclass
class CategoryShare:
    category: str
    sales: float
    units: int
    share: float


@dataclass
class StockRow:
    name: str
    category: str
    stock: int
    avg_daily: float             # units / day over the velocity window
    days_cover: Optional[float]  # None = no recent sales
    reorder_qty: int
    status: str                  # "Out of stock" | "Low" | "Running out" | "OK"
    tone: str


@dataclass
class SlowMover:
    name: str
    category: str
    stock: int
    value: float                 # stock tied up (at cost if known, else MRP)
    last_sold: Optional[date]


@dataclass
class InventoryHealth:
    products: int = 0
    stock_value_cost: float = 0.0
    stock_value_mrp: float = 0.0
    missing_cost: int = 0
    low_stock: int = 0
    out_of_stock: int = 0
    attention: List[StockRow] = field(default_factory=list)


@dataclass
class MarginRow:
    name: str
    sales: float
    profit: float
    margin: float


@dataclass
class Snapshot:
    preset: str
    period: Period
    previous: Period
    bucket: str                               # hour | day | week | month
    generated_at: datetime
    summary: Summary
    prev_summary: Summary
    labels: List[str]                         # x-axis captions
    long_labels: List[str]                    # tooltip captions
    revenue_series: List[float]
    prev_revenue_series: List[float]
    prev_long_labels: List[str]
    sparks: Dict[str, List[float]]
    heatmap: List[List[float]]                # [weekday 0=Mon][hour 0-23] revenue
    heatmap_bills: List[List[int]]
    categories: List[CategoryShare]
    top_products: List[TopProduct]
    slow_movers: List[SlowMover]
    inventory: InventoryHealth
    margin_by_category: List[MarginRow]
    margin_by_product: List[MarginRow]
    below_cost: List[MarginRow]
    payments: List[Tuple[str, float, int]]    # (method, amount, count); empty if no data
    catalog_size: int
    has_any_bills: bool
    same_time: bool = False                   # previous KPIs cut at the current time of day


# ---------------------------------------------------------------------------
# Periods & buckets (pure)
# ---------------------------------------------------------------------------
def preset_period(preset: str, today: Optional[date] = None,
                  custom: Optional[Tuple[date, date]] = None) -> Period:
    today = today or date.today()
    if preset == "Today":
        return Period(today, today)
    if preset == "7D":
        return Period(today - timedelta(days=6), today)
    if preset == "30D":
        return Period(today - timedelta(days=29), today)
    if preset == "90D":
        return Period(today - timedelta(days=89), today)
    if preset == "This year":
        return Period(date(today.year, 1, 1), today)
    if preset == "Custom" and custom:
        a, b = custom
        return Period(min(a, b), max(a, b))
    return Period(today - timedelta(days=29), today)


def previous_period(period: Period, preset: str = "") -> Period:
    """Comparison window. 'This year' compares with the same dates last year;
    everything else with the equally long window right before it."""
    if preset == "This year":
        s, e = period.start, period.end
        try:
            return Period(s.replace(year=s.year - 1), e.replace(year=e.year - 1))
        except ValueError:      # 29 Feb
            return Period(s.replace(year=s.year - 1), e.replace(year=e.year - 1, day=28))
    span = period.days
    end = period.start - timedelta(days=1)
    return Period(end - timedelta(days=span - 1), end)


def bucket_for(period: Period) -> str:
    if period.days <= 1:
        return "hour"
    if period.days <= 92:
        return "day"
    if period.days <= 400:
        return "week"
    return "month"


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def hour_label(h: int, long: bool = False) -> str:
    hh = h % 12 or 12
    if long:
        return f"{hh} {'AM' if h < 12 else 'PM'}"
    return f"{hh}{'a' if h < 12 else 'p'}"


def bucket_keys(period: Period, bucket: str, hours: Tuple[int, int] = (0, 23)
                ) -> List[Tuple[object, str, str]]:
    """Ordered (key, short label, long label) for every bucket in ``period``.
    Empty buckets are included so the time axis is continuous."""
    out: List[Tuple[object, str, str]] = []
    if bucket == "hour":
        for h in range(hours[0], hours[1] + 1):
            out.append((h, hour_label(h), f"{period.start.strftime('%a %d %b')}, {hour_label(h, True)}"))
    elif bucket == "day":
        d = period.start
        while d <= period.end:
            out.append((d, d.strftime("%d %b").lstrip("0"), d.strftime("%a, %d %b %Y")))
            d += timedelta(days=1)
    elif bucket == "week":
        d = _week_start(period.start)
        while d <= period.end:
            e = min(d + timedelta(days=6), period.end)
            s = max(d, period.start)
            out.append((d, s.strftime("%d %b").lstrip("0"),
                        f"Week of {s.strftime('%d %b').lstrip('0')} – {e.strftime('%d %b %Y').lstrip('0')}"))
            d += timedelta(days=7)
    else:
        y, m = period.start.year, period.start.month
        while (y, m) <= (period.end.year, period.end.month):
            d = date(y, m, 1)
            out.append(((y, m), d.strftime("%b"), d.strftime("%B %Y")))
            m += 1
            if m > 12:
                y, m = y + 1, 1
    return out


def bucket_key_of(bill: BillRow, bucket: str) -> object:
    if bucket == "hour":
        return bill.local_dt.hour if bill.local_dt else None
    if bucket == "day":
        return bill.day
    if bucket == "week":
        return _week_start(bill.day)
    return (bill.day.year, bill.day.month)


def shop_hours(bills: Iterable[BillRow], default: Tuple[int, int] = (9, 21)) -> Tuple[int, int]:
    hrs = [b.local_dt.hour for b in bills if b.local_dt]
    if not hrs:
        return default
    return min(min(hrs), default[0]), max(max(hrs), default[1])


# ---------------------------------------------------------------------------
# Parsing (pure)
# ---------------------------------------------------------------------------
def parse_bill_details(text: Optional[str]) -> List[LineItem]:
    """Parse ``bill_details`` (``name\\t\\tqty\\t\\tamount`` per line)."""
    items: List[LineItem] = []
    for line in (text or "").strip().splitlines():
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) < 3:
            continue
        try:
            items.append(LineItem(parts[0], int(float(parts[1])), float(parts[2])))
        except ValueError:
            continue
    return items


def utc_to_local(created_at: Optional[str]) -> Optional[datetime]:
    """``created_at`` is SQLite CURRENT_TIMESTAMP (UTC). Return naive local time."""
    if not created_at:
        return None
    try:
        dt = datetime.strptime(str(created_at)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)


def _to_date(s: str) -> Optional[date]:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Fetchers (read-only SQL)
# ---------------------------------------------------------------------------
def fetch_bills(start: date, end: date) -> List[BillRow]:
    rows = db.execute_query(
        "SELECT bill_no, date, created_at, total, subtotal, discount, tax_amount, bill_details "
        "FROM bill WHERE date BETWEEN ? AND ? ORDER BY date, created_at",
        (start.isoformat(), end.isoformat()))
    out: List[BillRow] = []
    for r in rows:
        d = _to_date(r["date"])
        if d is None:
            continue
        out.append(BillRow(
            bill_no=r["bill_no"], day=d, local_dt=utc_to_local(r.get("created_at")),
            total=float(r.get("total") or 0), subtotal=float(r.get("subtotal") or 0),
            discount=float(r.get("discount") or 0), tax=float(r.get("tax_amount") or 0),
            items=parse_bill_details(r.get("bill_details"))))
    return out


def fetch_catalog() -> Dict[str, CatalogItem]:
    rows = db.execute_query(
        "SELECT id, barcode, name, mrp, cost_price, stock, category, is_active FROM simple_products")
    cat: Dict[str, CatalogItem] = {}
    for r in rows:
        cat[r["name"]] = CatalogItem(
            id=int(r["id"]), barcode=r.get("barcode") or "", name=r["name"],
            category=(r.get("category") or "").strip() or UNCATEGORISED,
            mrp=float(r.get("mrp") or 0), cost=float(r.get("cost_price") or 0),
            stock=int(r.get("stock") or 0), active=bool(r.get("is_active", 1)))
    return cat


def fetch_has_any_bills() -> bool:
    return bool(db.execute_query("SELECT 1 FROM bill LIMIT 1"))


def fetch_payment_split(period: Period) -> List[Tuple[str, float, int]]:
    """Payment methods from ``payment_transactions`` (empty when unused)."""
    try:
        rows = db.execute_query(
            "SELECT UPPER(payment_method) AS method, SUM(amount) AS amount, COUNT(*) AS n "
            "FROM payment_transactions "
            "WHERE date(payment_timestamp) BETWEEN ? AND ? "
            "AND COALESCE(payment_status, 'COMPLETED') = 'COMPLETED' "
            "GROUP BY UPPER(payment_method) ORDER BY amount DESC",
            (period.start.isoformat(), period.end.isoformat()))
    except Exception:  # noqa: BLE001 - table may not exist on old DBs
        return []
    return [(r["method"], float(r["amount"] or 0), int(r["n"] or 0)) for r in rows if r["method"]]


# ---------------------------------------------------------------------------
# Pure computations
# ---------------------------------------------------------------------------
def delta(current: float, previous: float) -> Delta:
    """Percentage change with sane handling of a zero baseline."""
    if previous == 0:
        if current == 0:
            return Delta("—", "neutral", None)
        return Delta("New", "success" if current > 0 else "danger", None)
    pct = (current - previous) / abs(previous) * 100
    if abs(pct) < 0.05:
        return Delta("0.0%", "neutral", 0.0)
    return Delta(f"{pct:+.1f}%", "success" if pct > 0 else "danger", pct)


def summarize(bills: Sequence[BillRow], catalog: Dict[str, CatalogItem]) -> Summary:
    s = Summary()
    for b in bills:
        s.revenue += b.total
        s.bills += 1
        f = b.net_factor
        for it in b.items:
            s.units += it.qty
            net = it.amount * f
            s.net_sales += net
            c = catalog.get(it.name)
            if c and c.has_cost:
                s.covered_net += net
                s.covered_cost += c.cost * it.qty
    return s


def series(bills: Sequence[BillRow], keys: Sequence[Tuple[object, str, str]], bucket: str,
           metric: str = "revenue") -> List[float]:
    """Aggregate ``metric`` (revenue|bills|units) per bucket key."""
    idx = {k: i for i, (k, _a, _b) in enumerate(keys)}
    vals = [0.0] * len(keys)
    for b in bills:
        i = idx.get(bucket_key_of(b, bucket))
        if i is None:
            continue
        if metric == "revenue":
            vals[i] += b.total
        elif metric == "bills":
            vals[i] += 1
        elif metric == "units":
            vals[i] += b.units
    return vals


def kpi_sparks(bills: Sequence[BillRow], catalog: Dict[str, CatalogItem],
               keys: Sequence[Tuple[object, str, str]], bucket: str) -> Dict[str, List[float]]:
    """Per-bucket series for every KPI card sparkline."""
    idx = {k: i for i, (k, _a, _b) in enumerate(keys)}
    per: List[List[BillRow]] = [[] for _ in keys]
    for b in bills:
        i = idx.get(bucket_key_of(b, bucket))
        if i is not None:
            per[i].append(b)
    out: Dict[str, List[float]] = defaultdict(list)
    for group in per:
        s = summarize(group, catalog)
        out["revenue"].append(s.revenue)
        out["profit"].append(s.gross_profit or 0.0)
        out["bills"].append(float(s.bills))
        out["avg_bill"].append(s.avg_bill)
        out["units"].append(float(s.units))
        out["items_per_bill"].append(s.items_per_bill)
    return dict(out)


def heatmap(bills: Sequence[BillRow]) -> Tuple[List[List[float]], List[List[int]]]:
    rev = [[0.0] * 24 for _ in range(7)]
    cnt = [[0] * 24 for _ in range(7)]
    for b in bills:
        if not b.local_dt:
            continue
        wd, h = b.local_dt.weekday(), b.local_dt.hour
        rev[wd][h] += b.total
        cnt[wd][h] += 1
    return rev, cnt


def product_stats(bills: Sequence[BillRow], catalog: Dict[str, CatalogItem]) -> Dict[str, ProductStat]:
    stats: Dict[str, ProductStat] = {}
    for b in bills:
        f = b.net_factor
        for it in b.items:
            c = catalog.get(it.name)
            st = stats.get(it.name)
            if st is None:
                st = stats[it.name] = ProductStat(it.name, c.category if c else UNCATEGORISED,
                                                  cost=0.0 if (c and c.has_cost) else None)
            st.units += it.qty
            st.sales += it.amount
            st.net += it.amount * f
            if st.cost is not None and c is not None:
                st.cost += c.cost * it.qty
    return stats


def top_products(current: Dict[str, ProductStat], previous: Dict[str, ProductStat],
                 limit: int = 10) -> List[TopProduct]:
    total = sum(s.sales for s in current.values()) or 1.0
    ranked = sorted(current.values(), key=lambda s: (-s.sales, -s.units, s.name))[:limit]
    out = []
    for i, s in enumerate(ranked, 1):
        p = previous.get(s.name)
        out.append(TopProduct(i, s.name, s.category, s.units, s.sales, s.sales / total,
                              delta(s.sales, p.sales if p else 0.0)))
    return out


def category_breakdown(stats: Dict[str, ProductStat], max_slices: int = 6) -> List[CategoryShare]:
    agg: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0])
    for s in stats.values():
        agg[s.category][0] += s.sales
        agg[s.category][1] += s.units
    total = sum(v[0] for v in agg.values())
    if total <= 0:
        return []
    rows = sorted(agg.items(), key=lambda kv: -kv[1][0])
    if len(rows) > max_slices:
        head, tail = rows[:max_slices - 1], rows[max_slices - 1:]
        rows = head + [("Other", [sum(v[0] for _k, v in tail), sum(v[1] for _k, v in tail)])]
    return [CategoryShare(k, v[0], int(v[1]), v[0] / total) for k, v in rows]


def units_by_product(bills: Sequence[BillRow]) -> Dict[str, int]:
    out: Dict[str, int] = defaultdict(int)
    for b in bills:
        for it in b.items:
            out[it.name] += it.qty
    return dict(out)


def last_sold_dates(bills: Sequence[BillRow]) -> Dict[str, date]:
    out: Dict[str, date] = {}
    for b in bills:
        for it in b.items:
            if it.name not in out or b.day > out[it.name]:
                out[it.name] = b.day
    return out


def inventory_health(catalog: Dict[str, CatalogItem], units_recent: Dict[str, int],
                     window_days: int = VELOCITY_WINDOW_DAYS, threshold: int = LOW_STOCK_THRESHOLD,
                     target_days: int = REORDER_TARGET_DAYS, limit: int = 8) -> InventoryHealth:
    h = InventoryHealth()
    rows: List[StockRow] = []
    for c in catalog.values():
        if not c.active:
            continue
        h.products += 1
        stock = max(0, c.stock)
        h.stock_value_mrp += stock * c.mrp
        if c.has_cost:
            h.stock_value_cost += stock * c.cost
        elif stock > 0:
            h.missing_cost += 1
        avg = units_recent.get(c.name, 0) / window_days if window_days else 0.0
        cover = (stock / avg) if avg > 0 else None
        reorder = max(0, math.ceil(avg * target_days - stock)) if avg > 0 else (threshold if stock <= 0 else 0)
        if stock <= 0:
            status, tone = "Out of stock", "danger"
            h.out_of_stock += 1
        elif stock <= threshold:
            status, tone = "Low", "warning"
            h.low_stock += 1
        elif cover is not None and cover < target_days:
            status, tone = "Running out", "warning"
        else:
            continue
        rows.append(StockRow(c.name, c.category, stock, avg, cover, reorder, status, tone))
    rows.sort(key=lambda r: (0 if r.stock <= 0 else 1,
                             r.days_cover if r.days_cover is not None else 10_000, r.stock, r.name))
    h.attention = rows[:limit]
    return h


def slow_movers(catalog: Dict[str, CatalogItem], last_sold: Dict[str, date], ref: date,
                days: int = VELOCITY_WINDOW_DAYS, limit: int = 8) -> List[SlowMover]:
    cutoff = ref - timedelta(days=days - 1)
    out = []
    for c in catalog.values():
        if not c.active or c.stock <= 0:
            continue
        ls = last_sold.get(c.name)
        if ls is not None and ls >= cutoff:
            continue
        unit = c.cost if c.has_cost else c.mrp
        out.append(SlowMover(c.name, c.category, c.stock, c.stock * unit, ls))
    out.sort(key=lambda s: (-s.value, s.name))
    return out[:limit]


def margins(stats: Dict[str, ProductStat], limit: int = 8
            ) -> Tuple[List[MarginRow], List[MarginRow], List[MarginRow]]:
    """(by category, by product (top profit), selling below cost)."""
    costed = [s for s in stats.values() if s.cost is not None and s.net > 0]
    cat: Dict[str, List[float]] = defaultdict(lambda: [0.0, 0.0])
    for s in costed:
        cat[s.category][0] += s.net
        cat[s.category][1] += s.profit or 0.0
    by_cat = sorted((MarginRow(k, v[0], v[1], v[1] / v[0] if v[0] else 0.0) for k, v in cat.items()),
                    key=lambda r: -r.profit)
    by_prod = sorted((MarginRow(s.name, s.net, s.profit or 0.0, s.margin or 0.0) for s in costed),
                     key=lambda r: -r.profit)
    below = sorted((r for r in by_prod if r.profit < 0), key=lambda r: r.profit)
    return by_cat, by_prod[:limit], below[:limit]


# ---------------------------------------------------------------------------
# Snapshot (what the UI renders)
# ---------------------------------------------------------------------------
def build_snapshot(preset: str = "30D", custom: Optional[Tuple[date, date]] = None,
                   today: Optional[date] = None, now: Optional[datetime] = None) -> Snapshot:
    today = today or (now.date() if now else date.today())
    period = preset_period(preset, today, custom)
    prev = previous_period(period, preset)
    bucket = bucket_for(period)

    catalog = fetch_catalog()
    bills = fetch_bills(period.start, period.end)
    prev_bills = fetch_bills(prev.start, prev.end)
    # "Today" is still in progress: compare KPIs with yesterday *up to the same
    # time*, while the chart overlay still shows all of yesterday.
    prev_cmp = prev_bills
    same_time = preset == "Today" and period.end == today
    if same_time:
        now_t = (now or datetime.now()).time()
        prev_cmp = [b for b in prev_bills if b.local_dt is None or b.local_dt.time() <= now_t]

    hours = shop_hours(list(bills) + list(prev_bills)) if bucket == "hour" else (0, 23)
    keys = bucket_keys(period, bucket, hours)
    pkeys = bucket_keys(prev, bucket, hours)
    cur_series = series(bills, keys, bucket)
    prev_series = series(prev_bills, pkeys, bucket)
    # align previous series to the current axis length
    prev_series = (prev_series + [0.0] * len(keys))[:len(keys)]
    prev_long = ([k[2] for k in pkeys] + [""] * len(keys))[:len(keys)]

    # Sparklines use daily points for multi-day ranges (hourly for one day).
    spark_bucket = "hour" if bucket == "hour" else ("day" if period.days <= 92 else "week")
    skeys = keys if spark_bucket == bucket else bucket_keys(period, spark_bucket, hours)

    cur_stats = product_stats(bills, catalog)
    prev_stats = product_stats(prev_cmp, catalog)

    # Stock-side metrics are "as of today", independent of the selected range.
    recent = fetch_bills(today - timedelta(days=VELOCITY_WINDOW_DAYS - 1), today)
    history = fetch_bills(today - timedelta(days=365), today)
    hm, hm_n = heatmap(bills)
    by_cat, by_prod, below = margins(cur_stats)

    return Snapshot(
        preset=preset, period=period, previous=prev, bucket=bucket, generated_at=datetime.now(),
        summary=summarize(bills, catalog), prev_summary=summarize(prev_cmp, catalog), same_time=same_time,
        labels=[k[1] for k in keys], long_labels=[k[2] for k in keys],
        revenue_series=cur_series, prev_revenue_series=prev_series, prev_long_labels=prev_long,
        sparks=kpi_sparks(bills, catalog, skeys, spark_bucket),
        heatmap=hm, heatmap_bills=hm_n,
        categories=category_breakdown(cur_stats),
        top_products=top_products(cur_stats, prev_stats),
        slow_movers=slow_movers(catalog, last_sold_dates(history), today),
        inventory=inventory_health(catalog, units_by_product(recent)),
        margin_by_category=by_cat, margin_by_product=by_prod, below_cost=below,
        payments=fetch_payment_split(period),
        catalog_size=sum(1 for c in catalog.values() if c.active),
        has_any_bills=fetch_has_any_bills(),
    )


class AnalyticsEngine:
    """Thin facade kept for callers that like an object."""

    def snapshot(self, preset: str = "30D", custom: Optional[Tuple[date, date]] = None) -> Snapshot:
        return build_snapshot(preset, custom)

    def low_stock(self, threshold: int = LOW_STOCK_THRESHOLD) -> List[CatalogItem]:
        items = [c for c in fetch_catalog().values() if c.active and c.stock <= threshold]
        return sorted(items, key=lambda c: (c.stock, c.name))
