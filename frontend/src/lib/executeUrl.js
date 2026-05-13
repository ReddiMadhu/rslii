/**
 * URL for POST /api/execute (SSE).
 * In dev, call the FastAPI server directly so the Vite proxy does not buffer
 * the event stream; in prod use same-origin /api/execute.
 */
export function getExecuteStreamUrl() {
  const envBase = import.meta.env.VITE_API_ORIGIN;
  if (envBase) {
    return `${String(envBase).replace(/\/$/, "")}/api/execute`;
  }
  if (import.meta.env.DEV && typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000/api/execute`;
  }
  return "/api/execute";
}
