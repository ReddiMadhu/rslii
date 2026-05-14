"""Unit tests for the ColumnLineageBuilder."""

import pytest
from executor.context import NodeSnapshot
from executor.column_lineage import (
    ColumnLineageBuilder,
    STATE_INTRODUCED,
    STATE_PASSTHROUGH,
    STATE_DERIVED,
    STATE_RENAMED,
    STATE_AGGREGATED,
    STATE_AGG_DROPPED,
    STATE_JOINED,
    STATE_DROPPED,
    STATE_TYPE_CHANGED,
)


def _snap(
    node_id,
    cols_before=None,
    cols_after=None,
    dtypes_before=None,
    dtypes_after=None,
    cols_added=None,
    cols_removed=None,
    cols_renamed=None,
    cols_derived=None,
    cols_joined=None,
    cols_transformed=None,
    null_counts=None,
    status="completed",
):
    """Helper to build a NodeSnapshot with sensible defaults."""
    s = NodeSnapshot(node_id=node_id, status=status)
    s.columns_before = cols_before or []
    s.columns_after = cols_after or []
    s.dtypes_before = dtypes_before or {}
    s.dtypes_after = dtypes_after or {}
    s.cols_added = cols_added or []
    s.cols_removed = cols_removed or []
    s.cols_renamed = cols_renamed or {}
    s.cols_derived = cols_derived or []
    s.cols_joined = cols_joined or []
    s.cols_transformed = cols_transformed or {}
    s.null_counts = null_counts or {}
    return s


