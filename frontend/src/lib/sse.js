import { fetchEventSource } from "@microsoft/fetch-event-source";
import { getExecuteStreamUrl } from "./executeUrl";

/**
 * POST /api/execute with multipart form; stream SSE events.
 * @returns {() => void} abort by calling returned function
 */
export function executeWithSSE({
  code,
  filename,
  enableLlm,
  fileMapping,
  filesByFieldName,
  onNodeStart,
  onNodeComplete,
  onNodeError,
  onPipelineComplete,
  onResult,
  onOpen,
  onError,
}) {
  const controller = new AbortController();
  const fd = new FormData();
  fd.append("code", code);
  fd.append("filename", filename || "pipeline.py");
  fd.append("enable_llm", enableLlm ? "true" : "false");
  fd.append("file_mapping", JSON.stringify(fileMapping || {}));
  Object.entries(filesByFieldName || {}).forEach(([field, file]) => {
    fd.append(field, file);
  });

  fetchEventSource(getExecuteStreamUrl(), {
    method: "POST",
    body: fd,
    signal: controller.signal,
    openWhenHidden: true,
    async onopen(res) {
      if (res.ok && res.headers.get("content-type")?.includes("text/event-stream")) {
        onOpen?.();
        return;
      }
      if (res.status >= 400) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
    },
    onmessage(ev) {
      const eventType = String(ev.event || "").trim();
      if (!eventType || ev.data == null || ev.data === "") return;
      let data;
      try {
        data = JSON.parse(ev.data);
      } catch (e) {
        if (eventType === "result") {
          onError?.(
            new Error(
              `Could not parse execution result (invalid JSON — often NaN/Infinity in data). ${e?.message || e}`
            )
          );
        }
        return;
      }
      switch (eventType) {
        case "node_start":
          onNodeStart?.(data);
          break;
        case "node_complete":
          onNodeComplete?.(data);
          break;
        case "node_error":
          onNodeError?.(data);
          break;
        case "pipeline_complete":
          onPipelineComplete?.(data);
          break;
        case "result":
          onResult?.(data);
          break;
        default:
          break;
      }
    },
    onerror(err) {
      if (controller.signal.aborted || err?.name === "AbortError") return;
      onError?.(err);
      throw err;
    },
  }).catch((e) => {
    if (controller.signal.aborted) return;
    onError?.(e);
  });

  return () => controller.abort();
}
