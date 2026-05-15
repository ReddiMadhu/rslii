import { PlusCircle } from "lucide-react";

export default function ValidationAdditionalColumns({
  columns = [],
  hasPreviousSnapshot,
}) {
  return (
    <div className="space-y-2 p-3">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <PlusCircle size={14} style={{ color: "#22c55e" }} />
        New Columns
      </div>
      {!hasPreviousSnapshot ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          No baseline yet — baseline is created after first successful execution.
        </p>
      ) : columns.length === 0 ? (
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>No new columns vs baseline.</p>
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
    </div>
  );
}