# ------------------------------------------------------------------
# Source node
# ------------------------------------------------------------------
def test_source_introduced_columns():
    """All columns on a source node should be state=introduced."""
    nodes = [{"id": "n1", "category": "source", "method": "read_csv", "schema_refs": []}]
    edges = []
    snap = _snap(
        "n1",
        cols_after=["id", "amount", "status"],
        dtypes_after={"id": "int64", "amount": "float64", "status": "object"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n1": snap})
    result = builder.build()

    assert "n1" in result
    assert result["n1"]["id"]["state"] == STATE_INTRODUCED
    assert result["n1"]["amount"]["state"] == STATE_INTRODUCED
    assert result["n1"]["status"]["state"] == STATE_INTRODUCED


# ------------------------------------------------------------------
# Passthrough
# ------------------------------------------------------------------
def test_passthrough_columns():
    """dropna keeps all columns, all should be passthrough."""
    nodes = [{"id": "n2", "category": "clean", "method": "dropna", "schema_refs": ["amount"]}]
    edges = [{"source": "n1", "target": "n2"}]
    snap = _snap(
        "n2",
        cols_before=["id", "amount", "status"],
        cols_after=["id", "amount", "status"],
        dtypes_before={"id": "int64", "amount": "float64", "status": "object"},
        dtypes_after={"id": "int64", "amount": "float64", "status": "object"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n2": snap})
    result = builder.build()

    for col in ("id", "amount", "status"):
        assert result["n2"][col]["state"] == STATE_PASSTHROUGH


# ------------------------------------------------------------------
# Derived column
# ------------------------------------------------------------------
def test_derived_column():
    """df['tax'] = df['amount'] * 0.1 → tax derived from amount."""
    nodes = [
        {"id": "n3", "category": "column_op", "method": "column_assign",
         "schema_refs": ["amount", "tax"]},
    ]
    edges = [{"source": "n2", "target": "n3"}]
    snap = _snap(
        "n3",
        cols_before=["id", "amount"],
        cols_after=["id", "amount", "tax"],
        cols_added=["tax"],
        cols_derived=["tax"],
        dtypes_before={"id": "int64", "amount": "float64"},
        dtypes_after={"id": "int64", "amount": "float64", "tax": "float64"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n3": snap})
    result = builder.build()

    assert result["n3"]["tax"]["state"] == STATE_DERIVED
    assert "amount" in result["n3"]["tax"]["from"]
    assert result["n3"]["id"]["state"] == STATE_PASSTHROUGH


# ------------------------------------------------------------------
# Rename
# ------------------------------------------------------------------
def test_rename_tracking():
    """rename(columns={'a':'b'}) → b renamed from a."""
    nodes = [{"id": "n4", "category": "column_op", "method": "rename", "schema_refs": []}]
    edges = [{"source": "n3", "target": "n4"}]
    snap = _snap(
        "n4",
        cols_before=["id", "amount"],
        cols_after=["id", "total"],
        cols_added=["total"],
        cols_removed=["amount"],
        cols_renamed={"amount": "total"},
        dtypes_before={"id": "int64", "amount": "float64"},
        dtypes_after={"id": "int64", "total": "float64"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n4": snap})
    result = builder.build()

    assert result["n4"]["total"]["state"] == STATE_RENAMED
    assert result["n4"]["total"]["from"] == ["amount"]
    # amount should NOT appear as dropped (it was renamed)
    assert "amount" not in result["n4"]


# ------------------------------------------------------------------
# Merge / joined columns
# ------------------------------------------------------------------
def test_merge_joined_columns():
    """merge introduces cols_joined from right DataFrame."""
    nodes = [{"id": "n5", "category": "join", "method": "merge", "schema_refs": ["id"]}]
    edges = [{"source": "n4", "target": "n5"}]
    snap = _snap(
        "n5",
        cols_before=["id", "amount"],
        cols_after=["id", "amount", "name", "email"],
        cols_added=["name", "email"],
        cols_joined=["name", "email"],
        dtypes_before={"id": "int64", "amount": "float64"},
        dtypes_after={"id": "int64", "amount": "float64", "name": "object", "email": "object"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n5": snap})
    result = builder.build()

    assert result["n5"]["name"]["state"] == STATE_JOINED
    assert result["n5"]["email"]["state"] == STATE_JOINED
    assert result["n5"]["id"]["state"] == STATE_PASSTHROUGH


# ------------------------------------------------------------------
# Aggregation — survivors and dropped
# ------------------------------------------------------------------
def test_aggregation_survivors():
    """groupby key columns survive as aggregated; unlisted columns get agg_dropped."""
    nodes = [{"id": "n6", "category": "aggregation", "method": "groupby", "schema_refs": ["region"]}]
    edges = [{"source": "n5", "target": "n6"}]
    snap = _snap(
        "n6",
        cols_before=["id", "amount", "region"],
        cols_after=["region", "amount"],
        cols_removed=["id"],
        dtypes_before={"id": "int64", "amount": "float64", "region": "object"},
        dtypes_after={"region": "object", "amount": "float64"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n6": snap})
    result = builder.build()

    assert result["n6"]["region"]["state"] == STATE_AGGREGATED
    assert result["n6"]["amount"]["state"] == STATE_AGGREGATED
    assert result["n6"]["id"]["state"] == STATE_AGG_DROPPED


# ------------------------------------------------------------------
# Explicit drop
# ------------------------------------------------------------------
def test_explicit_drop():
    """drop(columns=['x']) → x state is dropped."""
    nodes = [{"id": "n7", "category": "column_op", "method": "drop", "schema_refs": ["temp"]}]
    edges = [{"source": "n6", "target": "n7"}]
    snap = _snap(
        "n7",
        cols_before=["id", "amount", "temp"],
        cols_after=["id", "amount"],
        cols_removed=["temp"],
        dtypes_before={"id": "int64", "amount": "float64", "temp": "float64"},
        dtypes_after={"id": "int64", "amount": "float64"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n7": snap})
    result = builder.build()

    assert result["n7"]["temp"]["state"] == STATE_DROPPED


# ------------------------------------------------------------------
# agg_dropped vs explicit drop
# ------------------------------------------------------------------
def test_agg_drop_vs_explicit_drop():
    """agg_dropped and dropped produce different states."""
    nodes_agg = [{"id": "a", "category": "aggregation", "method": "groupby", "schema_refs": []}]
    nodes_drop = [{"id": "b", "category": "column_op", "method": "drop", "schema_refs": []}]
    snap_agg = _snap("a", cols_before=["x", "y"], cols_after=["x"], cols_removed=["y"],
                      dtypes_before={"x": "int64", "y": "int64"}, dtypes_after={"x": "int64"})
    snap_drop = _snap("b", cols_before=["x", "y"], cols_after=["x"], cols_removed=["y"],
                       dtypes_before={"x": "int64", "y": "int64"}, dtypes_after={"x": "int64"})

    r1 = ColumnLineageBuilder(nodes_agg, [], {"a": snap_agg}).build()
    r2 = ColumnLineageBuilder(nodes_drop, [], {"b": snap_drop}).build()

    assert r1["a"]["y"]["state"] == STATE_AGG_DROPPED
    assert r2["b"]["y"]["state"] == STATE_DROPPED


# ------------------------------------------------------------------
# Type change
# ------------------------------------------------------------------
def test_type_changed():
    """astype produces type_changed state."""
    nodes = [{"id": "n8", "category": "clean", "method": "astype", "schema_refs": ["amount"]}]
    edges = []
    snap = _snap(
        "n8",
        cols_before=["id", "amount"],
        cols_after=["id", "amount"],
        cols_transformed={"amount": {"from": "object", "to": "float64"}},
        dtypes_before={"id": "int64", "amount": "object"},
        dtypes_after={"id": "int64", "amount": "float64"},
    )
    builder = ColumnLineageBuilder(nodes, edges, {"n8": snap})
    result = builder.build()

    assert result["n8"]["amount"]["state"] == STATE_TYPE_CHANGED
    assert result["n8"]["id"]["state"] == STATE_PASSTHROUGH


# ------------------------------------------------------------------
# Discovered columns
# ------------------------------------------------------------------
def test_discovered_columns_grouping():
    """Source columns from read nodes, output from write nodes."""
    nodes = [
        {"id": "n1", "category": "source", "method": "read_csv", "schema_refs": []},
        {"id": "n2", "category": "clean", "method": "dropna", "schema_refs": []},
        {"id": "n3", "category": "target", "method": "to_csv", "schema_refs": []},
    ]
    snaps = {
        "n1": _snap("n1", cols_after=["a", "b"], dtypes_after={"a": "int64", "b": "object"}),
        "n2": _snap("n2", cols_before=["a", "b"], cols_after=["a", "b"],
                     dtypes_after={"a": "int64", "b": "object"}),
        "n3": _snap("n3", cols_before=["a", "b", "c"], cols_after=["a", "b", "c"],
                     dtypes_after={"a": "int64", "b": "object", "c": "float64"}),
    }
    builder = ColumnLineageBuilder(nodes, [], snaps)
    disc = builder.get_discovered_columns()

    source_names = [c["name"] for c in disc["source"]]
    output_names = [c["name"] for c in disc["output"]]
    assert source_names == ["a", "b"]
    assert "c" in output_names


# ------------------------------------------------------------------
# Failed / not_reached nodes
# ------------------------------------------------------------------
def test_failed_node_excluded():
    """Nodes with status != completed should not appear in column lineage."""
    nodes = [{"id": "n1", "category": "source", "method": "read_csv", "schema_refs": []}]
    snap = _snap("n1", status="failed")
    builder = ColumnLineageBuilder(nodes, [], {"n1": snap})
    result = builder.build()

    assert "n1" not in result
