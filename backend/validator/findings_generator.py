"""Key findings and alerts — template + optional LLM."""

from __future__ import annotations

import json
import re
from typing import Any, Optional


def template_key_findings(
    null_blank_columns: int,
    additional_count: int,
    missing_count: int,
    column_lineage: Optional[dict] = None,
) -> list[dict[str, str]]:
    findings = []
    if null_blank_columns:
        impact = "Downstream targets may receive NULL values for affected columns"
        if column_lineage:
            targets = _lineage_null_targets(column_lineage, null_blank_columns)
            if targets:
                impact = f"Target columns may be affected: {', '.join(targets[:5])}"
        findings.append({
            "finding": f"{null_blank_columns} NULL/blank column(s)",
            "impact": impact,
        })
    if additional_count:
        findings.append({
            "finding": f"{additional_count} additional column(s)",
            "impact": "Will not be reflected in target unless mapped in pipeline code",
        })
    if missing_count:
        findings.append({
            "finding": f"{missing_count} missing column(s) vs expected schema",
            "impact": "Target variables may have NULL values unless mapped before execution",
        })
    if not findings:
        findings.append({
            "finding": "No major schema issues detected",
            "impact": "Uploaded file aligns with expected schema for this source",
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


def _lineage_null_targets(lineage: dict, _count: int) -> list[str]:
    out = []
    for _nid, info in (lineage or {}).items():
        if isinstance(info, dict):
            for col in info.get("columns") or []:
                name = col.get("name") if isinstance(col, dict) else col
                if name:
                    out.append(str(name))
    return list(dict.fromkeys(out))[:8]


async def llm_findings(
    profile: dict,
    code: str,
    snapshot: Optional[dict],
    enable_llm: bool,
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

    prompt = f"""Analyze this ETL source upload for schema drift and data quality.

File profile: {json.dumps({k: profile.get(k) for k in ('row_count', 'column_count', 'null_blank_columns', 'columns')}, default=str)[:3000]}
Has previous snapshot: {snapshot is not None}
Pipeline code snippet:
{code[:2500]}

Return JSON: {{"key_findings": [{{"finding": "", "impact": ""}}], "key_alerts": [{{"observation": "", "impact": ""}}]}}"""

    try:
        resp = await llm.ainvoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
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
    enable_llm: bool = False,
) -> tuple[list[dict], list[dict], bool]:
    kf_llm, ka_llm, used = await llm_findings(profile, code, snapshot, enable_llm)
    if used and kf_llm:
        return kf_llm, ka_llm or template_key_alerts(
            profile.get("columns") or [], profile.get("row_count") or 0
        ), True

    kf = template_key_findings(
        profile.get("null_blank_columns") or 0,
        additional_count,
        missing_count,
        (snapshot or {}).get("column_lineage"),
    )
    ka = template_key_alerts(profile.get("columns") or [], profile.get("row_count") or 0)
    return kf, ka, False
