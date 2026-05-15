import { AlertCircle } from "lucide-react";
import useAnalysisStore from "../store/useAnalysisStore";
import { useSourceOverrides } from "../store/validationSelectors";

function confidenceClass(conf) {
  if (conf >= 0.8) return "text-green-400";
  if (conf >= 0.5) return "text-yellow-400";
  return "text-red-400";
}

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
    <div className="space-y-2">
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
          No previous snapshot — comparing against pipeline code expectations only.
        </p>
      )}
      {rows.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>No missing columns detected.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full text-[10px]">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Expected</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Type</th>
                <th className="text-left px-2 py-2" style={{ color: "var(--text-muted)" }}>Override</th>
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
                    <td className="px-2 py-2">
                      <select
                        className="text-[10px] rounded px-1 py-0.5 max-w-[140px]"
                        style={{ background: "var(--bg-card)", color: "var(--text-primary)", border: "1px solid var(--border)" }}
                        value={selected}
                        onChange={(e) => {
                          const v = e.target.value;
                          Object.keys(renames).forEach((k) => {
                            if (renames[k] === expected) {
                              setValidationOverride(sourceId, "rename", k, null);
                            }
                          });
                          if (v) setValidationOverride(sourceId, "rename", v, expected);
                        }}
                      >
                        <option value="">No mapping (accept NULL)</option>
                        {recs.map((r) => (
                          <option key={r.column} value={r.column}>
                            {r.column} ({Math.round((r.confidence || 0) * 100)}%)
                          </option>
                        ))}
                        {additionalNames
                          .filter((n) => !recs.some((r) => r.column === n))
                          .map((n) => (
                            <option key={n} value={n}>
                              {n}
                            </option>
                          ))}
                      </select>
                      {recs[0] && (
                        <span className={`block text-[9px] mt-0.5 ${confidenceClass(recs[0].confidence)}`}>
                          Top: {Math.round(recs[0].confidence * 100)}%
                        </span>
                      )}
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
      <button
        type="button"
        onClick={onSave}
        className="text-xs px-3 py-1.5 rounded-lg font-medium"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--primary)" }}
      >
        {saved ? "Saved" : "Save"}
      </button>
    </div>
  );
}
