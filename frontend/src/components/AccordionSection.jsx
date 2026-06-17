import { useState } from "react";
import { ChevronDown, ChevronRight, Info } from "lucide-react";

export default function AccordionSection({ title, icon: Icon, defaultOpen = false, hasData = false, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-[var(--border)] overflow-hidden mb-2" style={{ background: "var(--bg-secondary)" }}>
      <button
        type="button"
        className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs font-semibold"
        style={{ color: "var(--text-primary)" }}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {Icon && <Icon size={14} style={{ color: "var(--primary)" }} />}
        {title}
        {!open && hasData && (
          <span
            className="flex items-center gap-1 shrink-0"
            title="This section has data — click to expand"
          >
            <Info
              size={13}
              className="animate-pulse"
              style={{ color: "var(--primary)", opacity: 0.85 }}
            />
          </span>
        )}
      </button>
      {open && <div className="px-3 pb-3 pt-0">{children}</div>}
    </div>
  );
}
