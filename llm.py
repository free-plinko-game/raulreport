"""OpenAI client for SERP extraction + classification."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from config import VALID_CATEGORIES  # single source of truth for the taxonomy

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_and_classify.md"
ADS_PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_ads.md"
ADS_REPORT_PROMPT_PATH = Path(__file__).parent / "prompts" / "ads_report_analysis.md"
SERP_FEATURES_PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_serp_features.md"
CLUSTER_PAA_PROMPT_PATH = Path(__file__).parent / "prompts" / "cluster_paa.md"

VALID_AD_POSITIONS = {"top", "bottom", "shopping"}


class LLMError(Exception):
    pass


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("OPENAI_API_KEY not set")
        _client = OpenAI(api_key=api_key)
    return _client


def _load_system_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_ads_prompt() -> str:
    with open(ADS_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_ads_report_prompt() -> str:
    with open(ADS_REPORT_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_serp_features_prompt() -> str:
    with open(SERP_FEATURES_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _load_cluster_paa_prompt() -> str:
    with open(CLUSTER_PAA_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _validate_result(data: dict) -> tuple[list[dict], list[dict]]:
    if not isinstance(data, dict):
        raise LLMError("LLM returned non-object JSON")
    positions = data.get("positions", [])
    warnings = data.get("warnings", []) or []
    if not isinstance(positions, list):
        raise LLMError("`positions` is not a list")
    cleaned: list[dict] = []
    for i, p in enumerate(positions):
        if not isinstance(p, dict):
            continue
        cat = (p.get("category") or "").upper().strip()
        if cat not in VALID_CATEGORIES:
            warnings.append({
                "rank": p.get("rank"),
                "issue": f"invalid category {cat!r} from LLM, defaulting to PARASITE",
                "detail": "Edit this row to correct.",
            })
            cat = "PARASITE"
        cleaned.append({
            "rank": int(p.get("rank", i + 1)),
            "short_label": str(p.get("short_label", "")).strip(),
            "domain": str(p.get("domain", "")).strip().lower().lstrip("www."),
            "full_url": str(p.get("full_url", "")).strip(),
            "category": cat,
            "reasoning": str(p.get("reasoning", "")).strip(),
            "edited": False,
        })
    return cleaned, warnings


def classify_paste(keyword: str, raw_paste: str) -> tuple[list[dict], list[dict], dict]:
    """Returns (positions, warnings, usage)."""
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = _load_system_prompt()
    user_msg = (
        f"Keyword: {keyword}\n\n"
        f"--- BEGIN RAW SERP PASTE ---\n{raw_paste}\n--- END RAW SERP PASTE ---"
    )

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                timeout=60,
            )
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    last_err = e
                    continue
                raise LLMError(f"Could not parse LLM JSON: {e}. Raw: {content[:500]}")
            positions, warnings = _validate_result(data)
            usage = {
                "model": model,
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
            }
            logger.info(
                "LLM ok keyword=%r prompt=%d completion=%d positions=%d",
                keyword, usage["prompt_tokens"], usage["completion_tokens"], len(positions),
            )
            return positions, warnings, usage
        except (RateLimitError, APITimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
        except APIError as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
            continue

    raise LLMError(f"LLM request failed after retries: {last_err}")


def _validate_ads(data: dict) -> list[dict]:
    ads_raw = data.get("ads", []) or []
    if not isinstance(ads_raw, list):
        return []
    ads: list[dict] = []
    for i, a in enumerate(ads_raw):
        if not isinstance(a, dict):
            continue
        ad_pos = (a.get("ad_position") or "top").lower().strip()
        if ad_pos not in VALID_AD_POSITIONS:
            ad_pos = "top"
        dom_cat = (a.get("domain_category") or "OTHER").upper().strip()
        if dom_cat not in VALID_CATEGORIES:
            dom_cat = "OTHER"
        ads.append({
            "position": int(a.get("position", i + 1)),
            "ad_position": ad_pos,
            "advertiser": str(a.get("advertiser", "")).strip(),
            "display_url": str(a.get("display_url", "")).strip(),
            "landing_url": str(a.get("landing_url", "")).strip(),
            "is_offshore": bool(a.get("is_offshore", False)),
            "notes": str(a.get("notes", "")).strip(),
            "domain_category": dom_cat,
        })
    return ads


def extract_ads_paste(keyword: str, raw_paste: str) -> tuple[list[dict], dict]:
    """Returns (ads, usage). Second focused LLM call — ads only."""
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = _load_ads_prompt()
    user_msg = (
        f"Keyword: {keyword}\n\n"
        f"--- BEGIN RAW SERP PASTE ---\n{raw_paste}\n--- END RAW SERP PASTE ---"
    )

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                timeout=60,
            )
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    last_err = e
                    continue
                raise LLMError(f"Could not parse ads JSON: {e}. Raw: {content[:500]}")
            if not isinstance(data, dict):
                raise LLMError("Ads LLM returned non-object JSON")
            ads = _validate_ads(data)
            usage = {
                "model": model,
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
            }
            logger.info(
                "Ads LLM ok keyword=%r prompt=%d completion=%d ads=%d",
                keyword, usage["prompt_tokens"], usage["completion_tokens"], len(ads),
            )
            return ads, usage
        except (RateLimitError, APITimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
        except APIError as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
            continue

    raise LLMError(f"Ads LLM request failed after retries: {last_err}")


VALID_AD_TYPES = {
    "LICENSED_OPERATOR", "OFFSHORE_OPERATOR", "AFFILIATE",
    "CRYPTO_CASINO", "APP", "OTHER",
}


def generate_ads_report_analysis(run_date: str, keywords_with_ads: list[dict]) -> dict:
    """
    Takes a list of {keyword, ads} dicts and returns a structured analysis dict.
    Uses gpt-4o (not mini) for the narrative quality.
    """
    client = _get_client()
    model = os.environ.get("OPENAI_REPORT_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o"))
    system_prompt = _load_ads_report_prompt()

    ads_input = json.dumps({
        "run_date": run_date,
        "keywords": keywords_with_ads,
    }, ensure_ascii=False)
    user_msg = f"Analyse the following ads data and produce the report:\n\n{ads_input}"

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                timeout=120,
            )
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    last_err = e
                    continue
                raise LLMError(f"Could not parse report JSON: {e}")
            if not isinstance(data, dict):
                raise LLMError("Report LLM returned non-object JSON")
            usage = {
                "model": model,
                "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
            }
            logger.info(
                "Report LLM ok run=%r prompt=%d completion=%d",
                run_date, usage["prompt_tokens"], usage["completion_tokens"],
            )
            return data
        except (RateLimitError, APITimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
        except APIError as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
            continue

    raise LLMError(f"Report LLM request failed after retries: {last_err}")


def extract_serp_features(keyword: str, raw_paste: str) -> dict:
    """Returns serp_features dict for one keyword."""
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    system_prompt = _load_serp_features_prompt()
    user_msg = (
        f"Keyword: {keyword}\n\n"
        f"--- BEGIN RAW SERP PASTE ---\n{raw_paste}\n--- END RAW SERP PASTE ---"
    )
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                timeout=60,
            )
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    last_err = e
                    continue
                raise LLMError(f"Could not parse serp_features JSON: {e}")
            if not isinstance(data, dict):
                raise LLMError("SERP features LLM returned non-object JSON")
            logger.info("SERP features ok keyword=%r", keyword)
            return data
        except (RateLimitError, APITimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
        except APIError as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
            continue
    raise LLMError(f"SERP features LLM failed after retries: {last_err}")


def cluster_paa(run_date: str, paa_items: list[dict]) -> dict:
    """
    Takes list of {question, keyword} dicts, returns cluster dict.
    Uses gpt-4o for better grouping quality.
    """
    client = _get_client()
    model = os.environ.get("OPENAI_REPORT_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o"))
    system_prompt = _load_cluster_paa_prompt()
    user_msg = (
        f"Run date: {run_date}\n\n"
        f"PAA questions:\n{json.dumps(paa_items, ensure_ascii=False)}"
    )
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=0.1,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                timeout=90,
            )
            content = resp.choices[0].message.content or "{}"
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt == 0:
                    last_err = e
                    continue
                raise LLMError(f"Could not parse PAA cluster JSON: {e}")
            if not isinstance(data, dict):
                raise LLMError("PAA cluster LLM returned non-object JSON")
            logger.info("PAA cluster ok run=%r questions=%d", run_date, len(paa_items))
            return data
        except (RateLimitError, APITimeoutError) as e:
            last_err = e
            time.sleep(2 ** attempt)
            continue
        except APIError as e:
            last_err = e
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
            continue
    raise LLMError(f"PAA cluster LLM failed after retries: {last_err}")
