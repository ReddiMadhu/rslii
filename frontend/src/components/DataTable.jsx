import { COLUMN_COLORS } from "./LineageTab";

export default function DataTable({ data, columns, maxRows = 5, columnMeta = {} }) {
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
            {cols.map((c) => {
              const cat = columnMeta[c];
              const cc = cat ? COLUMN_COLORS[cat] : null;
              return (
                <th
                  key={c}
                  className="text-left px-2 py-1 font-semibold"
                  style={{
                    color: cc ? cc.color : "var(--text-muted)",
                    borderBottom: cc ? `2px solid ${cc.color}` : undefined,
                    background: cc ? cc.bg : undefined,
                  }}
                >
                  {c}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
              {cols.map((c) => {
                const cat = columnMeta[c];
                const cc = cat ? COLUMN_COLORS[cat] : null;
                return (
                  <td
                    key={c}
                    className="px-2 py-1 max-w-[140px] truncate"
                    style={{
                      color: "var(--text-primary)",
                      background: cc ? `${cc.color}06` : undefined,
                    }}
                  >
                    {row[c] != null ? String(row[c]) : ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
