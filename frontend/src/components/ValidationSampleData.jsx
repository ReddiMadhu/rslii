import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 6;

function isBlank(v) {
  return v == null || v === "" || (typeof v === "string" && !v.trim());
}

export default function ValidationSampleData({ sampleData = [], columns = [] }) {
  const [page, setPage] = useState(0);
  const rows = sampleData || [];
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const pageRows = rows.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);
  const colMeta = useMemo(() => {
    const m = {};
    (columns || []).forEach((c) => {
      m[c.name] = c.dtype;
    });
    return m;
  }, [columns]);
  const colNames = pageRows[0] ? Object.keys(pageRows[0]) : (columns || []).map((c) => c.name);

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        Sample Data
      </div>
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="min-w-full text-[10px]">
          <thead>
            <tr style={{ background: "var(--bg-card)" }}>
              {colNames.map((c) => (
                <th key={c} className="text-left px-2 py-2 align-bottom">
                  <div className="font-semibold" style={{ color: "var(--text-primary)" }}>
                    {c}
                  </div>
                  <div className="text-[9px] font-normal" style={{ color: "var(--text-muted)" }}>
                    {colMeta[c] || "—"}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                {colNames.map((c) => (
                  <td
                    key={c}
                    className="px-2 py-1 max-w-[120px] truncate"
                    style={{
                      color: "var(--text-primary)",
                      background: isBlank(row[c]) ? "rgba(239,68,68,0.15)" : undefined,
                    }}
                  >
                    {isBlank(row[c]) ? "NULL" : String(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > PAGE_SIZE && (
        <div className="flex items-center justify-end gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
          <button
            type="button"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="p-1 rounded disabled:opacity-30"
          >
            <ChevronLeft size={14} />
          </button>
          <span>
            {page + 1} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
            className="p-1 rounded disabled:opacity-30"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
