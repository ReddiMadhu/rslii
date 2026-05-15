import { ChevronDown, FileCheck, AlertCircle } from "lucide-react";
import { cn } from "../lib/utils";
import { fileNeedsAction } from "../lib/validationUtils";

export default function ValidationSidebar({
  fileEntries = [],
  selectedSourceId,
  onSelectSource,
  overrides,
}) {
  return (
    <aside
      className="w-56 shrink-0 flex flex-col gap-2"
      style={{ minHeight: "min(70vh, 640px)" }}
    >
      <p className="text-[10px] font-bold uppercase tracking-wide px-1" style={{ color: "var(--text-muted)" }}>
        Uploaded files
      </p>
      <div className="flex flex-col gap-1 overflow-y-auto pr-1">
        {fileEntries.map(([sourceId, data]) => {
          const needsAction = fileNeedsAction(data, overrides[sourceId]);
          const active = sourceId === selectedSourceId;
          const open = active;

          return (
            <details
              key={sourceId}
              open={open}
              className="group rounded-xl overflow-hidden"
              style={{
                background: "var(--bg-card)",
                border: active
                  ? "1px solid rgba(251,78,11,0.45)"
                  : "1px solid var(--border)",
              }}
            >
              <summary
                className={cn(
                  "cursor-pointer list-none flex items-center gap-2 px-3 py-2.5 text-xs font-medium",
                  "[&::-webkit-details-marker]:hidden"
                )}
                style={{ color: "var(--text-primary)" }}
                onClick={() => onSelectSource(sourceId)}
              >
                <FileCheck
                  size={14}
                  className="shrink-0"
                  style={{ color: needsAction ? "#ef4444" : "var(--primary)" }}
                />
                <span className="truncate flex-1 text-left">{data.filename || sourceId}</span>
                {needsAction && <AlertCircle size={12} className="shrink-0 text-red-400" />}
                <ChevronDown
                  size={14}
                  className="shrink-0 opacity-50 transition-transform group-open:rotate-180"
                />
              </summary>
              <div
                className="px-3 pb-3 pt-0 space-y-1.5 text-[10px]"
                style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border)" }}
              >
                <p style={{ color: "var(--text-secondary)" }}>
                  {data.row_count} rows · {data.column_count} columns
                </p>
                <span
                  className="inline-block px-2 py-0.5 rounded-full text-[9px] font-semibold"
                  style={{
                    background: data.has_previous_snapshot
                      ? "rgba(34,197,94,0.12)"
                      : "rgba(234,179,8,0.12)",
                    color: data.has_previous_snapshot ? "#22c55e" : "#eab308",
                  }}
                >
                  {data.has_previous_snapshot ? "Baseline established" : "No baseline yet"}
                </span>
                {needsAction && (
                  <p className="text-red-400 font-medium">Action required</p>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </aside>
  );
}
