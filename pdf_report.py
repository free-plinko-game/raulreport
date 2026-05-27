"""Ads Intelligence PDF report builder using fpdf2."""
from __future__ import annotations

from fpdf import FPDF

# Colour palette
NAVY = (31, 56, 100)
RED = (192, 0, 0)
ORANGE = (246, 178, 107)
GREEN = (84, 130, 53)
BLUE = (0, 112, 192)
LIGHT_GREY = (240, 240, 243)
MID_GREY = (160, 160, 165)
DARK_GREY = (100, 100, 105)
WHITE = (255, 255, 255)
BLACK = (34, 34, 34)

AD_TYPE_COLOURS = {
    "LICENSED_OPERATOR": GREEN,
    "OFFSHORE_OPERATOR":  RED,
    "AFFILIATE":          ORANGE,
    "CRYPTO_CASINO":      BLUE,
    "APP":                (0, 112, 192),
    "OTHER":              MID_GREY,
}

AD_TYPE_LABELS = {
    "LICENSED_OPERATOR": "Licensed Operator",
    "OFFSHORE_OPERATOR":  "Offshore Operator",
    "AFFILIATE":          "Affiliate",
    "CRYPTO_CASINO":      "Crypto Casino",
    "APP":                "App",
    "OTHER":              "Other",
}

# Characters that fail latin-1 encoding — replace before encoding
_UNICODE_REPLACEMENTS = str.maketrans({
    "—": "-",   # em dash
    "–": "-",   # en dash
    "’": "'",   # right single quote
    "‘": "'",   # left single quote
    "“": '"',   # left double quote
    "”": '"',   # right double quote
    "•": "-",   # bullet
    "…": "...", # ellipsis
    "é": "e",   # e acute (for Spanish etc.)
    "ó": "o",
    "í": "i",
    "ú": "u",
    "á": "a",
    "à": "a",
    "è": "e",
    "ò": "o",
})


def _safe(text: str) -> str:
    """Sanitise text for latin-1 core fpdf fonts."""
    if not text:
        return ""
    return text.translate(_UNICODE_REPLACEMENTS).encode("latin-1", errors="replace").decode("latin-1")


