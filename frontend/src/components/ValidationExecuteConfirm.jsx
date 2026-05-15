import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";

export default function ValidationExecuteConfirm({ fixes = [], onCancel, onConfirm }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!fixes.length) return;
    setStep(0);
    const id = setInterval(() => {
      setStep((s) => (s < fixes.length - 1 ? s + 1 : s));
    }, 400);
    return () => clearInterval(id);
  }, [fixes]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.6)" }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-6 space-y-4"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
          Confirm pipeline execution
        </h3>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          The following fixes will be applied:
        </p>
        <ul className="space-y-2 text-xs max-h-48 overflow-y-auto">
          {fixes.map((f, i) => (
            <li
              key={i}
              className="flex items-start gap-2"
              style={{
                color: i <= step ? "var(--text-primary)" : "var(--text-muted)",
                opacity: i <= step ? 1 : 0.5,
              }}
            >
              <Check size={14} className="shrink-0 mt-0.5 text-green-500" />
              {f}
            </li>
          ))}
        </ul>
        {fixes.length === 0 && (
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>No overrides — run pipeline as-is.</p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-1 px-4 py-2 rounded-xl text-xs font-semibold"
            style={{ border: "1px solid var(--border)", color: "var(--text-secondary)" }}
          >
            <X size={14} />
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white"
            style={{ background: "linear-gradient(135deg, var(--primary), var(--primary-dark))" }}
          >
            Confirm &amp; Execute
          </button>
        </div>
      </div>
    </div>
  );
}
