import { Sparkles } from "lucide-react";

export default function ValidationKeyAlerts({ alerts = [] }) {
  if (!alerts.length) return null;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
        <Sparkles size={14} style={{ color: "#a855f7" }} />
        Key Alerts
      </div>
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="min-w-full text-[11px]">
          <thead>
            <tr style={{ background: "var(--bg-card)" }}>
              <th className="text-left px-3 py-2 font-semibold" style={{ color: "var(--text-muted)" }}>
                Observation
              </th>
              <th className="text-left px-3 py-2 font-semibold" style={{ color: "var(--text-muted)" }}>
                Potential Impact
              </th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a, i) => (
              <tr key={i} style={{ borderTop: "1px solid var(--border)" }}>
                <td className="px-3 py-2" style={{ color: "var(--text-primary)" }}>
                  {a.observation}
                </td>
                <td className="px-3 py-2" style={{ color: "var(--text-secondary)" }}>
                  {a.impact}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
