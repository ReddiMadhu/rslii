import { Columns3, Hash, AlertTriangle } from "lucide-react";

function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div
      className="flex-1 min-w-[120px] p-4 rounded-xl"
      style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
    >
      <Icon size={18} style={{ color }} className="mb-2" />
      <div className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>
        {value}
      </div>
      <div className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
        {label}
      </div>
    </div>
  );
}

export default function ValidationRowStats({ rowCount, columnCount, nullBlankColumns }) {
  return (
    <div className="flex flex-wrap gap-3">
      <StatCard icon={Hash} label="Row Count" value={rowCount ?? "—"} color="#3b82f6" />
      <StatCard icon={Columns3} label="Column Count" value={columnCount ?? "—"} color="#22c55e" />
      <StatCard
        icon={AlertTriangle}
        label="NULL/Blank Columns"
        value={nullBlankColumns ?? "—"}
        color="#ef4444"
      />
    </div>
  );
}
