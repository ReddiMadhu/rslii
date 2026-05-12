"""
LLM-based description enrichment for ETL lineage nodes.

Sends a batch of nodes (with their code + template description) to the LLM
and gets back richer, context-aware descriptions.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from .llm_factory import get_resilient_llm, stringify_chat_content

logger = logging.getLogger(__name__)

# ─── Prompt ───

SYSTEM_PROMPT = """You are an expert data engineer explaining ETL pipeline operations.
Given a list of ETL operations from a Python script, generate a clear, concise
natural-language description for each one.

Rules:
- Each description should be 1-2 sentences max.
- Focus on WHAT the operation does in the context of the pipeline, not HOW.
- Reference column names, file names, and conditions when available.
- Use present tense ("Reads...", "Filters...", "Merges...").
- Do NOT include code snippets in descriptions.

Return a JSON object with this exact structure:
{
  "descriptions": [
    {"id": "node_1", "description": "your description here"},
    {"id": "node_2", "description": "your description here"}
  ]
}
"""


def _build_user_prompt(nodes: list[dict], source_code: str) -> str:
    """Build the user prompt with node details."""
    lines = ["Here are the ETL operations to describe:\n"]

    for n in nodes:
        lines.append(f"### {n['id']} — {n['label']} ({n['category']})")
        lines.append(f"Code: `{n.get('code', 'N/A')}`")
        lines.append(f"Line: {n.get('line_number', '?')}")
        if n.get("schema_refs"):
            lines.append(f"Columns: {', '.join(n['schema_refs'])}")
        lines.append(f"Template description: {n.get('description', 'N/A')}")
        lines.append("")

    lines.append("---")
    lines.append("Full script context (first 80 lines):")
    lines.append("```python")
    script_lines = source_code.splitlines()[:80]
    lines.append("\n".join(script_lines))
    lines.append("```")

    return "\n".join(lines)


def _parse_llm_response(raw: str, node_ids: set[str]) -> dict[str, str]:
    """Parse the LLM response into {node_id: description}."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code block
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("LLM response not valid JSON even after extraction")
                return {}
        else:
            logger.warning("LLM response not valid JSON: %s", raw[:200])
            return {}

    descriptions = data.get("descriptions", [])
    result = {}
    for item in descriptions:
        nid = item.get("id", "")
        desc = item.get("description", "")
        if nid in node_ids and desc:
            result[nid] = desc

    return result


async def enrich_descriptions(
    nodes: list[dict],
    source_code: str,
    *,
    temperature: float = 0.3,
    max_nodes_per_batch: int = 25,
) -> tuple[list[dict], bool]:
    """
    Enrich node descriptions using LLM.

    Returns (enriched_nodes, llm_used).
    If LLM is not configured or fails, returns nodes unchanged with llm_used=False.
    """
    llm = get_resilient_llm(temperature=temperature, json_mode=True)
    if llm is None:
        logger.info("No LLM configured — skipping description enrichment")
        return nodes, False

    if not nodes:
        return nodes, False

    # Batch if too many nodes
    batches = []
    for i in range(0, len(nodes), max_nodes_per_batch):
        batches.append(nodes[i : i + max_nodes_per_batch])

    all_descriptions: dict[str, str] = {}
    node_ids = {n["id"] for n in nodes}

    for batch in batches:
        user_msg = _build_user_prompt(batch, source_code)

        try:
            from langchain_core.messages import SystemMessage, HumanMessage

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_msg),
            ]

            response = await llm.ainvoke(messages)
            raw = stringify_chat_content(response.content)
            batch_descs = _parse_llm_response(raw, node_ids)
            all_descriptions.update(batch_descs)

            logger.info(
                "LLM enriched %d/%d nodes in batch",
                len(batch_descs),
                len(batch),
            )

        except Exception as e:
            logger.warning("LLM enrichment failed for batch: %s", str(e))
            # Continue with remaining batches — partial enrichment is fine

    if not all_descriptions:
        logger.warning("LLM returned no usable descriptions")
        return nodes, False

    # Apply LLM descriptions to nodes
    enriched = []
    for node in nodes:
        node_copy = dict(node)
        if node["id"] in all_descriptions:
            node_copy["description"] = all_descriptions[node["id"]]
            node_copy["description_source"] = "llm"
        enriched.append(node_copy)

    enriched_count = sum(1 for n in enriched if n.get("description_source") == "llm")
    logger.info(
        "LLM enrichment complete: %d/%d nodes enriched",
        enriched_count,
        len(nodes),
    )

    return enriched, True


def is_llm_available() -> bool:
    """Check if any LLM provider is configured."""
    import os
    has_azure = bool(os.getenv("OPENAI_API_KEY", "").strip())
    has_google = bool(
        (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    )
    return has_azure or has_google
