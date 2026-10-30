"""CSV / PDF export of the Analytics view currently on screen."""
from __future__ import annotations

import csv
from typing import List, Sequence

from src.logic.analytics_engine import Snapshot, delta
from src.ui.admin.analytics.fmt import date_range_label, pct


def _r(v: float) -> str:
    return f"{v:.2f}"


def snapshot_tables(s: Snapshot) -> List[tuple]:
    """(title, header, rows) for every section of the view."""
    cur, prev = s.summary, s.prev_summary
    gp, pgp = cur.gross_profit, prev.gross_profit

    def kpi(name: str, a, b) -> list:
        if a is None:
            return [name, "", "" if b is None else _r(b), "cost prices missing"]
        return [name, _r(a), "" if b is None else _r(b), delta(a, b or 0).text]

    tables = [
        ("Summary", ["Metric", "This period", "Previous period", "Change"], [
            kpi("Revenue (incl. GST)", cur.revenue, prev.revenue),
            kpi("Gross profit", gp, pgp),
            ["Gross margin", pct(cur.gross_margin), pct(prev.gross_margin), ""],
            kpi("Bills", cur.bills, prev.bills),
            kpi("Avg bill value", cur.avg_bill, prev.avg_bill),
            kpi("Units sold", cur.units, prev.units),
            kpi("Items per bill", cur.items_per_bill, prev.items_per_bill),
        ]),
        (f"Revenue by {s.bucket}", ["Period", "Revenue", "Previous period"],
         [[lab, _r(v), _r(p)] for lab, v, p in zip(s.long_labels, s.revenue_series, s.prev_revenue_series)]),
        ("Top products", ["Rank", "Product", "Category", "Units", "Sales", "Share", "Change"],
         [[t.rank, t.name, t.category, t.units, _r(t.sales), pct(t.share), t.trend.text] for t in s.top_products]),
        ("Sales by category", ["Category", "Sales", "Units", "Share"],
         [[c.category, _r(c.sales), c.units, pct(c.share)] for c in s.categories]),
        ("Margin by category", ["Category", "Net sales", "Gross profit", "Margin"],
         [[m.name, _r(m.sales), _r(m.profit), pct(m.margin)] for m in s.margin_by_category]),
        ("Margin by product", ["Product", "Net sales", "Gross profit", "Margin"],
         [[m.name, _r(m.sales), _r(m.profit), pct(m.margin)] for m in s.margin_by_product]),
        ("Restock suggestions (as of today)",
         ["Product", "Category", "In stock", "Sold / day", "Days of cover", "Suggested reorder", "Status"],
         [[r.name, r.category, r.stock, f"{r.avg_daily:.2f}",
           "" if r.days_cover is None else f"{r.days_cover:.0f}", r.reorder_qty, r.status]
          for r in s.inventory.attention]),
        ("Slow movers (no sales in 30 days)", ["Product", "Category", "In stock", "Stock value", "Last sold"],
         [[m.name, m.category, m.stock, _r(m.value), m.last_sold.isoformat() if m.last_sold else "Never"]
          for m in s.slow_movers]),
    ]
    if s.payments:
        tables.append(("Payment methods", ["Method", "Amount", "Transactions"],
                       [[m, _r(a), n] for m, a, n in s.payments]))
    return tables


def write_csv(s: Snapshot, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["VendorVault analytics", date_range_label(s.period.start, s.period.end)])
        w.writerow(["Compared with", date_range_label(s.previous.start, s.previous.end)])
        w.writerow(["Generated", s.generated_at.strftime("%Y-%m-%d %H:%M")])
        for title, header, rows in snapshot_tables(s):
            w.writerow([])
            w.writerow([title])
            w.writerow(header)
            w.writerows(rows)


def write_pdf(s: Snapshot, path: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title="VendorVault analytics")
    story: list = [
        Paragraph("VendorVault analytics", styles["Title"]),
        Paragraph(f"{date_range_label(s.period.start, s.period.end)} · compared with "
                  f"{date_range_label(s.previous.start, s.previous.end)} · generated "
                  f"{s.generated_at.strftime('%d %b %Y %H:%M')}", styles["Normal"]),
        Spacer(1, 6 * mm),
    ]
    for title, header, rows in snapshot_tables(s):
        if not rows or title.startswith("Revenue by"):
            continue
        story.append(Paragraph(title, styles["Heading3"]))
        data: Sequence = [header] + [[str(c) for c in r] for r in rows]
        t = Table(data, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5B616B")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#7C6CF6")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F8")]),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story += [t, Spacer(1, 5 * mm)]
    doc.build(story)
