import { COLUMN_COLORS } from "./LineageTab";

export default function SchemaView({ before, after, columnMeta = {} }) {
  const bcols = before || {};
  const acols = after || {};
  const afterNames = Object.keys(acols);
  const removedNames = Object.keys(bcols).filter((n) => !(n in acols));

  return (
    <div className="space-y-2 text-[10px]">
      {/* Main schema table — current (after) columns */}
      <div className="rounded-lg border border-[var(--border)] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr style={{ background: "var(--bg-primary)" }}>
              <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Column</th>
              <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Type</th>
              <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {afterNames.map((name) => {
              const cat = columnMeta[name];
              const cc = cat ? COLUMN_COLORS[cat] : null;
              return (
                <tr
                  key={name}
                  style={{
                    background: cc ? cc.bg : "transparent",
                    borderTop: "1px solid var(--border)",
                  }}
                >
                  <td className="px-2 py-1 font-medium" style={{ color: cc ? cc.color : "var(--text-primary)" }}>
                    {name}
                  </td>
                  <td className="px-2 py-1" style={{ color: "var(--text-muted)" }}>
                    {acols[name] || "—"}
                  </td>
                  <td className="px-2 py-1">
                    {cc ? (
                      <span
                        className="text-[9px] px-1.5 py-0.5 rounded-full font-semibold"
                        style={{ background: cc.bg, color: cc.color, border: `1px solid ${cc.color}30` }}
                      >
                        {cc.label}
                      </span>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Removed columns sub-section */}
      {removedNames.length > 0 && (
        <div>
          <div className="text-[10px] font-semibold mb-1" style={{ color: COLUMN_COLORS.removed.color }}>
            Removed Columns
          </div>
          <div className="rounded-lg border border-[var(--border)] overflow-hidden">
            <table className="w-full">
              <tbody>
                {removedNames.map((name) => (
                  <tr
                    key={name}
                    style={{
                      background: COLUMN_COLORS.removed.bg,
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <td
                      className="px-2 py-1 font-medium"
                      style={{ color: COLUMN_COLORS.removed.color, textDecoration: "line-through" }}
                    >
                      {name}
                    </td>
                    <td className="px-2 py-1" style={{ color: "var(--text-muted)" }}>
                      {bcols[name] || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
