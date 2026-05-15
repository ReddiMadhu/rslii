import { AlertCircle } from "lucide-react";
import useAnalysisStore from "../store/useAnalysisStore";
import { useSourceOverrides } from "../store/validationSelectors";
import MappingOverrideSelect from "./MappingOverrideSelect";

export default function ValidationMissingColumns({
  sourceId,
  rows = [],
  additionalColumns = [],
  fuzzyNote,
  hasPreviousSnapshot,
  onSave,
  saved,
}) {
  const overrides = useSourceOverrides(sourceId);
  const setValidationOverride = useAnalysisStore((s) => s.setValidationOverride);
  const renames = overrides.column_renames;

  const additionalNames = additionalColumns.map((c) => c.name);

  return (
    <div className="space-y-2 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <AlertCircle size={14} style={{ color: "#f97316" }} />
        Missing Columns
      </div>
      {fuzzyNote && (
        <p className="text-[10px] text-yellow-500/90">
          AI matching unavailable — using fuzzy text matching
        </p>
      )}
      {!hasPreviousSnapshot && rows.length === 0 && (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No baseline yet — comparing against pipeline code expectations. Baseline is created after first
          successful execution.
        </p>
      )}
      {rows.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>No missing columns detected.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full text-[11px]">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Expected</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Type</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Line</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Mapping Override</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Pipeline change</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Impact</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const expected = row.expected_name;
                const selected =
                  Object.entries(renames).find(([, tgt]) => tgt === expected)?.[0] || "";
                const recs = row.recommendations || [];
                return (
                  <tr key={expected} style={{ borderTop: "1px solid var(--border)" }}>
                    <td className="px-2 py-2" style={{ color: "var(--text-primary)" }}>{expected}</td>
                    <td className="px-2 py-2" style={{ color: "var(--text-secondary)" }}>{row.expected_dtype}</td>
                    <td className="px-2 py-2 font-mono" style={{ color: "var(--text-muted)" }}>
                      {row.pipeline_line_number ?? "—"}
                    </td>
                    <td className="px-2 py-2">
                      <MappingOverrideSelect
                        value={selected}
                        recommendations={recs}
                        extraOptions={additionalNames}
                        onChange={(v) => {
                          Object.keys(renames).forEach((k) => {
                            if (renames[k] === expected) {
                              setValidationOverride(sourceId, "rename", k, null);
                            }
                          });
                          if (v) {
                            setValidationOverride(sourceId, "null", expected, false);
                            setValidationOverride(sourceId, "rename", v, expected);
                          } else {
                            setValidationOverride(sourceId, "null", expected, true);
                          }
                        }}
                      />
                    </td>
                    <td className="px-2 py-2 italic" style={{ color: "var(--text-muted)" }}>
                      {row.recommended_pipeline_change}
                    </td>
                    <td className="px-2 py-2" style={{ color: "var(--text-secondary)" }}>
                      {row.impact_on_target}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {rows.length > 0 && (
        <button
          type="button"
          onClick={onSave}
          className="text-xs px-3 py-1.5 rounded-lg font-medium"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--primary)" }}
        >
          {saved ? "Saved" : "Save"}
        </button>
      )}
    </div>
  );
}
