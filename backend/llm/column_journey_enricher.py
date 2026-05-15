"""
GenAI column-journey enrichment — plain-English summaries for business analysts.

Called lazily when a user selects a column + direction in the Column-level
Journey tab.  Sends the trace context to the LLM and receives:
  • per-node one-sentence business explanation
  • overall 2-3 sentence narrative of the column's journey
"""
from __future__ import annotations

import json
import logging
from typing import Any

from .llm_factory import get_resilient_llm, stringify_chat_content

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are explaining a data column's journey through an ETL pipeline to a
non-technical business analyst.

Rules:
- For EACH step, write ONE clear sentence explaining what happened to this
  column in plain business language.
- Avoid technical jargon like "DataFrame", "merge", "groupby", "boolean index",
  "fillna", "astype".  Instead use phrases like "combined with claims data",
  "summarised by product type", "calculated from premium and claim amounts",
  "missing values were filled with zero".
- For passthrough steps where nothing changed, write something like
  "This column passed through unchanged."
- Write an overall_summary (2-3 flowing sentences, NOT bullet points) that
  tells the complete story of how this column was created or transformed from
  source to final output.
- The overall_summary should read like a short paragraph a business analyst
  would include in a report.

Return ONLY a JSON object with this exact structure:
{
  "node_summaries": [
    {"id": "<trace_node_id>", "summary": "plain-English sentence"}
  ],
  "overall_summary": "2-3 sentence narrative paragraph"
}
"""


def _build_user_prompt(
    column: str,
    direction: str,
    trace_nodes: list[dict],
    source_code: str,
) -> str:
    """Build the user prompt with column journey context."""
    lines = [
        f"Column: **{column}**",
        f"Direction: {direction} ({'source → target' if direction == 'downstream' else 'target → source'})",
        "",
        "### Steps in this column's journey",
        "",
    ]

    for tn in trace_nodes:
        lines.append(f"**{tn['id']}** — {tn.get('operationLabel', '')} ({tn.get('operationCategory', '')})")
        lines.append(f"  State: {tn.get('state', '?')}")
        if tn.get("from"):
            lines.append(f"  Derived from columns: {', '.join(tn['from'])}")
        if tn.get("dtype"):
            lines.append(f"  Data type: {tn['dtype']}")
        if tn.get("code"):
            lines.append(f"  Code: `{tn['code']}`")
        if tn.get("nullCount"):
            lines.append(f"  Null count: {tn['nullCount']}")
        lines.append("")

    lines.append("---")
    lines.append("Full script context (first 80 lines):")
    lines.append("```python")
    script_lines = source_code.splitlines()[:80]
    lines.append("\n".join(script_lines))
    lines.append("```")

    return "\n".join(lines)


def _parse_response(raw: str, trace_ids: set[str]) -> dict:
    """Parse LLM response into {node_summaries: {id: summary}, overall_summary: str}."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("Column journey LLM response not valid JSON even after extraction")
                return {"node_summaries": {}, "overall_summary": ""}
        else:
            logger.warning("Column journey LLM response not valid JSON: %s", raw[:200])
            return {"node_summaries": {}, "overall_summary": ""}

    node_summaries: dict[str, str] = {}
    for item in data.get("node_summaries", []):
        nid = item.get("id", "")
        summary = item.get("summary", "")
        if nid and summary:
            node_summaries[nid] = summary

    return {
        "node_summaries": node_summaries,
        "overall_summary": data.get("overall_summary", ""),
    }


