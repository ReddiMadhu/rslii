"""Apply validation overrides by writing preprocessed upload files."""

from __future__ import annotations

import logging
import os
from typing import Any

from .file_reader import read_source_dataframe

logger = logging.getLogger(__name__)


def apply_overrides_to_uploads(
    saved_paths_by_source_id: dict[str, str],
    sources_meta: list[dict],
    overrides: dict[str, Any],
    uploads_dir: str,
) -> dict[str, str]:
    """
    Return updated ``saved_paths_by_source_id`` pointing at preprocessed files when overrides exist.
    """
    if not overrides:
        return saved_paths_by_source_id

    out = dict(saved_paths_by_source_id)
    for s in sources_meta:
        if not s.get("requires_upload"):
            continue
        sid = s["id"]
        ovr = overrides.get(sid) or {}
        renames = ovr.get("column_renames") or {}
        casts = ovr.get("dtype_casts") or {}
        if not renames and not casts:
            continue

        path = saved_paths_by_source_id.get(sid)
        if not path or not os.path.isfile(path):
            continue

        fmt = s.get("format") or "csv"
        df = read_source_dataframe(path, fmt)
        if renames:
            df = df.rename(columns=renames)
        for col, dtype in casts.items():
            if col not in df.columns:
                continue
            try:
                df[col] = df[col].astype(dtype)
            except Exception as e:
                logger.warning("astype failed for %s: %s", col, e)

        ext = os.path.splitext(path)[1] or ".csv"
        dest = os.path.join(uploads_dir, f"_rsli_preprocessed_{sid}{ext}")
        if fmt == "parquet":
            df.to_parquet(dest, index=False)
        elif fmt == "excel":
            df.to_excel(dest, index=False)
        else:
            df.to_csv(dest, index=False)
        out[sid] = dest

    return out
