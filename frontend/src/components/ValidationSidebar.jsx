import { ChevronDown, FileCheck, AlertCircle, Database } from "lucide-react";
import { cn } from "../lib/utils";
import { fileNeedsAction } from "../lib/validationUtils";

export default function ValidationSidebar({
  fileEntries = [],
  selectedSourceId,
  onSelectSource,
  overrides,
  selectedData,
}) {
  const baselineCols = selectedData?.baseline_columns;
  const baselineCount = selectedData?.baseline_column_count;

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

      {/* ── Baseline Schema Table ── */}
      <div className="mt-3">
        <div className="flex items-center gap-1.5 px-1 mb-1.5">
          <Database size={11} style={{ color: "var(--primary)" }} />
          <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>
            Baseline Schema
          </p>
          {baselineCount != null && (
            <span
              className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full ml-auto"
              style={{ background: "rgba(34,197,94,0.12)", color: "#22c55e" }}
            >
              {baselineCount} cols
            </span>
          )}
        </div>

        {!baselineCols ? (
          <div
            className="px-3 py-3 rounded-xl text-[10px] text-center"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
            }}
          >
            No baseline established yet
          </div>
        ) : baselineCols.length === 0 ? (
          <div
            className="px-3 py-3 rounded-xl text-[10px] text-center"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
            }}
          >
            Baseline has no columns
          </div>
        ) : (
          <div
            className="rounded-xl overflow-hidden"
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
            }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]" style={{ minWidth: 180 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th
                      className="text-left px-2.5 py-1.5 font-semibold"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Column
                    </th>
                    <th
                      className="text-left px-2.5 py-1.5 font-semibold"
                      style={{ color: "var(--text-muted)" }}
                    >
                      Type
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {baselineCols.map((col, i) => (
                    <tr
                      key={col.name}
                      style={{
                        borderBottom:
                          i < baselineCols.length - 1
                            ? "1px solid var(--border)"
                            : "none",
                      }}
                    >
                      <td
                        className="px-2.5 py-1.5 font-medium truncate"
                        style={{ color: "var(--text-primary)", maxWidth: 110 }}
                        title={col.name}
                      >
                        {col.name}
                      </td>
                      <td
                        className="px-2.5 py-1.5"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        <span
                          className="inline-block px-1.5 py-0.5 rounded text-[9px] font-medium"
                          style={{
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border)",
                          }}
                        >
                          {col.dtype}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
