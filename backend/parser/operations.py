"""Operation detection registry — maps pandas methods to categories."""

from __future__ import annotations

import os.path

# ─── v2: read method → logical format (parse / upload validation) ───

FORMAT_MAP: dict[str, str] = {
    "read_csv": "csv",
    "read_excel": "excel",
    "read_parquet": "parquet",
    "read_json": "json",
    "read_html": "html",
    "read_xml": "xml",
    "read_sql": "sql",
    "read_sql_table": "sql",
    "read_sql_query": "sql",
    "read_feather": "feather",
    "read_orc": "orc",
    "read_stata": "stata",
    "read_pickle": "pickle",
    "read_clipboard": "clipboard",
    "DataFrame": "inline",
}

# Expected file extensions per format (lowercase, with dot)
ACCEPTED_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "csv": (".csv", ".tsv", ".txt"),
    "excel": (".xlsx", ".xls"),
    "parquet": (".parquet", ".pq"),
    "json": (".json",),
    "html": (".html", ".htm"),
    "xml": (".xml",),
    "feather": (".feather",),
    "orc": (".orc",),
    "stata": (".dta",),
    "pickle": (".pkl", ".pickle"),
    "sql": (),  # external / non-file
    "clipboard": (),
    "inline": (),
}

# Sources that cannot be satisfied with an uploaded file in v2 MVP
EXTERNAL_READ_METHODS = frozenset({
    "read_sql", "read_sql_table", "read_sql_query", "read_clipboard",
})

# ─── Category Definitions ───

CATEGORIES = {
    "source":      {"color": "#3b82f6", "icon": "database",       "label": "Source"},
    "target":      {"color": "#22c55e", "icon": "hard-drive",     "label": "Target"},
    "filter":      {"color": "#eab308", "icon": "filter",         "label": "Filter"},
    "join":        {"color": "#f97316", "icon": "git-merge",      "label": "Join"},
    "aggregation": {"color": "#a855f7", "icon": "bar-chart-2",    "label": "Aggregation"},
    "reshape":     {"color": "#ef4444", "icon": "shuffle",        "label": "Reshape"},
    "clean":       {"color": "#14b8a6", "icon": "sparkles",       "label": "Clean"},
    "column_op":   {"color": "#64748b", "icon": "columns",        "label": "Column Op"},
    "sort":        {"color": "#92400e", "icon": "arrow-up-down",  "label": "Sort"},
    "apply":       {"color": "#ec4899", "icon": "zap",            "label": "Apply/Map"},
    "unknown":     {"color": "#6b7280", "icon": "help-circle",    "label": "Unknown"},
}


# ─── Read Operations ───

READ_OPS = {
    "read_csv", "read_excel", "read_sql", "read_sql_table", "read_sql_query",
    "read_parquet", "read_json", "read_html", "read_clipboard", "read_fwf",
    "read_orc", "read_sas", "read_spss", "read_feather", "read_hdf",
    "read_pickle", "read_xml", "read_stata",
}

# ─── Write Operations ───

WRITE_OPS = {
    "to_csv", "to_sql", "to_parquet", "to_excel", "to_json", "to_html",
    "to_pickle", "to_feather", "to_hdf", "to_xml", "to_stata", "to_orc",
}

# ─── Transform Operations ───

FILTER_OPS = {"query", "where", "mask", "sample"}  # boolean indexing handled separately
JOIN_OPS = {"merge", "join", "concat"}
AGG_OPS = {"groupby", "agg", "aggregate", "sum", "mean", "count", "min", "max",
           "std", "var", "median", "pivot_table", "value_counts", "cumsum", "cumprod"}
RESHAPE_OPS = {"melt", "pivot", "stack", "unstack", "transpose", "T"}
CLEAN_OPS = {"dropna", "fillna", "drop_duplicates", "replace", "astype",
             "to_datetime", "to_numeric", "isna", "isnull", "notna", "notnull",
             "interpolate", "clip"}
COLUMN_OPS = {"rename", "drop", "assign", "reindex", "insert"}
SORT_OPS = {"sort_values", "sort_index", "reset_index", "set_index"}
APPLY_OPS = {"apply", "map", "applymap", "transform", "pipe", "json_normalize"}

# Special subscript methods (e.g., .loc[], .iloc[])
SUBSCRIPT_FILTER_ATTRS = {"loc", "iloc", "at", "iat"}
# String accessor — treated as clean
STR_ACCESSOR = "str"


def classify_method(method_name: str) -> tuple[str, str]:
    """
    Classify a method name into (category, type).
    Returns (category_key, type_string).
    """
    # Inline structured source (pd.DataFrame(...)) — no file upload
    if method_name == "DataFrame":
        return "source", "inline"
    if method_name in READ_OPS:
        return "source", "read"
    if method_name in WRITE_OPS:
        return "target", "write"
    if method_name in FILTER_OPS:
        return "filter", "filter"
    if method_name in JOIN_OPS:
        return "join", "join"
    if method_name in AGG_OPS:
        return "aggregation", "aggregation"
    if method_name in RESHAPE_OPS:
        return "reshape", "reshape"
    if method_name in CLEAN_OPS:
        return "clean", "clean"
    if method_name in COLUMN_OPS:
        return "column_op", "column_op"
    if method_name in SORT_OPS:
        return "sort", "sort"
    if method_name in APPLY_OPS:
        return "apply", "apply"
    return "unknown", "unknown"


def get_category_info(category: str) -> dict:
    """Get display info for a category."""
    return CATEGORIES.get(category, CATEGORIES["unknown"])


def validate_upload_extension(format_key: str, filename: str) -> tuple[bool, str]:
    """
    Return (ok, error_message). Used by /api/execute (Phase 3) and can be
    mirrored on the client for Phase 4.
    """
    allowed = ACCEPTED_EXTENSIONS.get(format_key)
    if not allowed:
        return True, ""
    ext = os.path.splitext(filename.lower())[1]
    if ext in allowed:
        return True, ""
    expect = ", ".join(allowed) if allowed else format_key
    return False, f"Expected {format_key} ({expect}), got {ext or 'no extension'}"