def _truncate(text: str, max_chars: int) -> str:
    """Truncate at a word boundary."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars - 3].rsplit(" ", 1)[0]
    return cut + "..."


class Report(FPDF):
    def __init__(self, run_date: str):
        super().__init__()
        self.run_date = run_date
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MID_GREY)
        self.cell(0, 8, _safe(f"Ads Intelligence Report  |  {self.run_date}"), align="L")
        self.set_text_color(*BLACK)
        self.ln(3)
        self.set_draw_color(*LIGHT_GREY)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MID_GREY)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")
        self.set_text_color(*BLACK)

    def _section_title(self, title: str):
        self.ln(4)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 9, _safe(f"  {title}"), fill=True, ln=True)
        self.set_text_color(*BLACK)
        self.ln(4)

    def _body(self, text: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5.5, _safe(text))
        self.ln(2)

    def _stat_box(self, x: float, y: float, w: float, h: float,
                  value: str, label: str, value_colour: tuple):
        self.set_fill_color(*LIGHT_GREY)
        self.rect(x, y, w, h, "F")
        # Value
        self.set_xy(x, y + 7)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*value_colour)
        self.cell(w, 10, _safe(value), align="C", ln=False)
        # Label
        self.set_xy(x, y + h - 10)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*DARK_GREY)
        self.cell(w, 6, _safe(label), align="C", ln=False)
        self.set_text_color(*BLACK)

    def _bar_legend_item(self, ad_type: str, count: int):
        colour = AD_TYPE_COLOURS.get(ad_type, MID_GREY)
        swatch_x = self.get_x()
        swatch_y = self.get_y() + 1
        self.set_fill_color(*colour)
        self.rect(swatch_x, swatch_y, 10, 6, "F")
        self.set_x(swatch_x + 13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        label = AD_TYPE_LABELS.get(ad_type, ad_type)
        self.cell(58, 8, _safe(f"{label}: {count}"), ln=False)


# ---- Public builder --------------------------------------------------------

def build_report(run: dict, analysis: dict) -> bytes:
    """Build and return PDF bytes from run data + LLM analysis."""
    run_date = run.get("run_date", "")
    keywords = run.get("keywords", [])

    total_ads = sum(len(k.get("ads", [])) for k in keywords)
    total_offshore = sum(
        sum(1 for a in k.get("ads", []) if a.get("is_offshore")) for k in keywords
    )
    kw_with_ads = sum(1 for k in keywords if k.get("ads"))
    offshore_pct = round(total_offshore / total_ads * 100) if total_ads else 0

    breakdown: dict = analysis.get("ad_type_breakdown", {})
    top_advertisers: list = analysis.get("top_advertisers", [])
    key_findings: list = analysis.get("key_findings", [])
    keyword_highlights: list = analysis.get("keyword_highlights", [])
    classified_ads: list = analysis.get("classified_ads", [])

    pdf = Report(run_date)
    pdf.add_page()

    # ---- COVER ----
    pdf.ln(18)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 14, "Ads Intelligence Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*DARK_GREY)
    pdf.cell(0, 8, _safe(f"Australian Online Casino Keywords  |  {run_date}"), ln=True, align="C")
    pdf.ln(12)

    # Horizontal rule
    pdf.set_draw_color(*MID_GREY)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(12)

    # Stat boxes — 4 across, taller and well-spaced
    box_w = 38
    gap = 5
    total_row_w = 4 * box_w + 3 * gap
    start_x = (210 - total_row_w) / 2
    box_h = 32
    box_y = pdf.get_y()

    stat_configs = [
        ("Total Ads",        str(total_ads),                NAVY),
        ("Keywords w/ Ads",  f"{kw_with_ads} / {len(keywords)}", NAVY),
        ("Offshore Ads",     str(total_offshore),           RED if total_offshore > 0 else NAVY),
        ("Offshore %",       f"{offshore_pct}%",            RED if offshore_pct >= 50 else (ORANGE if offshore_pct >= 25 else NAVY)),
    ]
    for i, (label, val, colour) in enumerate(stat_configs):
        pdf._stat_box(start_x + i * (box_w + gap), box_y, box_w, box_h, val, label, colour)

    pdf.set_y(box_y + box_h + 14)

    # Second rule
    pdf.set_draw_color(*LIGHT_GREY)
    pdf.line(40, pdf.get_y(), 170, pdf.get_y())
    pdf.ln(14)

    # Brief context note
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*DARK_GREY)
    pdf.multi_cell(0, 5.5,
        _safe("This report analyses paid search ads detected across 26 Australian online casino "
              "keywords. Each ad is classified by type and flagged if the advertiser appears to be "
              "an offshore or unlicensed operator targeting Australian users."),
        align="C")
    pdf.ln(12)

    # Contents
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "Contents", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*DARK_GREY)
    contents = [
        "Executive Summary",
        "Offshore Density Analysis",
        "Ad Type Breakdown",
        "Key Findings",
        "Top Advertisers",
        "Keyword Highlights",
        "Full Ads Detail by Keyword",
    ]
    for item in contents:
        pdf.cell(0, 5.5, _safe(f"  {item}"), ln=True, align="C")
    pdf.set_text_color(*BLACK)

    # ---- EXECUTIVE SUMMARY ----
    pdf.add_page()
    pdf._section_title("Executive Summary")
    pdf._body(analysis.get("executive_summary", ""))

    # ---- OFFSHORE DENSITY ----
    pdf._section_title("Offshore Density Analysis")
    pdf._body(analysis.get("offshore_density_analysis", ""))

    # Stacked bar chart
    if total_ads:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, "Composition of all ads this run:", ln=True)
        pdf.ln(2)

        bar_w = 170.0
        bar_h = 10.0
        drawn = 0.0
        bar_y = pdf.get_y()
        for ad_type, count in breakdown.items():
            if not count:
                continue
            seg_w = round(bar_w * count / total_ads, 1)
            colour = AD_TYPE_COLOURS.get(ad_type, MID_GREY)
            pdf.set_fill_color(*colour)
            pdf.rect(20 + drawn, bar_y, seg_w, bar_h, "F")
            drawn += seg_w

        pdf.set_y(bar_y + bar_h + 4)

        # Legend — 2 per row
        items = [(t, c) for t, c in breakdown.items() if c]
        for i, (ad_type, count) in enumerate(items):
            if i % 2 == 0:
                pdf.set_x(20)
            pdf._bar_legend_item(ad_type, count)
            if i % 2 == 1:
                pdf.ln(8)
        if len(items) % 2 == 1:
            pdf.ln(8)
        pdf.ln(4)
        pdf.set_text_color(*BLACK)

    # ---- AD TYPE BREAKDOWN TABLE ----
    pdf._section_title("Ad Type Breakdown")
    col_widths = [90, 30, 50]
    headers = ["Ad Type", "Count", "% of Total"]
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 9)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, _safe(h), border=0, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*BLACK)
    for i, (ad_type, count) in enumerate(breakdown.items()):
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
        pct = f"{round(count / total_ads * 100)}%" if total_ads else "-"
        colour = AD_TYPE_COLOURS.get(ad_type, MID_GREY)
        pdf.set_text_color(*colour)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_widths[0], 6, _safe(f"  {AD_TYPE_LABELS.get(ad_type, ad_type)}"), fill=fill)
        pdf.set_text_color(*BLACK)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(col_widths[1], 6, str(count), align="C", fill=fill)
        pdf.cell(col_widths[2], 6, _safe(pct), align="C", fill=fill)
        pdf.ln()
    pdf.ln(4)

    # ---- KEY FINDINGS ----
    pdf._section_title("Key Findings")
    for finding in key_findings:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*BLACK)
        x = pdf.get_x()
        pdf.cell(6, 5.5, "-", ln=False)
        pdf.multi_cell(0, 5.5, _safe(finding))
        pdf.ln(1)
    pdf.ln(2)

    # ---- TOP ADVERTISERS ----
    pdf._section_title("Top Advertisers")
    col_widths = [48, 38, 16, 68]
    headers = ["Advertiser", "Type", "Kwds", "Notes"]
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 9)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, _safe(h), border=0, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(*BLACK)
    for i, adv in enumerate(top_advertisers[:10]):
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
        ad_type = adv.get("ad_type", "OTHER")
        colour = AD_TYPE_COLOURS.get(ad_type, MID_GREY)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*colour)
        pdf.cell(col_widths[0], 6, _safe(f"  {_truncate(adv.get('advertiser', ''), 22)}"), fill=fill)
        pdf.set_text_color(*BLACK)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(col_widths[1], 6, _safe(AD_TYPE_LABELS.get(ad_type, ad_type)), align="C", fill=fill)
        pdf.cell(col_widths[2], 6, str(adv.get("keyword_count", 0)), align="C", fill=fill)
        pdf.cell(col_widths[3], 6, _safe(_truncate(adv.get("notes", ""), 62)), fill=fill)
        pdf.ln()
    pdf.ln(4)

    # ---- KEYWORD HIGHLIGHTS ----
    if keyword_highlights:
        pdf._section_title("Keyword Highlights")
        for item in keyword_highlights:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*NAVY)
            pdf.cell(0, 5.5, _safe(item.get("keyword", "")), ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*BLACK)
            pdf.multi_cell(0, 5, _safe(item.get("finding", "")))
            pdf.ln(3)

    # ---- PER-KEYWORD DETAIL ----
    pdf.add_page()
    pdf._section_title("Full Ads Detail by Keyword")

    # Group classified_ads by keyword
    by_kw: dict[str, list] = {}
    for ad in classified_ads:
        kw = ad.get("keyword", "Unknown")
        by_kw.setdefault(kw, []).append(ad)

    # Separate keywords into those with ads and those without
    kw_no_ads = [
        k.get("keyword", "") for k in keywords
        if not k.get("ads") and k.get("keyword", "") not in by_kw
    ]

    # Keywords with ads first
    for kw_name, ads in by_kw.items():
        if not ads:
            continue
        if pdf.get_y() > 245:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 6, _safe(kw_name), ln=True)

        col_w = [8, 38, 32, 38, 12, 42]
        col_h = ["#", "Advertiser", "Type", "Landing Page", "Pos", "Notes"]
        pdf.set_fill_color(*LIGHT_GREY)
        pdf.set_text_color(*DARK_GREY)
        pdf.set_font("Helvetica", "B", 7)
        for w, h in zip(col_w, col_h):
            pdf.cell(w, 5, _safe(h), fill=True)
        pdf.ln()

        for j, ad in enumerate(ads):
            fill = j % 2 == 0
            pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
            ad_type = ad.get("ad_type", "OTHER")
            colour = AD_TYPE_COLOURS.get(ad_type, MID_GREY)

            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*BLACK)
            pdf.cell(col_w[0], 5, str(ad.get("position", "")), fill=fill)

            pdf.set_text_color(*colour)
            pdf.set_font("Helvetica", "B", 7)
            pdf.cell(col_w[1], 5, _safe(_truncate(ad.get("advertiser", ""), 24)), fill=fill)

            pdf.set_font("Helvetica", "", 7)
            pdf.cell(col_w[2], 5, _safe(AD_TYPE_LABELS.get(ad_type, ad_type)), fill=fill)

            pdf.set_text_color(*BLACK)
            landing = ad.get("display_url") or ad.get("landing_url", "")
            pdf.cell(col_w[3], 5, _safe(_truncate(landing, 28)), fill=fill)
            pdf.cell(col_w[4], 5, _safe(ad.get("ad_position", "")), align="C", fill=fill)
            pdf.cell(col_w[5], 5, _safe(_truncate(ad.get("notes", ""), 38)), fill=fill)
            pdf.ln()

        pdf.ln(4)
        pdf.set_text_color(*BLACK)

    # No-ads keywords — compact block at the end
    if kw_no_ads:
        if pdf.get_y() > 230:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 6, _safe(f"No ads detected ({len(kw_no_ads)} keywords):"), ln=True)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MID_GREY)
        # Two columns
        col_w = 85
        for i, kw_name in enumerate(kw_no_ads):
            if i % 2 == 0:
                pdf.set_x(20)
            pdf.cell(col_w, 5, _safe(f"  - {kw_name}"), ln=(i % 2 == 1))
        if len(kw_no_ads) % 2 == 1:
            pdf.ln()
        pdf.set_text_color(*BLACK)

    return bytes(pdf.output())
