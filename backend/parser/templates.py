"""Template-based NL description generator for ETL nodes."""


def generate_description(node: dict) -> str:
    """Generate a human-readable description for an ETL node using templates."""
    method = node.get("method", "")
    category = node.get("category", "")
    label = node.get("label", "")
    code = node.get("code", "")
    schema_refs = node.get("schema_refs", [])

    # ─── Source operations ───
    if category == "source":
        fmt = method.replace("read_", "").upper()
        # Extract filename from label
        parts = label.split(": ", 1)
        name = parts[1] if len(parts) > 1 else "file"
        return f"Reads data from {fmt} source: {name}"

    # ─── Target operations ───
    if category == "target":
        fmt = method.replace("to_", "").upper()
        parts = label.split(": ", 1)
        name = parts[1] if len(parts) > 1 else "destination"
        return f"Writes data to {fmt} destination: {name}"

    # ─── Filter operations ───
    if category == "filter":
        if method == "boolean_index":
            # Extract condition from label
            parts = label.split(": ", 1)
            cond = parts[1] if len(parts) > 1 else "condition"
            return f"Filters rows where {cond}"
        if method == "query":
            parts = label.split(": ", 1)
            expr = parts[1] if len(parts) > 1 else "expression"
            return f"Filters rows matching query: {expr}"
        if method == "where":
            return "Keeps rows where condition is True, replaces others with NaN"
        if method == "mask":
            return "Replaces rows where condition is True with NaN"
        if method == "sample":
            return "Selects a random sample of rows"
        return f"Filters data using {method}"

    # ─── Join operations ───
    if category == "join":
        if method == "merge":
            return label.replace("Merge", "Merges DataFrames")
        if method == "join":
            return label.replace("Join", "Joins DataFrames")
        if method == "concat":
            return "Concatenates multiple DataFrames together"
        return f"Combines data using {method}"

    # ─── Aggregation operations ───
    if category == "aggregation":
        if method == "groupby":
            parts = label.split(": ", 1)
            by = parts[1] if len(parts) > 1 else "columns"
            return f"Groups data by {by} for aggregation"
        if method == "pivot_table":
            return "Creates a pivot table summary"
        if method == "value_counts":
            return "Counts unique values in the column"
        if method in ("sum", "mean", "count", "min", "max", "std", "var", "median"):
            return f"Calculates {method} aggregation"
        return f"Aggregates data using {method}"

    # ─── Reshape operations ───
    if category == "reshape":
        if method == "melt":
            return "Unpivots DataFrame from wide to long format"
        if method == "pivot":
            return "Pivots DataFrame from long to wide format"
        if method in ("stack", "unstack"):
            return f"Reshapes DataFrame using {method}"
        if method in ("transpose", "T"):
            return "Transposes rows and columns"
        return f"Reshapes data using {method}"

    # ─── Clean operations ───
    if category == "clean":
        if method == "dropna":
            if schema_refs:
                return f"Removes rows with missing values in columns: {', '.join(schema_refs)}"
            return "Removes rows with missing values"
        if method == "fillna":
            parts = label.split("with: ", 1)
            val = parts[1] if len(parts) > 1 else "a value"
            return f"Fills missing values with {val}"
        if method == "drop_duplicates":
            return "Removes duplicate rows"
        if method == "replace":
            return "Replaces specific values in the data"
        if method == "astype":
            return "Converts column data types"
        if method == "to_datetime":
            return "Converts values to datetime format"
        if method == "to_numeric":
            return "Converts values to numeric format"
        if method in ("isna", "isnull"):
            return "Detects missing values"
        if method in ("notna", "notnull"):
            return "Detects non-missing values"
        if method == "interpolate":
            return "Fills missing values using interpolation"
        if method == "clip":
            return "Clips values to specified bounds"
        return f"Cleans data using {method}"

    # ─── Column operations ───
    if category == "column_op":
        if method == "column_assign":
            parts = label.split(": ", 1)
            col = parts[1] if len(parts) > 1 else "new column"
            return f"Creates new column: {col}"
        if method == "rename":
            return "Renames one or more columns"
        if method == "drop":
            return "Drops specified columns from the DataFrame"
        if method == "assign":
            return "Creates new columns using assign"
        return f"Modifies columns using {method}"

    # ─── Sort operations ───
    if category == "sort":
        if method == "sort_values":
            parts = label.split(": ", 1)
            by = parts[1] if len(parts) > 1 else "column"
            return f"Sorts rows by {by}"
        if method == "sort_index":
            return "Sorts by index"
        if method == "reset_index":
            return "Resets the DataFrame index"
        if method == "set_index":
            parts = label.split(": ", 1)
            col = parts[1] if len(parts) > 1 else "column"
            return f"Sets {col} as the index"
        return f"Sorts/reindexes using {method}"

    # ─── Apply operations ───
    if category == "apply":
        if method == "apply":
            if "lambda" in code:
                return "Applies a lambda transformation to the data"
            return "Applies a function to the data"
        if method == "map":
            return "Maps values using a function or dictionary"
        if method == "applymap":
            return "Applies a function element-wise"
        if method == "transform":
            return "Transforms data while preserving shape"
        if method == "pipe":
            return "Pipes DataFrame through a function"
        if method == "json_normalize":
            return "Normalizes semi-structured JSON into a flat table"
        return f"Applies transformation using {method}"

    # ─── Unknown ───
    return f"Operation: {method} (line {node.get('line_number', '?')})"


def apply_descriptions(nodes: list[dict]) -> list[dict]:
    """Apply template descriptions to all nodes."""
    for node in nodes:
        if not node.get("description"):
            node["description"] = generate_description(node)
            node["description_source"] = "template"
    return nodes
