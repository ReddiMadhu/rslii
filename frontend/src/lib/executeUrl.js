import { getApiOrigin } from "./apiBase";

/**
 * URL for POST /api/execute (SSE).
 * Production split-host: VITE_API_ORIGIN (see apiBase.js).
 * Dev: bypass Vite proxy to reduce SSE buffering (direct :8000).
 */
export function getExecuteStreamUrl() {
  const o = getApiOrigin();
  if (o) {
    return `${o}/api/execute`;
  }
  if (import.meta.env.DEV && typeof window !== "undefined") {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000/api/execute`;
  }
  return "/api/execute";
}
