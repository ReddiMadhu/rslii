/** Shared validation UI helpers */

/** Show Key Findings / Key Alerts when schema drift includes missing columns or dtype changes. */
export function showSchemaDriftInsights(data) {
  if (!data) return false;
  const missing = data.missing_columns || [];
  const dtype = data.dtype_changes || [];
  return missing.length > 0 || dtype.length > 0;
}

export function reasonLabel(reason) {
  const r = (reason || "").toLowerCase();
  if (r.includes("exact")) return "Exact match";
  if (r.includes("llm")) return "LLM semantic match";
  if (r.includes("semantic rename")) return "Semantic rename";
  if (r.includes("fuzzy")) return "Fuzzy match";
  return "Match";
}

export function fileNeedsAction(data, overrides) {
  if (!data) return false;
  const missing = data.missing_columns || [];
  const additional = data.additional_columns || [];
  const dtype = data.dtype_changes || [];
  if (missing.length > 0 || additional.length > 0) return true;
  if (data.has_previous_snapshot && dtype.length > 0) return true;

  const renames = overrides?.column_renames || {};
  for (const row of missing) {
    const expected = row.expected_name;
    const mapped = Object.entries(renames).find(([, tgt]) => tgt === expected);
    if (!mapped) return true;
  }
  return false;
}

export function sectionNeedsAction(type, data, overrides) {
  if (!data) return false;
  if (type === "missing") {
    const rows = data.missing_columns || [];
    if (rows.length === 0) return false;
    const renames = overrides?.column_renames || {};
    return rows.some((row) => {
      const expected = row.expected_name;
      return !Object.entries(renames).some(([, tgt]) => tgt === expected);
    });
  }
  if (type === "additional") return (data.additional_columns || []).length > 0;
  if (type === "dtype") {
    return data.has_previous_snapshot && (data.dtype_changes || []).length > 0;
  }
  return false;
}
