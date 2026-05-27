"""Run Intelligence PDF report builder using fpdf2."""
from __future__ import annotations

from fpdf import FPDF

NAVY        = (31, 56, 100)
RED         = (192, 0, 0)
ORANGE      = (246, 178, 107)
GREEN       = (84, 130, 53)
BLUE        = (0, 112, 192)
PURPLE      = (120, 80, 160)
TEAL        = (0, 140, 130)
AMBER       = (180, 120, 0)
LIGHT_GREY  = (240, 240, 243)
MID_GREY    = (160, 160, 165)
DARK_GREY   = (100, 100, 105)
WHITE       = (255, 255, 255)
BLACK       = (34, 34, 34)

CAT_COLOURS = {
    "OPERATOR":  NAVY,
    "PUBLISHER": BLUE,
    "SUBDOMAIN": TEAL,
    "PARASITE":  ORANGE,
    "HACKED":    RED,
    "UGC":       PURPLE,
    "GOV":       GREEN,
    "APP":       AMBER,
    "UNKNOWN":   MID_GREY,
    "OTHER":     MID_GREY,
}

_UNICODE_REPLACEMENTS = str.maketrans({
    "—": "-",  # em dash
    "–": "-",  # en dash
    "‘": "'",  "’": "'",
    "“": '"',  "”": '"',
    "•": "-",  "…": "...",
    "\xe9": "e", "\xf3": "o", "\xed": "i", "\xfa": "u",
    "\xe1": "a", "\xe0": "a", "\xe8": "e", "\xf2": "o",
})

MARGIN      = 20
PAGE_H      = 297
CONTENT_W   = 170   # 210 - 2*20
SAFE_BOTTOM = 265   # trigger page break


def _safe(text: str) -> str:
    if not text:
        return ""
    return str(text).translate(_UNICODE_REPLACEMENTS).encode("latin-1", errors="replace").decode("latin-1")


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3].rsplit(" ", 1)[0] + "..."


class IntelReport(FPDF):
    def __init__(self, run_date: str):
        super().__init__()
        self.run_date = run_date
        self.set_auto_page_break(auto=True, margin=MARGIN)
        self.set_margins(MARGIN, MARGIN, MARGIN)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MID_GREY)
        self.cell(CONTENT_W / 2, 7, _safe(f"Run Intelligence  |  {self.run_date}"), align="L")
        self.cell(CONTENT_W / 2, 7, _safe(f"Page {self.page_no()}"), align="R")
        self.set_text_color(*BLACK)
        self.ln(2)
        self.set_draw_color(*LIGHT_GREY)
        self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        self.ln(5)

    def footer(self):
        pass  # page numbers are in header for non-cover pages

    # ── Design primitives ────────────────────────────────────────────────────

    def _rule(self, colour: tuple = LIGHT_GREY):
        self.set_draw_color(*colour)
        self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())

    def _section_title(self, number: str, title: str):
        """Left-accent style section header — lighter than a full navy bar."""
        self.ln(6)
        y = self.get_y()
        # Navy accent bar on left
        self.set_fill_color(*NAVY)
        self.rect(MARGIN, y, 3, 10, "F")
        # Section number (small, grey)
        self.set_xy(MARGIN + 6, y)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MID_GREY)
        self.cell(20, 5, _safe(number))
        # Title (bold, navy)
        self.set_xy(MARGIN + 6, y + 4)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*NAVY)
        self.cell(CONTENT_W - 6, 7, _safe(title))
        self.set_y(y + 12)
        self.set_draw_color(*LIGHT_GREY)
        self.line(MARGIN, self.get_y(), 210 - MARGIN, self.get_y())
        self.ln(5)
        self.set_text_color(*BLACK)

    def _sub_heading(self, text: str):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.cell(0, 6, _safe(text), ln=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def _caption(self, text: str):
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*DARK_GREY)
        self.cell(0, 4, _safe(text), ln=True)
        self.set_text_color(*BLACK)
        self.ln(2)

    def _cover_stat(self, x: float, y: float, w: float, h: float,
                    value: str, label: str, colour: tuple = NAVY):
        self.set_fill_color(*LIGHT_GREY)
        self.rect(x, y, w, h, "F")
        # Accent line at top of box
        self.set_fill_color(*colour)
        self.rect(x, y, w, 2, "F")
        self.set_xy(x, y + 10)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(*colour)
        self.cell(w, 12, _safe(value), align="C")
        self.set_xy(x, y + h - 10)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*DARK_GREY)
        self.cell(w, 7, _safe(label), align="C")
        self.set_text_color(*BLACK)

    def _feature_box(self, x: float, y: float, w: float, h: float,
                     value: str, label: str):
        self.set_fill_color(*LIGHT_GREY)
        self.rect(x, y, w, h, "F")
        self.set_xy(x, y + 3)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*NAVY)
        self.cell(w, 9, _safe(value), align="C")
        self.set_xy(x, y + 13)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*DARK_GREY)
        self.cell(w, 5, _safe(label), align="C")
        self.set_text_color(*BLACK)

    def _th_row(self, col_widths: list[float], headers: list[str], row_h: int = 6):
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 7)
        for w, h in zip(col_widths, headers):
            self.cell(w, row_h, _safe(h), fill=True, align="C")
        self.ln()
        self.set_text_color(*BLACK)

    def _cat_cell(self, cat: str, width: float, row_h: float = 5, fill: bool = False):
        colour = CAT_COLOURS.get(cat, MID_GREY)
        self.set_text_color(*colour)
        self.set_font("Helvetica", "B", 7)
        self.cell(width, row_h, _safe(cat), fill=fill)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*BLACK)

    def _ensure_space(self, needed_mm: float):
        """Add a page if less than needed_mm remain."""
        if self.get_y() > PAGE_H - MARGIN - needed_mm:
            self.add_page()


