"""Read uploaded source files with row caps for validation."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd


def _demo_mode() -> bool:
    return os.environ.get("RSLI_DEMO_MODE", "").strip().lower() in ("1", "true", "yes", "on")


def read_limit() -> int:
    if _demo_mode():
        return 100
    return 1000


def read_source_dataframe(file_path: str, fmt: str) -> pd.DataFrame:
    """Read up to ``read_limit()`` rows from a source file."""
    from .csv_export import sanitize_dataframe

    nrows = read_limit()
    fmt = (fmt or "csv").lower()
    if fmt == "csv":
        df = pd.read_csv(file_path, nrows=nrows)
    elif fmt == "parquet":
        df = pd.read_parquet(file_path).head(nrows)
    elif fmt == "excel":
        df = pd.read_excel(file_path, nrows=nrows)
    elif fmt == "json":
        df = pd.read_json(file_path).head(nrows)
    elif fmt == "html":
        tables = pd.read_html(file_path)
        df = tables[0].head(nrows) if tables else pd.DataFrame()
    elif fmt == "feather":
        df = pd.read_feather(file_path).head(nrows)
    elif fmt == "orc":
        df = pd.read_orc(file_path).head(nrows)
    elif fmt == "stata":
        df = pd.read_stata(file_path)
    elif fmt == "pickle":
        df = pd.read_pickle(file_path)
        df = df.head(nrows) if hasattr(df, "head") else df
    else:
        df = pd.read_csv(file_path, nrows=nrows)
    return sanitize_dataframe(df)


def dtype_label(dtype: Any) -> str:
    s = str(dtype)
    if s.startswith("dtype("):
        s = s[6:-2].strip("'\"")
    mapping = {
        "int64": "numeric",
        "float64": "numeric",
        "object": "string",
        "bool": "boolean",
        "datetime64[ns]": "datetime",
    }
    return mapping.get(s, s)


def profile_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Column stats, sample rows, null-blank column count."""
    total_rows = len(df)
    columns = []
    null_blank_columns = 0
    for name in df.columns:
        col = df[name]
        null_count = int(col.isna().sum())
        if col.dtype == object:
            as_str = col.astype(str).str.strip()
            blank_mask = as_str.eq("") | as_str.str.upper().eq("NULL") | as_str.str.upper().eq("NAN")
            blank_count = int(blank_mask.sum())
        else:
            blank_count = 0
        combined_null = null_count + blank_count
        is_fully_null = total_rows > 0 and combined_null >= total_rows
        if is_fully_null:
            null_blank_columns += 1
        columns.append({
            "name": str(name),
            "dtype": dtype_label(col.dtype),
            "null_count": combined_null,
            "is_fully_null": is_fully_null,
        })

    sample = df.head(6).replace({float("nan"): None}).to_dict(orient="records")
    for row in sample:
        for k, v in list(row.items()):
            if pd.isna(v):
                row[k] = None

    return {
        "row_count": total_rows,
        "column_count": len(df.columns),
        "null_blank_columns": null_blank_columns,
        "columns": columns,
        "sample_data": sample,
        "column_names": [str(c) for c in df.columns],
    }
