/** Stable fallbacks and default override builders (no React / store imports). */
export const EMPTY_SOURCE_OVERRIDES = Object.freeze({
  column_renames: Object.freeze({}),
  dtype_casts: Object.freeze({}),
  null_columns: Object.freeze([]),
});

export function buildDefaultOverridesFromValidation(validationResult) {
  const overrides = {};
  for (const [sourceId, data] of Object.entries(validationResult?.files || {})) {
    const dtype_casts = {};
    for (const ch of data.dtype_changes || []) {
      if (ch.column && ch.expected_dtype) {
        dtype_casts[ch.column] = ch.expected_dtype;
      }
    }
    const null_columns = (data.missing_columns || [])
      .map((row) => row.expected_name)
      .filter(Boolean);
    if (null_columns.length > 0 || Object.keys(dtype_casts).length > 0) {
      overrides[sourceId] = { column_renames: {}, dtype_casts, null_columns };
    }
  }
  return overrides;
}