# ── Public builder ─────────────────────────────────────────────────────────────

def build_intelligence_report(
    run: dict,
    landscape: dict,
    snippet: dict,
    ovi: dict,
) -> bytes:
    run_date    = run.get("run_date", "")
    keywords    = run.get("keywords", [])
    paa_data    = run.get("paa_clusters") or {}
    clusters    = paa_data.get("clusters", [])
    total_q     = paa_data.get("total_questions", 0)
    total_uq    = paa_data.get("total_unique_questions", 0)

    fc           = landscape.get("feature_counts", {})
    snippet_cnt  = landscape.get("keywords_with_featured_snippet", 0)
    scd          = landscape.get("snippet_category_breakdown", {})
    domain_count = len(ovi.get("domains", []))
    total_kw_ovi = ovi.get("total_keywords", 0)

    pdf = IntelReport(run_date)
    pdf.add_page()

    # ── COVER ──────────────────────────────────────────────────────────────────
    # Vertically: title cluster at ~y=55, stat boxes at y=100, contents at y=180
    pdf.set_y(50)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 16, "Run Intelligence Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*DARK_GREY)
    pdf.cell(0, 7, _safe(f"Australian Online Casino Keywords  |  {run_date}"), ln=True, align="C")
    pdf.ln(8)
    pdf._rule(MID_GREY)
    pdf.ln(14)

    # 4 stat boxes — larger and better proportioned
    box_w, gap, box_h = 38, 5, 40
    start_x = (210 - (4 * box_w + 3 * gap)) / 2
    box_y = pdf.get_y()
    for i, (val, label, col) in enumerate([
        (str(len(keywords)),            "Keywords",          NAVY),
        (str(snippet_cnt),              "Featured Snippets", NAVY),
        (str(fc.get("has_paa", 0)),     "PAA Boxes",         NAVY),
        (str(domain_count),             "Domains Tracked",   NAVY),
    ]):
        pdf._cover_stat(start_x + i * (box_w + gap), box_y, box_w, box_h, val, label, col)
    pdf.set_y(box_y + box_h + 14)
    pdf._rule(LIGHT_GREY)
    pdf.ln(14)

    # Brief description
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*DARK_GREY)
    pdf.multi_cell(CONTENT_W, 5.5,
        _safe("This report analyses SERP features, snippet language patterns, operator visibility, "
              "and People Also Ask intent clusters across the full set of Australian online casino keywords. "
              "Each section is derived from raw SERP data — no projections or estimates."),
        align="C")
    pdf.ln(12)

    # Contents — styled list
    pdf._rule(LIGHT_GREY)
    pdf.ln(10)
    contents = [
        ("1", "SERP Landscape",           "Featured snippets, SERP feature flags, keyword detail"),
        ("2", "Snippet Language Analysis","Bonus density, compliance language, CTA patterns"),
        ("3", "Operator Visibility Index","Domain rankings by keyword breadth and position"),
        ("4", "People Also Ask",          "Thematic question clusters from PAA boxes"),
    ]
    left_x = (210 - 130) / 2
    for num, title, desc in contents:
        pdf.set_x(left_x)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.cell(8, 6, _safe(num + "."))
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(40, 6, _safe(title))
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(82, 6, _safe(desc), ln=True)
    pdf.set_text_color(*BLACK)

    # ── SECTION 1: SERP LANDSCAPE ──────────────────────────────────────────────
    pdf.add_page()
    pdf._section_title("Section 1", "SERP Landscape")

    # 6 feature boxes, 3 per row, slightly taller
    items = [
        ("Featured Snippets",  snippet_cnt),
        ("PAA Boxes",          fc.get("has_paa", 0)),
        ("News Boxes",         fc.get("has_news_box", 0)),
        ("Video Carousels",    fc.get("has_video_carousel", 0)),
        ("Knowledge Panels",   fc.get("has_knowledge_panel", 0)),
        ("Shopping",           fc.get("has_shopping", 0)),
    ]
    cw, ch, cg = 54, 26, 4
    row_start_y = pdf.get_y()
    for i, (label, val) in enumerate(items):
        col = i % 3
        if col == 0 and i > 0:
            row_start_y += ch + cg
        cx = MARGIN + col * (cw + cg)
        pdf._feature_box(cx, row_start_y, cw, ch, str(val), label)
    pdf.set_y(row_start_y + ch + cg + 8)
    pdf.set_text_color(*BLACK)

    # Snippet ownership bars
    if scd and snippet_cnt:
        pdf._sub_heading("Featured Snippet Ownership by Category")
        bar_w = 100.0
        label_w = 26
        for cat, count in sorted(scd.items(), key=lambda x: -x[1]):
            pct = round(count / snippet_cnt * 100)
            colour = CAT_COLOURS.get(cat, MID_GREY)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*colour)
            pdf.cell(label_w, 5.5, _safe(cat))
            bx, by = pdf.get_x(), pdf.get_y() + 1
            pdf.set_fill_color(*LIGHT_GREY)
            pdf.rect(bx, by, bar_w, 3.5, "F")
            pdf.set_fill_color(*colour)
            pdf.rect(bx, by, bar_w * pct / 100, 3.5, "F")
            pdf.set_x(bx + bar_w + 4)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*DARK_GREY)
            pdf.cell(40, 5.5, _safe(f"{count} / {snippet_cnt}  ({pct}%)"), ln=True)
        pdf.set_text_color(*BLACK)
        pdf.ln(5)

    # Keyword detail table
    pdf._sub_heading("Keyword Detail")

    col_w = [52, 34, 14, 14, 14, 14, 18]
    # Check if there's enough room for the header + a few rows; if not, start fresh page
    pdf._ensure_space(14 + 5 * 5)
    pdf._th_row(col_w, ["Keyword", "Snippet Domain", "PAA", "News", "Video", "KP", "Features"])

    for i, kw in enumerate(keywords):
        pdf._ensure_space(10)
        sf = kw.get("serp_features") or {}
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*BLACK)
        pdf.cell(col_w[0], 5, _safe(_truncate(kw.get("keyword", ""), 32)), fill=fill)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(col_w[1], 5, _safe(_truncate(sf.get("featured_snippet_domain") or "-", 22)), fill=fill)
        for flag, cw_f in zip(
            ["has_paa", "has_news_box", "has_video_carousel", "has_knowledge_panel"], col_w[2:6]
        ):
            if sf.get(flag):
                pdf.set_text_color(*GREEN)
                pdf.set_font("Helvetica", "B", 7)
                pdf.cell(cw_f, 5, "Y", align="C", fill=fill)
                pdf.set_font("Helvetica", "", 7)
            else:
                pdf.set_text_color(*MID_GREY)
                pdf.cell(cw_f, 5, "-", align="C", fill=fill)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(col_w[6], 5, str(sf.get("serp_feature_count", 0)), align="C", fill=fill)
        pdf.ln()
    pdf.set_text_color(*BLACK)

    # ── SECTION 2: SNIPPET LANGUAGE ────────────────────────────────────────────
    pdf._ensure_space(60)
    pdf._section_title("Section 2", "Snippet Language Analysis")

    # Bonus heat
    bonus_heat = [b for b in snippet.get("bonus_heat", []) if b.get("bonus_count", 0) > 0]
    pdf._sub_heading("Bonus Copy Density")
    pdf._caption("Results mentioning bonuses, deposit matches or free spins (out of 10)")

    if bonus_heat:
        bar_w = 80.0
        for item in bonus_heat[:15]:
            kw_label = _truncate(item.get("keyword", ""), 36)
            count = item.get("bonus_count", 0)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*BLACK)
            pdf.cell(64, 5, _safe(kw_label))
            bx, by = pdf.get_x(), pdf.get_y() + 1
            pdf.set_fill_color(*LIGHT_GREY)
            pdf.rect(bx, by, bar_w, 3.5, "F")
            pdf.set_fill_color(*ORANGE)
            pdf.rect(bx, by, bar_w * count / 10, 3.5, "F")
            pdf.set_x(bx + bar_w + 4)
            pdf.set_text_color(*DARK_GREY)
            pdf.cell(18, 5, f"{count}/10", ln=True)
        amounts = snippet.get("all_bonus_amounts", [])
        if amounts:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*DARK_GREY)
            pdf.cell(0, 5, _safe("Amounts seen: " + ", ".join(str(a) for a in amounts)), ln=True)
    else:
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 5, "No bonus language detected.", ln=True)
    pdf.set_text_color(*BLACK)
    pdf.ln(6)

    # Compliance buckets
    pdf._ensure_space(46)
    pdf._sub_heading("Compliance Language Distribution")
    pdf._caption("Results mentioning AU licensing, ACMA or responsible gambling")

    cd = snippet.get("compliance_distribution", {})
    bw, bh, bg = 52, 30, 5
    bstart = (210 - (3 * bw + 2 * bg)) / 2
    by = pdf.get_y()
    for i, (val, label, colour) in enumerate([
        (cd.get("zero", 0),        "0 mentions",    RED),
        (cd.get("low_1_3", 0),     "1-3 mentions",  ORANGE),
        (cd.get("high_4_plus", 0), "4+ mentions",   GREEN),
    ]):
        bx = bstart + i * (bw + bg)
        pdf.set_fill_color(*LIGHT_GREY)
        pdf.rect(bx, by, bw, bh, "F")
        # Top accent
        colour_list = list(colour)
        pdf.set_fill_color(*colour)
        pdf.rect(bx, by, bw, 2, "F")
        pdf.set_xy(bx, by + 5)
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(*colour)
        pdf.cell(bw, 11, str(val), align="C")
        pdf.set_xy(bx, by + 17)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(bw, 5, _safe(label), align="C")
        pdf.set_xy(bx, by + 22)
        pdf.cell(bw, 4, "keywords", align="C")
    pdf.set_y(by + bh + 6)
    pdf.set_text_color(*BLACK)

    cta_types = snippet.get("all_cta_types", [])
    if cta_types:
        pdf.ln(2)
        pdf._sub_heading("CTA Patterns")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 5, _safe(", ".join(cta_types)), ln=True)
        pdf.set_text_color(*BLACK)

    years = snippet.get("freshness_years", [])
    if years:
        pdf.ln(3)
        pdf._sub_heading("Freshness Years Cited")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 5, _safe(", ".join(str(y) for y in years)), ln=True)
        pdf.set_text_color(*BLACK)

    # ── SECTION 3: OPERATOR VISIBILITY INDEX ───────────────────────────────────
    pdf._ensure_space(60)
    pdf._section_title("Section 3", "Operator Visibility Index")
    pdf._caption(f"Domains ranked by keyword breadth across all {total_kw_ovi} keywords")

    col_w = [8, 52, 26, 24, 24, 18, 18]

    # Check space before header + minimum 6 rows
    pdf._ensure_space(6 + 6 * 5)
    pdf._th_row(col_w, ["#", "Domain", "Category", "Keywords", "Appearances", "Avg Pos", "Best"])

    for i, d in enumerate(ovi.get("domains", [])):
        pdf._ensure_space(10)
        fill = i % 2 == 0
        pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(col_w[0], 4.5, str(i + 1), align="C", fill=fill)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*BLACK)
        pdf.cell(col_w[1], 4.5, _safe(_truncate(d.get("domain", ""), 32)), fill=fill)
        pdf._cat_cell(d.get("category", "OTHER"), col_w[2], 4.5, fill)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(col_w[3], 4.5, f"{d.get('keyword_count', 0)} / {total_kw_ovi}", align="C", fill=fill)
        pdf.cell(col_w[4], 4.5, str(d.get("total_appearances", 0)), align="C", fill=fill)
        pdf.cell(col_w[5], 4.5, str(d.get("avg_position", 0)), align="C", fill=fill)
        pdf.cell(col_w[6], 4.5, str(d.get("best_position", 0)), align="C", fill=fill)
        pdf.ln()
    pdf.set_text_color(*BLACK)

    # ── SECTION 4: PEOPLE ALSO ASK ─────────────────────────────────────────────
    pdf._ensure_space(60)
    pdf._section_title("Section 4", "People Also Ask")

    if not clusters:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 6, "No PAA questions detected across this run.", ln=True)
    else:
        pdf._caption(f"{total_uq} unique questions  -  {total_q} total appearances")
        pdf.ln(2)

        col_w_paa = [105, 65]
        for cluster in clusters:
            n_rows = len(cluster.get("questions", []))
            # Need space for: cluster header (8) + table header (6) + rows (4.5 each) + gap (5)
            pdf._ensure_space(14 + min(n_rows, 4) * 4.5)

            theme = cluster.get("theme", "")
            q_count = cluster.get("question_count", 0)
            # Cluster header — light grey fill, navy left accent
            y_clust = pdf.get_y()
            pdf.set_fill_color(*LIGHT_GREY)
            pdf.cell(CONTENT_W, 7, "", fill=True, ln=False)
            pdf.set_x(MARGIN)
            pdf.set_fill_color(*NAVY)
            pdf.rect(MARGIN, y_clust, 3, 7, "F")
            pdf.set_xy(MARGIN + 6, y_clust)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*NAVY)
            pdf.cell(CONTENT_W - 6 - 20, 7, _safe(theme))
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*MID_GREY)
            pdf.cell(20, 7, _safe(f"{q_count} questions"), align="R", ln=True)
            pdf.ln(1)

            pdf._th_row(col_w_paa, ["Question", "Keywords"])

            for j, item in enumerate(cluster.get("questions", [])):
                pdf._ensure_space(9)
                fill = j % 2 == 0
                pdf.set_fill_color(*LIGHT_GREY if fill else WHITE)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*BLACK)
                pdf.cell(col_w_paa[0], 4.5, _safe(_truncate(item.get("question", ""), 72)), fill=fill)
                pdf.set_text_color(*DARK_GREY)
                kw_str = ", ".join(item.get("keywords", []))
                pdf.cell(col_w_paa[1], 4.5, _safe(_truncate(kw_str, 50)), fill=fill, ln=True)
            pdf.ln(5)

    pdf.set_text_color(*BLACK)
    return bytes(pdf.output())