async def enrich_column_journey(
    column: str,
    direction: str,
    trace_nodes: list[dict],
    source_code: str,
    *,
    temperature: float = 0.3,
) -> dict:
    """
    Generate GenAI summaries for a column's journey.

    Returns:
        {
            "node_summaries": {"node_5:loss_ratio": "...", ...},
            "overall_summary": "2-3 sentence narrative",
            "llm_used": True/False
        }
    """
    llm = get_resilient_llm(temperature=temperature, json_mode=True)
    if llm is None:
        logger.info("No LLM configured — skipping column journey enrichment")
        return {"node_summaries": {}, "overall_summary": "", "llm_used": False}

    if not trace_nodes:
        return {"node_summaries": {}, "overall_summary": "", "llm_used": False}

    user_msg = _build_user_prompt(column, direction, trace_nodes, source_code)
    trace_ids = {tn["id"] for tn in trace_nodes}

    try:
        from langchain_core.messages import SystemMessage, HumanMessage

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ]

        response = await llm.ainvoke(messages)
        raw = stringify_chat_content(response.content)
        parsed = _parse_response(raw, trace_ids)

        logger.info(
            "Column journey enriched: %d/%d nodes, column=%s",
            len(parsed["node_summaries"]),
            len(trace_nodes),
            column,
        )

        return {
            "node_summaries": parsed["node_summaries"],
            "overall_summary": parsed["overall_summary"],
            "llm_used": True,
        }

    except Exception as e:
        logger.warning("Column journey LLM enrichment failed: %s", str(e))
        return {"node_summaries": {}, "overall_summary": "", "llm_used": False}


# ── Template fallback ─────────────────────────────────────────────

_STATE_TEMPLATES = {
    "introduced": "This column originates here — it is first read from the data source.",
    "passthrough": "This column passed through unchanged during this operation.",
    "derived": "This column was calculated from other data fields at this step.",
    "renamed": "This column was given a new name at this step.",
    "aggregated": "This column survived the summarisation step and was included in the grouped output.",
    "agg_dropped": "This column was not included in the summary grouping and was automatically removed.",
    "joined": "This column was brought in from another dataset when the data was combined.",
    "dropped": "This column was explicitly removed at this step.",
    "type_changed": "The data type of this column was converted at this step.",
    "written": "This column was written out to the final output file.",
}


def generate_template_node_summary(trace_node: dict) -> str:
    """Deterministic fallback summary for a single trace node."""
    state = trace_node.get("state", "")
    base = _STATE_TEMPLATES.get(state, "This column was processed at this step.")

    # Enrich with specific context
    from_cols = trace_node.get("from", [])
    col_name = trace_node.get("column", "")

    if state == "derived" and from_cols:
        sources = ", ".join(from_cols)
        base = f"This column was calculated using {sources}."
    elif state == "renamed" and from_cols:
        old = from_cols[0] if from_cols else "?"
        base = f'This column was renamed from "{old}" to "{col_name}".'
    elif state == "aggregated":
        op_label = trace_node.get("operationLabel", "")
        if op_label:
            base = f"This column was summarised as part of the {op_label} step."

    return base


def generate_template_overall_summary(
    column: str, direction: str, trace_nodes: list[dict]
) -> str:
    """Deterministic fallback overall narrative."""
    if not trace_nodes:
        return ""

    states = [tn.get("state", "") for tn in trace_nodes]
    first = trace_nodes[0]
    last = trace_nodes[-1]

    parts = []

    # Origin sentence
    if direction == "downstream":
        parts.append(
            f'The column "{column}" originates at the {first.get("operationLabel", "source")} step'
            f' as a {first.get("dtype", "data")} field.'
        )
    else:
        parts.append(
            f'The column "{column}" appears in the final output at the'
            f' {first.get("operationLabel", "target")} step as a {first.get("dtype", "data")} field.'
        )

    # Key transformations
    events = []
    if "derived" in states:
        dn = next((t for t in trace_nodes if t["state"] == "derived"), None)
        if dn and dn.get("from"):
            events.append(f"calculated from {', '.join(dn['from'])}")
    if "renamed" in states:
        rn = next((t for t in trace_nodes if t["state"] == "renamed"), None)
        if rn and rn.get("from"):
            events.append(f'renamed from "{rn["from"][0]}"')
    if "joined" in states:
        events.append("brought in from a merged dataset")
    if "aggregated" in states:
        events.append("summarised during the grouping step")
    if "type_changed" in states:
        events.append("had its data type converted")

    if events:
        parts.append("Along the way, it was " + ", ".join(events) + ".")

    # Destination sentence
    if "dropped" in states or "agg_dropped" in states:
        parts.append("This column does not appear in the final output.")
    else:
        total_ops = len(trace_nodes)
        parts.append(f"It passes through {total_ops} operation{'s' if total_ops > 1 else ''} in total.")

    return " ".join(parts)
