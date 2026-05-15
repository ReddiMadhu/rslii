import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";
import { reasonLabel } from "../lib/validationUtils";

function OptionRow({ label, subtext, selected, onSelect }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full text-left px-3 py-2.5 hover:bg-[var(--bg-card-hover)] transition-colors"
      style={{
        background: selected ? "rgba(251,78,11,0.08)" : "transparent",
      }}
    >
      <div className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        {label}
      </div>
      {subtext && (
        <div className="text-[11px] mt-0.5 leading-snug" style={{ color: "var(--text-muted)" }}>
          {subtext}
        </div>
      )}
    </button>
  );
}

export default function MappingOverrideSelect({
  value,
  recommendations = [],
  extraOptions = [],
  onChange,
}) {
  const [open, setOpen] = useState(false);
  const [menuStyle, setMenuStyle] = useState({});
  const ref = useRef(null);
  const menuRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      const t = e.target;
      if (ref.current?.contains(t) || menuRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    if (!open || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const maxH = 280;
    const spaceBelow = window.innerHeight - rect.bottom - 8;
    const openUp = spaceBelow < 160 && rect.top > spaceBelow;
    setMenuStyle({
      position: "fixed",
      left: rect.left,
      width: Math.max(rect.width, 280),
      zIndex: 9999,
      ...(openUp
        ? { bottom: window.innerHeight - rect.top + 4, maxHeight: Math.min(maxH, rect.top - 8) }
        : { top: rect.bottom + 4, maxHeight: Math.min(maxH, spaceBelow) }),
    });
  }, [open]);

  const options = [
    { value: "", label: "No mapping (accept NULL)", subtext: null },
    ...recommendations.map((r) => ({
      value: r.column,
      label: r.column,
      subtext: `Confidence Score (${reasonLabel(r.reason)}): ${Math.round((r.confidence || 0) * 100)}%`,
    })),
    ...extraOptions
      .filter((n) => !recommendations.some((r) => r.column === n))
      .map((n) => ({ value: n, label: n, subtext: null })),
  ];

  const selected = options.find((o) => o.value === value) || options[0];

  const menu = open ? (
    <div
      ref={menuRef}
      className="overflow-y-auto rounded-lg shadow-xl"
      style={{
        ...menuStyle,
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
      }}
    >
      {options.map((o) => (
        <OptionRow
          key={o.value || "__none__"}
          label={o.label}
          subtext={o.subtext}
          selected={o.value === value}
          onSelect={() => {
            onChange(o.value);
            setOpen(false);
          }}
        />
      ))}
    </div>
  ) : null;

  return (
    <div ref={ref} className="relative min-w-[260px] max-w-full">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between gap-2 text-sm rounded-lg px-3 py-2.5 text-left"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          color: "var(--text-primary)",
        }}
      >
        <span className="flex flex-col min-w-0 flex-1">
          <span className="truncate font-medium">{selected?.label || "Select mapping"}</span>
          {selected?.subtext && (
            <span className="text-[11px] truncate mt-0.5" style={{ color: "var(--text-muted)" }}>
              {selected.subtext}
            </span>
          )}
        </span>
        <ChevronDown
          size={16}
          className={`shrink-0 opacity-60 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>
      {menu && createPortal(menu, document.body)}
    </div>
  );
}
