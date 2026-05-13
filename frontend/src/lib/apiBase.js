/**
 * API origin for Azure / split hosting: SPA (e.g. Storage static site) calls App Service.
 * Set VITE_API_ORIGIN at build time (no trailing slash), e.g. https://my-api.azurewebsites.net
 */
export function getApiOrigin() {
  const raw = import.meta.env.VITE_API_ORIGIN;
  if (!raw) return "";
  return String(raw).replace(/\/$/, "");
}

/** Prefix for JSON routes: /api or https://host/api */
export function getApiBase() {
  const o = getApiOrigin();
  return o ? `${o}/api` : "/api";
}
