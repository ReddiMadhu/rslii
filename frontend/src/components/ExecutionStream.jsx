import { useEffect, useRef } from "react";
import { Terminal } from "lucide-react";
import useAnalysisStore from "../store/useAnalysisStore";

function formatTime(ts) {
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

export default function ExecutionStream() {
  const execLog = useAnalysisStore((s) => s.execLog);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [execLog.length]);

  return (
    <div
      className="w-full max-w-6xl mx-auto mb-4 rounded-xl overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
      }}
    >
      <div
        className="flex items-center gap-2 px-3 py-2 text-xs font-semibold border-b"
        style={{ borderColor: "var(--border)", color: "var(--text-primary)" }}
      >
        <Terminal size={14} style={{ color: "var(--primary)" }} />
        Live execution
        <span style={{ color: "var(--text-muted)", fontWeight: 500 }} className="ml-auto">
          SSE stream
        </span>
      </div>
      <div
        className="px-3 py-2 font-mono text-[11px] leading-relaxed overflow-y-auto max-h-44"
        style={{ color: "var(--text-secondary)", background: "var(--bg-secondary)" }}
        aria-live="polite"
      >
        {execLog.length === 0 ? (
          <span style={{ color: "var(--text-muted)" }}>Waiting for first step…</span>
        ) : (
          execLog.map((e, i) => (
            <div key={`${e.t}-${i}`} className="whitespace-pre-wrap break-all">
              <span style={{ color: "var(--text-muted)" }}>{formatTime(e.t)}</span>{" "}
              {e.text}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
