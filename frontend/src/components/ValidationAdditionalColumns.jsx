import { PlusCircle } from "lucide-react";

export default function ValidationAdditionalColumns({
  columns = [],
  hasPreviousSnapshot,
  onSave,
  saved,
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <PlusCircle size={14} style={{ color: "#22c55e" }} />
        Additional Columns
      </div>
      {!hasPreviousSnapshot ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No previous snapshot — this will become the baseline.
        </p>
      ) : columns.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>No additional columns vs previous upload.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="min-w-full text-[11px]">
            <thead>
              <tr style={{ background: "var(--bg-card)" }}>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Column Name</th>
                <th className="text-left px-3 py-2" style={{ color: "var(--text-muted)" }}>Column Datatype</th>
              </tr>
            </thead>
            <tbody>
              {columns.map((c) => (
                <tr key={c.name} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="px-3 py-2" style={{ color: "var(--text-primary)" }}>{c.name}</td>
                  <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>{c.dtype}</td>
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
