import { useState } from "react";
import useAnalysisStore from "../store/useAnalysisStore";
import { ShieldCheck, ShieldAlert, Shield, HelpCircle } from "lucide-react";

export default function RiskBadge() {
  const parseResult = useAnalysisStore((s) => s.parseResult);
  const [showTooltip, setShowTooltip] = useState(false);

  if (!parseResult || !parseResult.risk) return null;

  const { level, reasons, blocked } = parseResult.risk;

  let badgeColor = "bg-[rgba(34,197,94,0.08)] border-[#22c55e] text-[#22c55e]";
  let icon = <ShieldCheck size={10} />;
  let label = "Low Risk";

  if (level === "medium") {
    badgeColor = "bg-[rgba(234,179,8,0.08)] border-[#eab308] text-[#eab308]";
    icon = <Shield size={10} />;
    label = "Medium Risk";
  } else if (level === "high") {
    badgeColor = "bg-[rgba(239,68,68,0.08)] border-[#ef4444] text-[#ef4444]";
    icon = <ShieldAlert size={10} />;
    label = blocked ? "Blocked (High Risk)" : "High Risk";
  }

  return (
    <div 
      className="relative"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div 
        className={`flex items-center gap-1.5 px-2 py-0.5 rounded-lg border text-[9px] font-semibold select-none cursor-help transition-all ${badgeColor}`}
      >
        {icon}
        <span>{label}</span>
      </div>

      {showTooltip && (
        <div className="absolute right-0 mt-2 w-64 p-3.5 rounded-xl bg-[#0f0f16] border border-[rgba(255,255,255,0.08)] shadow-2xl z-50 text-xs text-[var(--text-secondary)] animate-fade-in leading-relaxed">
          <div className="font-bold text-white mb-1.5 flex items-center gap-1">
            <HelpCircle size={12} className="text-[#fb4e0b]" />
            Risk Classification Details
          </div>
          {reasons && reasons.length > 0 ? (
            <ul className="list-disc pl-4 space-y-1">
              {reasons.map((r, idx) => (
                <li key={idx} className="marker:text-[#fb4e0b]">{r}</li>
              ))}
            </ul>
          ) : (
            <p>No security concerns detected. The ETL script is safe to execute.</p>
          )}
        </div>
      )}
    </div>
  );
}
