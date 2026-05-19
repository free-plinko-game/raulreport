"""Build a classified-SERP .xlsx matching the boss's template."""
from __future__ import annotations

from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import DoughnutChart, Reference
from openpyxl.chart.marker import DataPoint
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Body fills (per spec §7 — what cells in the data grid look like)
BODY_FILL = {
    "SUBDOMAIN": ("F4CCCC", "660000", False),  # bg, font, bold
    "HACKED":    ("C00000", "FFFFFF", True),
    "PARASITE":  ("F6B26B", "5B2A00", False),
    "UGC":       ("B4C7E7", "1F3864", False),
    "PUBLISHER": ("C6E0B4", "375623", False),
    "OPERATOR":  ("1F3864", "FFFFFF", True),
    "GOV":       ("548235", "FFFFFF", True),
    "APP":       ("0070C0", "FFFFFF", True),
}

LEGEND_ROWS = [
    ("SUBDOMAIN", "Pseudo-TLD or keyword-stuffed subdomain spam (.co.com, .it.com, best.X, etc.)"),
    ("HACKED",    "Legitimate unrelated domain compromised to host casino content"),
    ("PARASITE",  "Affiliate iGaming section latched onto a news/general site"),
    ("UGC",       "User-generated content – Reddit, Trustpilot, Quora, forums, YouTube"),
    ("PUBLISHER", "Legitimate gambling industry site, operator, or marketplace"),
    ("GOV",       "Government, regulator, or government-funded help service"),
    ("OPERATORS", "Casino Operators"),
    ("APP",       "App store"),
]

# Summary block uses the singular label "OPERATOR" with grey, per existing template
SUMMARY_ROWS = ["SUBDOMAIN", "HACKED", "PARASITE", "UGC", "PUBLISHER", "OPERATOR", "GOV", "APP"]

HEADER_NAVY = "1F3864"
HEADER_GREY = "D8D8D8"


def _fill(rgb: str) -> PatternFill:
    return PatternFill(fill_type="solid", fgColor=rgb)


def _category_style(cell, category: str) -> None:
    if category not in BODY_FILL:
        return
    bg, fg, bold = BODY_FILL[category]
    cell.fill = _fill(bg)
    cell.font = Font(color=fg, bold=bold)


def _format_date(run_date: str) -> str:
    try:
        dt = datetime.strptime(run_date, "%Y-%m-%d")
    except ValueError:
        return run_date
    # "Date: May 18, 2026" — strip leading zero on day for non-Windows portability
    return f"Date: {dt.strftime('%B')} {dt.day}, {dt.year}"


def build_workbook(run: dict) -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.title = "rankings"

    # Row 2: date
    c = ws.cell(row=2, column=1, value=_format_date(run["run_date"]))
    c.font = Font(bold=True)

    # Row 3: VPN line
    c = ws.cell(row=3, column=1, value="VPN mobile")
    c.font = Font(bold=True)

    # Row 5: Legend header
    h1 = ws.cell(row=5, column=1, value="Label")
    h2 = ws.cell(row=5, column=2, value="Meaning")
    for cell in (h1, h2):
        cell.fill = _fill(HEADER_NAVY)
        cell.font = Font(color="FFFFFF", bold=True)

    # Rows 6..13: legend body
    for i, (label, meaning) in enumerate(LEGEND_ROWS):
        r = 6 + i
        label_cell = ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=meaning)
        cat_key = "OPERATOR" if label == "OPERATORS" else label
        _category_style(label_cell, cat_key)

    # Row 15: column headers (Keyword + 1..10)
    hdr = ws.cell(row=15, column=1, value="Keyword")
    hdr.fill = _fill(HEADER_NAVY)
    hdr.font = Font(color="FFFFFF", bold=True)
    for i in range(10):
        c = ws.cell(row=15, column=2 + i, value=i + 1)
        c.fill = _fill(HEADER_NAVY)
        c.font = Font(color="FFFFFF", bold=True)
        c.alignment = Alignment(horizontal="center")

    # Rows 16..41: 26 keyword rows
    counts = {k: 0 for k in SUMMARY_ROWS}
    for row_idx, kw in enumerate(run["keywords"]):
        r = 16 + row_idx
        ws.cell(row=r, column=1, value=kw["keyword"])
        positions_by_rank = {p["rank"]: p for p in kw.get("positions", [])}
        for rank in range(1, 11):
            p = positions_by_rank.get(rank)
            cell = ws.cell(row=r, column=1 + rank)
            if not p:
                continue
            cell.value = p.get("short_label") or p.get("domain", "")
            cat = p.get("category", "")
            _category_style(cell, cat)
            if cat in counts:
                counts[cat] += 1

    # Row 45: summary header
    for i, val in enumerate(["Category", "MARKET SHARE %", "Count"]):
        c = ws.cell(row=45, column=1 + i, value=val)
        c.fill = _fill(HEADER_GREY)
        c.font = Font(bold=True)

    # Rows 46..53: per-category counts
    for i, cat in enumerate(SUMMARY_ROWS):
        r = 46 + i
        label = ws.cell(row=r, column=1, value=cat)
        # match template: summary cell uses grey for OPERATOR, body fill for others
        if cat == "OPERATOR":
            label.fill = _fill(HEADER_GREY)
        else:
            _category_style(label, cat)
        ws.cell(row=r, column=2, value=f"=C{r}/C54").number_format = "0.00%"
        ws.cell(row=r, column=3, value=counts[cat])

    # Row 54: TOTAL
    total_label = ws.cell(row=54, column=1, value="TOTAL")
    total_label.font = Font(bold=True)
    bsum = ws.cell(row=54, column=2, value="=SUM(B46:B53)")
    bsum.font = Font(bold=True)
    bsum.number_format = "0.00%"
    csum = ws.cell(row=54, column=3, value="=SUM(C46:C53)")
    csum.font = Font(bold=True)

    # Column widths — roughly match template's main columns
    widths = {1: 44.0, 2: 22.0, 3: 22.0, 4: 22.0, 5: 22.0, 6: 22.0,
              7: 22.0, 8: 22.0, 9: 22.0, 10: 22.0, 11: 22.0}
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    # Doughnut chart of category market share, anchored to the right of the
    # summary block (template uses D45). Slice colours match the §7 palette so
    # the chart reads against the colour key.
    chart = DoughnutChart()
    chart.holeSize = 50
    data_ref = Reference(ws, min_col=2, min_row=46, max_row=53)
    cats_ref = Reference(ws, min_col=1, min_row=46, max_row=53)
    chart.add_data(data_ref, titles_from_data=False)
    chart.set_categories(cats_ref)
    series = chart.series[0]
    series.dPt = []
    for i, cat in enumerate(SUMMARY_ROWS):
        bg = BODY_FILL[cat][0]
        gp = GraphicalProperties(solidFill=bg)
        gp.line = None
        series.dPt.append(DataPoint(idx=i, spPr=gp))
    chart.width = 15
    chart.height = 7.5
    ws.add_chart(chart, "D45")

    # Match template print setup
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE

    return wb
