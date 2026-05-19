"""OpenAI client for SERP extraction + classification."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_and_classify.md"

VALID_CATEGORIES = {
    "SUBDOMAIN", "HACKED", "PARASITE", "UGC",
    "PUBLISHER", "OPERATOR", "GOV", "APP",
}


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
