import { COLUMN_COLORS } from "./LineageTab";

export default function SchemaView({
  before,
  after,
  columnMeta = {},
  isSource = false,
  isMerge = false,
  mergeInputs = [],
  joinedColumns = [],
  joinKeys = [],
}) {
  const bcols = before || {};
  const acols = after || {};
  const afterNames = Object.keys(acols);
  const removedNames = Object.keys(bcols).filter((n) => !(n in acols));

  // Build a set for quick lookup of joined columns
  const joinedSet = new Set(joinedColumns);

  // Determine left / right legend colors
  const leftInput = mergeInputs[0] || { name: "Left", color: "#3b82f6" };
  const rightInput = mergeInputs[1] || { name: "Right", color: "#22c55e" };

  return (
    <div className="space-y-2 text-[10px]">
      {/* Merge legends — shown above the table for merge/join nodes */}
      {isMerge && mergeInputs.length >= 2 && (
        <div className="flex items-center justify-end gap-4 px-1 mb-1">
          {mergeInputs.map((input, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block"
                style={{ background: input.color }}
              />
              <span
                className="text-[10px] font-semibold"
                style={{ color: input.color }}
              >
                {input.name}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Main schema table — current (after) columns */}
      <div className="rounded-lg border border-[var(--border)] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr style={{ background: "var(--bg-primary)" }}>
              <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Column</th>
              <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Type</th>
              {/* Hide Status column for source nodes (no meaningful status) */}
              {!isSource && (
                <th className="text-left px-2 py-1.5 font-semibold" style={{ color: "var(--text-muted)" }}>Status</th>
              )}
            </tr>
          </thead>
          <tbody>
            {afterNames.map((name) => {
              const cat = columnMeta[name];
              const cc = cat ? COLUMN_COLORS[cat] : null;

              // Source nodes: no color coding at all
              if (isSource) {
                return (
                  <tr
                    key={name}
                    style={{
                      background: "transparent",
                      borderTop: "1px solid var(--border)",
                    }}
                  >
                    <td className="px-2 py-1 font-medium" style={{ color: "var(--text-primary)" }}>
                      {name}
                    </td>
                    <td className="px-2 py-1" style={{ color: "var(--text-muted)" }}>
                      {acols[name] || "—"}
                    </td>
                  </tr>
                );
              }

              // Merge nodes: tint rows by source DataFrame
              let rowBg = cc ? cc.bg : "transparent";
              let rowColor = cc ? cc.color : "var(--text-primary)";
              if (isMerge && mergeInputs.length >= 2) {
                if (joinKeys.includes(name)) {
                  // Primary key / join key: no side-specific tint
                } else if (joinedSet.has(name)) {
                  rowBg = rightInput.color + "12";
                  rowColor = rightInput.color;
                } else {
                  rowBg = leftInput.color + "12";
                  rowColor = leftInput.color;
                }
              }

              return (
                <tr
                  key={name}
                  style={{
                    background: rowBg,
                    borderTop: "1px solid var(--border)",
                  }}
                >
                  <td className="px-2 py-1 font-medium" style={{ color: isMerge ? rowColor : (cc ? cc.color : "var(--text-primary)") }}>
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
