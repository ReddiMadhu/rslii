"""Runtime DataFrame snapshot capture for instrumented pipelines."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .context import NodeSnapshot

if TYPE_CHECKING:
    from .context import RSLIContext


def rsli_snapshot_fn(node_id: str, method: str, df: Any, ctx: RSLIContext) -> None:
    """Injected into user code after each ETL step."""
    import pandas as pd

    if df is None:
        return

    is_groupby = type(df).__name__ in ("DataFrameGroupBy", "SeriesGroupBy")
    if not isinstance(df, (pd.DataFrame, pd.Series)) and not is_groupby:
        return

    # If it's a GroupBy object, we extract the underlying dataframe to get columns/stats
    if is_groupby:
        df = getattr(df, "obj", df)

    end = time.perf_counter()
    duration_ms = round((end - ctx.step_start) * 1000, 2)

    prev_id = ctx.get_input_node(node_id)
    prev_snap = ctx.snapshots.get(prev_id) if prev_id else None
    prev_df = ctx.dataframes.get(prev_id) if prev_id else None

    rows_in = prev_snap.rows_out if prev_snap else None
    cols_in = prev_snap.cols_out if prev_snap else None
    cols_before = list(prev_df.columns) if prev_df is not None else []
    cols_after = list(df.columns)

    snap = NodeSnapshot(
        node_id=node_id,
        status="completed",
        rows_in=rows_in,
        rows_out=len(df),
        cols_in=cols_in,
        cols_out=len(df.columns),
        columns_before=cols_before,
        columns_after=cols_after,
        dtypes_before={c: str(t) for c, t in prev_df.dtypes.items()} if prev_df is not None else {},
        dtypes_after={c: str(t) for c, t in df.dtypes.items()},
        duration_ms=duration_ms,
        sample_output=df.head(5).to_dict(orient="records"),
        sample_input=prev_df.head(5).to_dict(orient="records") if prev_df is not None else [],
        null_counts={c: int(v) for c, v in df.isnull().sum().items()},
    )

    snap.cols_added = [c for c in cols_after if c not in cols_before]
    snap.cols_removed = [c for c in cols_before if c not in cols_after]
    snap.cols_renamed = dict(ctx.get_rename_map(node_id))

    # Detect dtype-transformed columns (present in both before & after but dtype changed)
    dtypes_before = snap.dtypes_before
    dtypes_after = snap.dtypes_after
    snap.cols_transformed = {
        c: {"from": dtypes_before[c], "to": dtypes_after[c]}
        for c in cols_after
        if c in cols_before and c in dtypes_before and c in dtypes_after
        and dtypes_before[c] != dtypes_after[c]
    }

    # Categorise new columns: derived (computed) vs joined (from merge/join)
    if method in ("merge", "join", "concat"):
        snap.cols_joined = list(snap.cols_added)
        snap.cols_derived = []
    else:
        snap.cols_derived = list(snap.cols_added)
        snap.cols_joined = []

    ri, ro = rows_in or 0, len(df)
    if method in ("dropna", "fillna"):
        snap.nulls_handled = max(0, ri - ro)
    if method == "drop_duplicates":
        snap.duplicates_removed = max(0, ri - ro)
    if method in ("boolean_index", "query", "where", "mask", "sample"):
        snap.rows_filtered = max(0, ri - ro)

    ctx.store_snapshot(node_id, snap, df.copy())
