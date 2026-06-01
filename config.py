"""
Single source of truth for the SERP domain-classification taxonomy.

Every layer (LLM validation, xlsx export, web UI, intelligence PDFs) derives its
category list, display labels and colours from CATEGORIES below. To add or change
a category, edit this list only.

`key`        internal token — CSS-safe (no spaces), stored in run JSON, used in
             CSS class names (cat-<key>). Never change an existing key without a
             data migration.
`label`      human-facing display label (Raul's exact wording for the xlsx legend).
`definition` legend "meaning" text.
`fill`       background colour (6-hex, no '#') for xlsx cells and UI pills.
`font`       text colour (6-hex) used on top of `fill`.
`bold`       whether xlsx cells render bold.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    definition: str
    fill: str
    font: str
    bold: bool


# Order here drives the xlsx legend, summary block and doughnut chart.
CATEGORIES: list[Category] = [
    Category("SUBDOMAIN", "SUBDOMAIN & TLD ABUSE",
             "Pseudo-TLD or keyword-stuffed subdomain spam (.co.com, .it.com, best.X, etc.)",
             "F4CCCC", "660000", False),
    Category("FLIPPED", "FLIPPED",
             "Domain that was flipped into casino related",
             "FCE49B", "660000", False),
    Category("EMD", "EXACT MATCH DOMAIN (EMD)",
             "Keyword-stuffed purpose-built domain - AUS impersonation",
             "7030A0", "FFFFFF", True),
    Category("HACKED", "HACKED",
             "Legitimate unrelated domain compromised to host casino content",
             "C00000", "FFFFFF", True),
    Category("PARASITE", "PARASITE",
             "Affiliate iGaming section latched onto a news/general site",
             "F6B26B", "5B2A00", False),
    Category("UGC", "UGC",
             "User-generated content - Reddit, Trustpilot, Quora, forums, YouTube",
             "B4C7E7", "1F3864", False),
    Category("PUBLISHER", "PUBLISHER",
             "Legitimate gambling industry site, operator, or marketplace",
             "C6E0B4", "375623", False),
    Category("OPERATOR", "OPERATORS",
             "Casino Operators",
             "D8D8D8", "000000", False),
    Category("GOV", "GOV",
             "Government, regulator, or government-funded help service",
             "548235", "FFFFFF", True),
    Category("APP", "APP",
             "App store",
             "0070C0", "FFFFFF", True),
    Category("FAKE_CASINO", "Fake Casino",
             "Site pretending to be a casino operator",
             "3B3B3B", "FFFFFF", True),
]

# ── Derived lookups (do not edit) ───────────────────────────────────────────────

CATEGORY_KEYS: list[str] = [c.key for c in CATEGORIES]
VALID_CATEGORIES: set[str] = {c.key for c in CATEGORIES}
BY_KEY: dict[str, Category] = {c.key: c for c in CATEGORIES}
CATEGORY_LABELS: dict[str, str] = {c.key: c.label for c in CATEGORIES}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    """'F4CCCC' -> (244, 204, 204)."""
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def label_for(key: str) -> str:
    """Display label for a category key, falling back to the key itself."""
    return CATEGORY_LABELS.get(key, key)
