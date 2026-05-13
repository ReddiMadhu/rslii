import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export default function AccordionSection({ title, icon: Icon, defaultOpen = false, children }) {
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
      </button>
      {open && <div className="px-3 pb-3 pt-0">{children}</div>}
    </div>
  );
}
