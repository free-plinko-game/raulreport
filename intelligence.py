"""
Operator Visibility Index and other pure-aggregation intelligence.
No LLM calls — works entirely from stored Phase 1 position data.
"""
from __future__ import annotations

from collections import defaultdict


def operator_visibility_index(keywords: list[dict]) -> dict:
    """
    Aggregate domain appearances across all keyword position lists.

    Returns:
      {
        "domains": [
          {
            "domain": "oddschecker.com",
            "category": "AFFILIATE",
            "keyword_count": 18,
            "total_appearances": 20,   # same domain can appear twice on one kw
            "avg_position": 3.2,
            "best_position": 1,
            "keywords": ["online casino australia", ...]
          },
          ...
        ],
        "categories": ["AFFILIATE", "OPERATOR", ...],   # all seen categories
        "total_keywords": 26,
      }
    """
    # domain -> {category, positions: [(kw, rank)], keywords: set}
    domain_data: dict[str, dict] = defaultdict(lambda: {
        "category": "OTHER",
        "positions": [],
        "keywords": set(),
    })

    total_keywords = len(keywords)

    for kw_obj in keywords:
        kw_name = kw_obj.get("keyword", "")
        for pos in kw_obj.get("positions", []):
            domain = pos.get("domain", "").strip()
            if not domain:
                continue
            category = pos.get("category", "OTHER")
            rank = pos.get("rank", 99)
            d = domain_data[domain]
            d["category"] = category
            d["positions"].append((kw_name, rank))
            d["keywords"].add(kw_name)

    domains = []
    for domain, data in domain_data.items():
        positions = [r for _, r in data["positions"]]
        avg_pos = round(sum(positions) / len(positions), 1) if positions else 0
        best_pos = min(positions) if positions else 0
        domains.append({
            "domain": domain,
            "category": data["category"],
            "keyword_count": len(data["keywords"]),
            "total_appearances": len(data["positions"]),
            "avg_position": avg_pos,
            "best_position": best_pos,
            "keywords": sorted(data["keywords"]),
        })

    # Sort: keyword_count desc, then avg_position asc
    domains.sort(key=lambda d: (-d["keyword_count"], d["avg_position"]))

    categories = sorted({d["category"] for d in domains})

    return {
        "domains": domains,
        "categories": categories,
        "total_keywords": total_keywords,
    }


def serp_landscape_summary(keywords: list[dict]) -> dict:
    """
    Aggregate SERP feature data across all keywords for Section 1 summary stats.

    Returns counts and featured snippet ownership breakdown.
    """
    total = len(keywords)
    features_present = {
        "has_paa": 0,
        "has_news_box": 0,
        "has_video_carousel": 0,
        "has_knowledge_panel": 0,
        "has_shopping": 0,
        "local_pack_present": 0,
    }
    snippet_owners: list[dict] = []  # {domain, keyword, category}

    for kw_obj in keywords:
        sf = kw_obj.get("serp_features") or {}
        for flag in features_present:
            if sf.get(flag):
                features_present[flag] += 1
        domain = sf.get("featured_snippet_domain")
        if domain:
            # Find category from positions
            category = "UNKNOWN"
            for pos in kw_obj.get("positions", []):
                if pos.get("domain", "").lower() in domain.lower() or domain.lower() in pos.get("domain", "").lower():
                    category = pos.get("category", "UNKNOWN")
                    break
            snippet_owners.append({
                "domain": domain,
                "keyword": kw_obj.get("keyword", ""),
                "category": category,
            })

    # Snippet ownership by category
    category_counts: dict[str, int] = defaultdict(int)
    for s in snippet_owners:
        category_counts[s["category"]] += 1

    return {
        "total_keywords": total,
        "keywords_with_featured_snippet": len(snippet_owners),
        "feature_counts": features_present,
        "snippet_owners": snippet_owners,
        "snippet_category_breakdown": dict(category_counts),
    }


def snippet_language_summary(keywords: list[dict]) -> dict:
    """
    Aggregate snippet language analysis across all keywords for Section 2.
    """
    bonus_by_keyword = []
    compliance_by_keyword = []
    all_bonus_amounts: set[str] = set()
    all_cta_types: set[str] = set()
    all_years: set[int] = set()
    ratings_count = 0

    for kw_obj in keywords:
        sf = kw_obj.get("serp_features") or {}
        sa = sf.get("snippet_analysis") or {}
        kw_name = kw_obj.get("keyword", "")

        bonus_count = sa.get("bonus_language_count", 0)
        compliance_count = sa.get("compliance_language_count", 0)

        bonus_by_keyword.append({
            "keyword": kw_name,
            "bonus_count": bonus_count,
            "max": 10,
        })
        compliance_by_keyword.append({
            "keyword": kw_name,
            "compliance_count": compliance_count,
        })
        all_bonus_amounts.update(sa.get("bonus_amounts", []))
        all_cta_types.update(sa.get("cta_types", []))
        all_years.update(sa.get("freshness_years", []))
        if sa.get("review_ratings_present"):
            ratings_count += 1

    # Sort bonus heat highest first
    bonus_by_keyword.sort(key=lambda x: -x["bonus_count"])

    # Compliance distribution buckets
    zero = sum(1 for k in compliance_by_keyword if k["compliance_count"] == 0)
    low = sum(1 for k in compliance_by_keyword if 1 <= k["compliance_count"] <= 3)
    high = sum(1 for k in compliance_by_keyword if k["compliance_count"] >= 4)

    return {
        "bonus_heat": bonus_by_keyword,
        "compliance_distribution": {"zero": zero, "low_1_3": low, "high_4_plus": high},
        "all_bonus_amounts": sorted(all_bonus_amounts),
        "all_cta_types": sorted(all_cta_types),
        "freshness_years": sorted(all_years, reverse=True),
        "keywords_with_ratings": ratings_count,
    }
