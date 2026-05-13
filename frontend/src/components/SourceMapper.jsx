import { useCallback, useMemo } from "react";
import { useDropzone } from "react-dropzone";
import { Database, AlertCircle, ArrowLeft, Play, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { cn } from "../lib/utils";
import useAnalysisStore, { APP_STATES } from "../store/useAnalysisStore";
import { executeWithSSE } from "../lib/sse";

const EXT_BY_FORMAT = {
  csv: [".csv", ".tsv", ".txt"],
  excel: [".xlsx", ".xls"],
  parquet: [".parquet", ".pq"],
  json: [".json"],
  html: [".html", ".htm"],
  xml: [".xml"],
  feather: [".feather"],
  orc: [".orc"],
  stata: [".dta"],
  pickle: [".pkl", ".pickle"],
};

function extOk(format, filename) {
  const ext = (filename || "").toLowerCase().slice(filename.lastIndexOf("."));
  const allowed = EXT_BY_FORMAT[format];
  if (!allowed || allowed.length === 0) return true;
  return allowed.includes(ext);
}

export default function SourceMapper({ llmAvailable = false }) {
  const parseResult = useAnalysisStore((s) => s.parseResult);
  const pipelineCode = useAnalysisStore((s) => s.pipelineCode);
  const pipelineFilename = useAnalysisStore((s) => s.pipelineFilename);
  const fileMappings = useAnalysisStore((s) => s.fileMappings);
  const setFileMapping = useAnalysisStore((s) => s.setFileMapping);
  const clearFileMapping = useAnalysisStore((s) => s.clearFileMapping);
  const setEnableLlmForExecute = useAnalysisStore((s) => s.setEnableLlmForExecute);
  const enableLlmForExecute = useAnalysisStore((s) => s.enableLlmForExecute);
  const setLiveExecSummary = useAnalysisStore((s) => s.setLiveExecSummary);
  const setAppState = useAnalysisStore((s) => s.setAppState);
  const setExecuting = useAnalysisStore((s) => s.setExecuting);
  const setError = useAnalysisStore((s) => s.setError);

  const sources = parseResult?.sources || [];
  const required = useMemo(
    () => sources.filter((s) => s.requires_upload),
    [sources]
  );
  const ready = useMemo(
    () => required.every((s) => fileMappings[s.id]),
    [required, fileMappings]
  );

  const handleExecute = useCallback(() => {
    if (!ready || !pipelineCode) return;
    const fileMapping = {};
    const filesByFieldName = {};
    for (const s of required) {
      const f = fileMappings[s.id];
      const logical = f.name;
      fileMapping[s.id] = logical;
      filesByFieldName[`file_${logical}`] = f;
    }
    setExecuting();
    executeWithSSE({
      code: pipelineCode,
      filename: pipelineFilename || "pipeline.py",
      enableLlm: enableLlmForExecute,
      fileMapping,
      filesByFieldName,
      onOpen: () => {
        useAnalysisStore.getState().appendExecLog("Stream connected — running pipeline…");
      },
      onNodeStart: (d) => {
        if (!d?.node_id) return;
        const st = useAnalysisStore.getState();
        const label = d.label ? String(d.label) : d.node_id;
        const idx = d.index != null && d.total != null ? `[${d.index}/${d.total}] ` : "";
        st.appendExecLog(`▶ ${idx}${label} (${d.node_id})`);
        st.updateNodeProgress(d.node_id, { status: "executing" });
      },
      onNodeComplete: (d) => {
        if (!d?.node_id) return;
        const st = useAnalysisStore.getState();
        const ms = d.duration_ms != null ? `${Number(d.duration_ms).toFixed(1)}ms` : "?";
        const rowPart =
          d.rows_in != null || d.rows_out != null
            ? `  rows ${d.rows_in ?? "?"}→${d.rows_out ?? "?"}`
            : "";
        st.appendExecLog(`✓ ${d.node_id}  ${ms}${rowPart}`);
        st.updateNodeProgress(d.node_id, {
          status: "completed",
          metrics: d,
        });
      },
      onNodeError: (d) => {
        const st = useAnalysisStore.getState();
        if (d?.node_id) {
          st.appendExecLog(`✗ ${d.node_id}: ${d.error || "failed"}`);
          st.updateNodeProgress(d.node_id, {
            status: "failed",
            error: d.error,
          });
        } else {
          const msg = d?.error || "Pipeline failed";
          st.appendExecLog(`✗ ${msg}`);
          setError(msg);
          toast.error(msg);
          setAppState(APP_STATES.SOURCE_MAPPING);
        }
      },
      onPipelineComplete: (d) => {
        const st = useAnalysisStore.getState();
        const ms = d?.total_duration_ms != null ? `${Number(d.total_duration_ms).toFixed(1)}ms total` : "";
        const counts = [
          d?.nodes_completed != null ? `${d.nodes_completed} completed` : "",
          d?.nodes_failed != null && d.nodes_failed > 0 ? `${d.nodes_failed} failed` : "",
        ]
          .filter(Boolean)
          .join(", ");
        st.appendExecLog(`Pipeline finished${ms ? ` — ${ms}` : ""}${counts ? ` (${counts})` : ""}`);
        setLiveExecSummary({
          total_duration_ms: d?.total_duration_ms,
          nodes_completed: d?.nodes_completed,
          nodes_failed: d?.nodes_failed,
          nodes_skipped: d?.nodes_skipped,
          status: (d?.nodes_failed ?? 0) > 0 ? "partial" : "completed",
        });
      },
      onResult: (data) => {
        useAnalysisStore.getState().appendExecLog("Result received — loading summary…");
        useAnalysisStore.getState().setResult(data);
      },
      onError: (e) => {
        console.error(e);
        const msg = e?.message || "Connection lost — retry from the mapping step.";
        useAnalysisStore.getState().appendExecLog(`Stream error: ${msg}`);
        setError(msg);
        toast.error(msg);
        setAppState(APP_STATES.SOURCE_MAPPING);
      },
    });
  }, [
    ready,
    pipelineCode,
    pipelineFilename,
    required,
    fileMappings,
    enableLlmForExecute,
    setExecuting,
    setError,
    setAppState,
    setLiveExecSummary,
  ]);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div
        className="p-5 rounded-2xl"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
            Map data files
          </h2>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {parseResult?.summary?.total_nodes ?? 0} operations
          </span>
        </div>
        <p className="text-xs mb-4" style={{ color: "var(--text-muted)" }}>
          Drop a file for each required source. The multipart field name must be{" "}
          <code className="text-[10px]">file_&lt;filename&gt;</code> matching the chosen file name.
        </p>

        <div className="space-y-4">
          {sources.map((s) => (
            <SourceSlot key={s.id} source={s} />
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setAppState(APP_STATES.UPLOAD_SCRIPT)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
          }}
        >
          <ArrowLeft size={16} />
          Back
        </button>
        <div className="flex items-center gap-3">
          {llmAvailable && (
            <button
              type="button"
              onClick={() => setEnableLlmForExecute(!enableLlmForExecute)}
              className={cn(
                "flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium",
                enableLlmForExecute ? "ring-1 ring-purple-500/40" : ""
              )}
              style={{
                background: enableLlmForExecute ? "rgba(168,85,247,0.12)" : "var(--bg-card)",
                border: "1px solid var(--border)",
                color: enableLlmForExecute ? "#a855f7" : "var(--text-muted)",
              }}
            >
              <Sparkles size={14} />
              AI Enhance
            </button>
          )}
          <button
            type="button"
            disabled={!ready}
            onClick={handleExecute}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-bold text-white disabled:opacity-40"
            style={{
              background: "linear-gradient(135deg, var(--primary), var(--primary-dark))",
            }}
          >
            <Play size={16} />
            Execute Pipeline
          </button>
        </div>
      </div>
    </div>
  );
}

function SourceSlot({ source }) {
  const fileMappings = useAnalysisStore((s) => s.fileMappings);
  const setFileMapping = useAnalysisStore((s) => s.setFileMapping);
  const clearFileMapping = useAnalysisStore((s) => s.clearFileMapping);
  const mapped = fileMappings[source.id];
  const [fmtLabel, fmtClass] = formatBadge(source.format);

  const onDrop = useCallback(
    (accepted) => {
      const f = accepted[0];
      if (!f) return;
      if (source.requires_upload && !extOk(source.format, f.name)) {
        return;
      }
      setFileMapping(source.id, f);
    },
    [source, setFileMapping]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: !source.requires_upload,
  });

  if (!source.requires_upload) {
    return (
      <div
        className="p-3 rounded-xl text-xs flex items-start gap-2"
        style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
      >
        <Database size={14} className="shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold" style={{ color: "var(--text-primary)" }}>
            {source.method} — {fmtLabel}
          </div>
          <div style={{ color: "var(--text-muted)" }}>
            {source.skip_reason || "No file upload required"}
          </div>
        </div>
      </div>
    );
  }

  const badExt = mapped && !extOk(source.format, mapped.name);

  return (
    <div
      className="p-4 rounded-xl space-y-2"
      style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2">
        <span
          className="text-[10px] font-bold uppercase px-2 py-0.5 rounded"
          style={{ background: `${fmtClass}22`, color: fmtClass }}
        >
          {source.format}
        </span>
        <span className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>
          {source.filename || source.path || "file"}
        </span>
        <span className="text-[10px] ml-auto" style={{ color: "var(--text-muted)" }}>
          line {source.line}
        </span>
      </div>
      <div
        {...getRootProps()}
        className={cn(
          "border border-dashed rounded-lg p-4 text-center text-xs cursor-pointer transition-colors",
          isDragActive ? "border-[var(--primary)]" : "border-[var(--border)]",
          badExt ? "border-red-500/60" : ""
        )}
        style={{ color: "var(--text-muted)" }}
      >
        <input {...getInputProps()} />
        {mapped ? (
          <div className="flex items-center justify-center gap-2">
            <span style={{ color: "var(--text-primary)" }}>{mapped.name}</span>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                clearFileMapping(source.id);
              }}
            >
              Remove
            </button>
          </div>
        ) : (
          <>Drop {source.format.toUpperCase()} file here</>
        )}
      </div>
      {badExt && (
        <div className="flex items-center gap-1 text-xs text-red-400">
          <AlertCircle size={12} />
          Extension does not match expected format
        </div>
      )}
    </div>
  );
}

function formatBadge(format) {
  const f = (format || "unknown").toLowerCase();
  const map = {
    csv: ["CSV", "#3b82f6"],
    excel: ["Excel", "#22c55e"],
    parquet: ["Parquet", "#a855f7"],
    json: ["JSON", "#eab308"],
  };
  return map[f] || [f, "#64748b"];
}
