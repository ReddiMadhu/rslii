import { toast } from "sonner";
import { executeWithSSE } from "./sse";
import useAnalysisStore, { APP_STATES } from "../store/useAnalysisStore";

/** Shared SSE execution handler used from validation (and legacy paths). */
export function runPipelineExecution({
  pipelineCode,
  pipelineFilename,
  fileMappings,
  required,
  enableLlmForExecute,
  overrides,
  setExecuting,
  setError,
  setAppState,
  setLiveExecSummary,
}) {
  const fileMapping = {};
  const filesByFieldName = {};
  for (const s of required) {
    const f = fileMappings[s.id];
    const logical = f.name;
    fileMapping[s.id] = logical;
    filesByFieldName[`file_${logical}`] = f;
  }

  setExecuting();
  return executeWithSSE({
    code: pipelineCode,
    filename: pipelineFilename || "pipeline.py",
    enableLlm: enableLlmForExecute,
    fileMapping,
    filesByFieldName,
    overrides,
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
      st.updateNodeProgress(d.node_id, { status: "completed", metrics: d });
    },
    onNodeError: (d) => {
      const st = useAnalysisStore.getState();
      if (d?.node_id) {
        st.appendExecLog(`✗ ${d.node_id}: ${d.error || "failed"}`);
        st.updateNodeProgress(d.node_id, { status: "failed", error: d.error });
      } else {
        const msg = d?.error || "Pipeline failed";
        st.appendExecLog(`✗ ${msg}`);
        setError(msg);
        toast.error(msg);
        setAppState(APP_STATES.SOURCE_VALIDATION);
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
      const msg = e?.message || "Connection lost — retry from validation.";
      useAnalysisStore.getState().appendExecLog(`Stream error: ${msg}`);
      setError(msg);
      toast.error(msg);
      setAppState(APP_STATES.SOURCE_VALIDATION);
    },
  });
}

export function buildFixSummary(validationOverrides, validationResult) {
  const fixes = [];
  const files = validationResult?.files || {};
  Object.entries(validationOverrides || {}).forEach(([sid, ovr]) => {
    const renames = ovr.column_renames || {};
    const casts = ovr.dtype_casts || {};
    Object.entries(renames).forEach(([from, to]) => {
      fixes.push(`Missing column fix: map "${from}" → "${to}"`);
    });
    Object.entries(casts).forEach(([col, dtype]) => {
      const file = files[sid];
      const ch = file?.dtype_changes?.find((c) => c.column === col);
      const from = ch?.new_dtype || "?";
      fixes.push(`Data type change for ${col}: ${from} → ${dtype}`);
    });
  });
  return fixes;
}
