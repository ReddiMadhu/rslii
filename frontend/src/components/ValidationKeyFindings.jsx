import { Sparkles } from "lucide-react";

export default function ValidationKeyFindings({ findings = [] }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <Sparkles size={14} style={{ color: "#a855f7" }} />
        Key Findings &amp; Potential Impact
      </div>
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="min-w-full text-[11px]">
          <thead>
            <tr style={{ background: "var(--bg-card)" }}>
              <th className="text-left px-3 py-2 font-semibold" style={{ color: "var(--text-muted)" }}>
                Finding
              </th>
              <th className="text-left px-3 py-2 font-semibold" style={{ color: "var(--text-muted)" }}>
                Impact
              </th>
            </tr>
          </thead>
          <tbody>
            {findings.length === 0 ? (
              <tr style={{ borderTop: "1px solid var(--border)" }}>
                <td
                  colSpan={2}
                  className="px-3 py-3 text-center"
                  style={{ color: "var(--text-muted)" }}
                >
                  —
                </td>
              </tr>
            ) : (
              findings.map((f, i) => (
                <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                  <td className="px-3 py-2" style={{ color: "var(--text-primary)" }}>
                    {f.finding}
                  </td>
                  <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                    {f.impact}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
