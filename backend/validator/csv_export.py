"""Prepare DataFrames for CSV — drop sparse blank columns and fill nulls."""

from __future__ import annotations

import pandas as pd

_BLANK_STRINGS = frozenset({"", "null", "nan", "none"})
# Drop columns that are mostly empty (same threshold as key-alerts).
_SPARSE_COLUMN_RATIO = 0.5


def _blank_mask(s: pd.Series) -> pd.Series:
    if s.dtype == object or pd.api.types.is_string_dtype(s):
        as_str = s.fillna("").astype(str).str.strip().str.lower()
        return s.isna() | as_str.isin(_BLANK_STRINGS)
    return s.isna()


def _is_sparse_blank_column(s: pd.Series) -> bool:
    if len(s) == 0:
        return True
    blank = int(_blank_mask(s).sum())
    return blank >= len(s) * _SPARSE_COLUMN_RATIO


def _is_fully_blank_column(s: pd.Series) -> bool:
    if len(s) == 0:
        return True
    return int(_blank_mask(s).sum()) >= len(s)


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Drop all-blank or mostly-blank columns; fill remaining null/blank cells."""
    out = df.copy()
    drop_cols = [c for c in out.columns if _is_sparse_blank_column(out[c])]
    if drop_cols:
        out = out.drop(columns=drop_cols)
    return prepare_dataframe_for_csv(out)


def prepare_dataframe_for_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Drop all-null/blank columns and replace remaining nulls before writing CSV."""
    out = df.copy()

    drop_cols = [c for c in out.columns if _is_fully_blank_column(out[c])]
    if drop_cols:
        out = out.drop(columns=drop_cols)

    for col in out.columns:
        if out[col].isna().any() or (out[col].dtype == object):
            blank = _blank_mask(out[col])
            if blank.any():
                if pd.api.types.is_numeric_dtype(out[col]):
                    out[col] = out[col].fillna(0)
                elif pd.api.types.is_bool_dtype(out[col]):
                    out[col] = out[col].fillna(False)
                else:
                    out.loc[blank, col] = ""
                    out[col] = out[col].fillna("")

    return out
