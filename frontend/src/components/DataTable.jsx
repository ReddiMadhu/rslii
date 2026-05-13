export default function DataTable({ data, columns, maxRows = 5 }) {
  const rows = Array.isArray(data) ? data.slice(0, maxRows) : [];
  const cols =
    columns ||
    (rows[0] ? Object.keys(rows[0]) : []);

  if (!cols.length) {
    return <p className="text-xs" style={{ color: "var(--text-muted)" }}>No rows</p>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
      <table className="min-w-full text-[10px]">
        <thead>
          <tr style={{ background: "var(--bg-card)" }}>
            {cols.map((c) => (
              <th key={c} className="text-left px-2 py-1 font-semibold" style={{ color: "var(--text-muted)" }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
              {cols.map((c) => (
                <td key={c} className="px-2 py-1 max-w-[140px] truncate" style={{ color: "var(--text-primary)" }}>
                  {row[c] != null ? String(row[c]) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
