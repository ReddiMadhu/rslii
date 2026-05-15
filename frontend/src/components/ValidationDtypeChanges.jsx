import { ArrowRightLeft } from "lucide-react";
import useAnalysisStore from "../store/useAnalysisStore";
import { useSourceOverrides } from "../store/validationSelectors";

const DTYPE_OPTIONS = ["object", "int64", "float64", "bool", "string", "numeric"];

export default function ValidationDtypeChanges({
  sourceId,
  changes = [],
  hasPreviousSnapshot,
  onSave,
  saved,
}) {
  const overrides = useSourceOverrides(sourceId);
  const casts = overrides.dtype_casts;
  const setValidationOverride = useAnalysisStore((s) => s.setValidationOverride);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <ArrowRightLeft size={14} style={{ color: "#a855f7" }} />
        Data Type Changes
      </div>
      {!hasPreviousSnapshot ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No previous snapshot — this will become the baseline.
        </p>
      ) : changes.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>No dtype changes vs previous upload.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full text-[11px]">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Column</th>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Previous</th>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>New</th>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Cast to</th>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Recommended change</th>
              </tr>
            </thead>
            <tbody>
              {changes.map((ch) => (
                <tr key={ch.column} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="px-3 py-2" style={{ color: "var(--text-primary)" }}>{ch.column}</td>
                  <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>{ch.expected_dtype}</td>
                  <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>{ch.new_dtype}</td>
                  <td className="px-3 py-2">
                    <select
                      className="text-[10px] rounded px-1 py-0.5"
                      style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }}
                      value={casts[ch.column] || ch.expected_dtype}
                      onChange={(e) =>
                        setValidationOverride(sourceId, "dtype", ch.column, e.target.value)
                      }
                    >
                      {DTYPE_OPTIONS.map((d) => (
                        <option key={d} value={d}>
                          {d}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2 italic" style={{ color: "var(--text-muted)" }}>
                    {ch.recommended_change}
                  </td>
                </tr>
              ))}
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
