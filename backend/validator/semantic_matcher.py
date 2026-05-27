"""Column semantic matching — LLM with difflib fuzzy fallback."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any, Optional


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _tokens(name: str) -> set[str]:
    return {t for t in re.split(r"[_\s]+", name.lower()) if t}


# Common rename pairs in drifted / legacy source files
_RENAME_TOKEN_PAIRS = (
    ("smoker", "tobacco"),
    ("face", "coverage"),
    ("amount", "value"),
    ("status", "usage"),
    ("claim", "reported"),
)


def _semantic_rename_score(expected_name: str, candidate: str) -> float:
    """Heuristic score for renamed columns (e.g. smoker_status → tobacco_usage)."""
    exp_t = _tokens(expected_name)
    cand_t = _tokens(candidate)
    if not exp_t or not cand_t:
        return 0.0
    overlap = len(exp_t & cand_t) / len(exp_t | cand_t)
    score = overlap
    for a, b in _RENAME_TOKEN_PAIRS:
        if (a in exp_t and b in cand_t) or (b in exp_t and a in cand_t):
            score = max(score, 0.55 + 0.15 * len(exp_t & cand_t))
    # claim_date ↔ reported_date — same semantic date field
    if "date" in exp_t and "date" in cand_t:
        if ("claim" in exp_t and "reported" in cand_t) or ("reported" in exp_t and "claim" in cand_t):
            score = max(score, 0.88)
    return min(score, 0.92)


def fuzzy_match_columns(
    expected_name: str,
    candidate_columns: list[str],
    *,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    scored = []
    seen: set[str] = set()
    for col in candidate_columns:
        if col.lower() == expected_name.lower():
            scored.append({
                "column": col,
                "confidence": 0.95,
                "reason": "Exact name match (case-insensitive)",
            })
            seen.add(col)
            continue
        ratio = max(_similarity(expected_name, col), _semantic_rename_score(expected_name, col))
        if ratio >= 0.35:
            reason = "Semantic rename similarity" if ratio >= 0.55 else "Fuzzy text similarity"
            scored.append({
                "column": col,
                "confidence": round(ratio, 2),
                "reason": reason,
            })
            seen.add(col)
    scored.sort(key=lambda x: -x["confidence"])
    return scored[:top_n]


from sqlalchemy.orm import Session

async def llm_match_columns(
    expected_name: str,
    expected_dtype: str,
    candidate_columns: list[dict[str, Any]],
    code_context: str,
    sample_values: Optional[dict[str, list]] = None,
    db: Optional[Session] = None,
    username: Optional[str] = None,
) -> Optional[list[dict[str, Any]]]:
    try:
        from llm.llm_factory import get_resilient_llm
    except ImportError:
        return None

    llm = get_resilient_llm(temperature=0.1, json_mode=True)
    if llm is None:
        return None

    prompt = f"""Match the expected ETL column to the best uploaded column candidates.

Expected column: {expected_name} ({expected_dtype})
Candidates: {json.dumps(candidate_columns)}
Sample values: {json.dumps(sample_values or {})}

Code context (snippet):
{code_context[:2000]}

Return JSON array: [{{"column": "name", "confidence": 0.0-1.0, "reason": "brief"}}]
Only include candidates with confidence > 0.3. Max 5 items."""

    try:
        import os
        resp = await llm.ainvoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)

        # Metadata and token usage extraction for audit trail
        metadata = getattr(resp, "response_metadata", {})
        usage = metadata.get("token_usage") or metadata.get("usage_metadata") or {}
        tokens = usage.get("total_tokens") or usage.get("total_billable_characters") or 0
        model_name = metadata.get("model_name") or os.environ.get("GEMINI_MODEL") or os.environ.get("OPENAI_MODEL") or "unknown"

        if db and username:
            try:
                from audit.logger import log_llm_call
                await log_llm_call(
                    db=db,
                    session_id=None,
                    username=username,
                    prompt=prompt,
                    response_content=text,
                    model_name=model_name,
                    tokens=tokens,
                )
            except Exception as ex:
                import logging
                logging.getLogger("rsli").warning("Failed to log LLM semantic match call: %s", ex)

        m = re.search(r"\[[\s\S]*\]", text)
        if not m:
            return None
        data = json.loads(m.group())
        if isinstance(data, list):
            return [
                {
                    "column": str(x.get("column", "")),
                    "confidence": float(x.get("confidence", 0)),
                    "reason": str(x.get("reason", "LLM semantic match")),
                }
                for x in data
                if x.get("column")
            ]
    except Exception:
        return None
    return None


class SemanticColumnMatcher:
    def __init__(self, *, enable_llm: bool = False, code: str = "", db: Optional[Session] = None, username: Optional[str] = None) -> None:
        self.enable_llm = enable_llm
        self.code = code
        self.db = db
        self.username = username

    async def recommend(
        self,
        expected_name: str,
        expected_dtype: str,
        additional_columns: list[str],
        column_dtypes: dict[str, str],
        sample_data: list[dict],
    ) -> tuple[list[dict[str, Any]], bool]:
        """Returns (recommendations, llm_used)."""
        candidates = [
            {"name": c, "dtype": column_dtypes.get(c, "unknown")}
            for c in additional_columns
        ]
        sample_values = {}
        for c in additional_columns[:8]:
            sample_values[c] = [
                row.get(c) for row in (sample_data or [])[:3]
                if row.get(c) is not None
            ]

        if self.enable_llm and additional_columns:
            llm_result = await llm_match_columns(
                expected_name,
                expected_dtype,
                candidates,
                self.code,
                None, # Strip sample values to ensure no PII goes to LLM
                db=self.db,
                username=self.username,
            )
            if llm_result:
                return llm_result, True

        return fuzzy_match_columns(expected_name, additional_columns), False
