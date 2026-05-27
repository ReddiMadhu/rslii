"""Key findings and alerts — template + optional LLM."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

# Drop findings that only describe nulls or dtypes (not pipeline/schema drift).
_NON_PIPELINE_FINDING = re.compile(
    r"null|blank|dtype|data\s*type|entirely\s+empty|fully\s+null",
    re.IGNORECASE,
)


def _filter_pipeline_findings(findings: list[dict]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for f in findings:
        text = f"{f.get('finding', '')} {f.get('impact', '')}"
        if _NON_PIPELINE_FINDING.search(text):
            continue
        out.append({"finding": str(f.get("finding", "")), "impact": str(f.get("impact", ""))})
    return out


def template_key_findings(
    additional_count: int,
    missing_count: int,
    dtype_count: int = 0,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if additional_count:
        findings.append({
            "finding": f"{additional_count} new column(s)",
            "impact": "Will not be reflected in target unless mapped in pipeline code",
        })
    if missing_count:
        findings.append({
            "finding": f"{missing_count} missing column(s) vs expected schema",
            "impact": "Target variables may have NULL values unless mapped before execution",
        })
    if dtype_count:
        findings.append({
            "finding": f"{dtype_count} data type change(s) vs expected schema",
            "impact": "May cause type errors or implicit casts during pipeline execution",
        })
    return findings


def template_key_alerts(columns: list[dict], row_count: int = 0) -> list[dict[str, str]]:
    alerts = []
    for c in columns:
        name = c.get("name", "")
        null_count = int(c.get("null_count") or 0)
        if c.get("is_fully_null"):
            alerts.append({
                "observation": f"Column '{name}' is entirely NULL/blank",
                "impact": "May cause downstream NULL propagation",
            })
        elif row_count > 0 and null_count > 0:
            ratio = null_count / row_count
            if ratio >= 0.5:
                alerts.append({
                    "observation": f"Column '{name}' is mostly NULL/blank ({null_count}/{row_count} rows)",
                    "impact": "May cause downstream NULL propagation",
                })
    return alerts


from sqlalchemy.orm import Session
import os

async def llm_findings(
    profile: dict,
    code: str,
    snapshot: Optional[dict],
    enable_llm: bool,
    db: Optional[Session] = None,
    username: Optional[str] = None,
) -> tuple[list[dict], list[dict], bool]:
    if not enable_llm:
        return [], [], False
    try:
        from llm.llm_factory import get_resilient_llm
    except ImportError:
        return [], [], False

    llm = get_resilient_llm(temperature=0.2, json_mode=True)
    if llm is None:
        return [], [], False

    prompt = f"""Analyze this ETL source upload for schema drift affecting the pipeline.

File profile: {json.dumps({k: profile.get(k) for k in ('row_count', 'column_count', 'columns')}, default=str)[:3000]}
Has previous snapshot: {snapshot is not None}
Pipeline code snippet:
{code[:2500]}

Focus only on missing columns, new/unexpected columns, and schema drift that breaks ETL or downstream targets.
Do NOT report null counts, blank columns, or data type labels as key findings.

Return JSON: {{"key_findings": [{{"finding": "", "impact": ""}}], "key_alerts": [{{"observation": "", "impact": ""}}]}}"""

    try:
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
                logging.getLogger("rsli").warning("Failed to log LLM findings call: %s", ex)

        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return [], [], False
        data = json.loads(m.group())
        kf = data.get("key_findings") or []
        ka = data.get("key_alerts") or []
        return kf, ka, True
    except Exception:
        return [], [], False


async def generate_findings(
    profile: dict,
    code: str,
    snapshot: Optional[dict],
    *,
    additional_count: int = 0,
    missing_count: int = 0,
    dtype_count: int = 0,
    enable_llm: bool = False,
    db: Optional[Session] = None,
    username: Optional[str] = None,
) -> tuple[list[dict], list[dict], bool]:
    template_kf = template_key_findings(additional_count, missing_count, dtype_count)
    kf_llm, ka_llm, used = await llm_findings(profile, code, snapshot, enable_llm, db=db, username=username)
    if used and kf_llm:
        kf = _filter_pipeline_findings(kf_llm)
        if not kf:
            kf = template_kf
        return kf, ka_llm or template_key_alerts(
            profile.get("columns") or [], profile.get("row_count") or 0
        ), True

    kf = template_kf
    ka = template_key_alerts(profile.get("columns") or [], profile.get("row_count") or 0)
    return kf, ka, False
