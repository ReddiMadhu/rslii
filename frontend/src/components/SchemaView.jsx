export default function SchemaView({ before, after }) {
  const bcols = before || {};
  const acols = after || {};
  const names = new Set([...Object.keys(bcols), ...Object.keys(acols)]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[10px]">
      <div>
        <div className="font-semibold mb-1" style={{ color: "var(--text-muted)" }}>Before</div>
        <SchemaTable cols={bcols} names={names} mode="before" other={acols} />
      </div>
      <div>
        <div className="font-semibold mb-1" style={{ color: "var(--text-muted)" }}>After</div>
        <SchemaTable cols={acols} names={names} mode="after" other={bcols} />
      </div>
    </div>
  );
}

function SchemaTable({ cols, names, mode, other }) {
  const list = [...names].sort();
  return (
    <div className="rounded-lg border border-[var(--border)] overflow-hidden">
      <table className="w-full">
        <tbody>
          {list.map((name) => {
            const t = cols[name];
            const o = other[name];
            let bg = "transparent";
            if (mode === "after" && t && !o) bg = "rgba(34,197,94,0.12)";
            if (mode === "before" && t && !other[name]) bg = "rgba(239,68,68,0.12)";
            if (t && o && t !== o) bg = "rgba(234,179,8,0.15)";
            return (
              <tr key={name} style={{ background: bg }}>
                <td className="px-2 py-1 font-medium" style={{ color: "var(--text-primary)" }}>{name}</td>
                <td className="px-2 py-1" style={{ color: "var(--text-muted)" }}>{t || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
