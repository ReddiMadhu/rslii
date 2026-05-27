import { getApiBase } from "./apiBase";

const API_BASE = getApiBase();

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function analyzeCode({ code, filename, enableLlm = false }) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({
      code,
      filename,
      enable_llm: enableLlm,
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    let message = "Analysis failed";
    if (body) {
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail.map((e) => e.msg).join("; ");
      }
    }
    throw new Error(message);
  }
  return res.json();
}

export async function parseCode({ code, filename }) {
  const res = await fetch(`${API_BASE}/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ code, filename }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    let message = "Parse failed";
    if (body?.detail) message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    throw new Error(message);
  }
  return res.json();
}

export function getDownloadUrl(sessionId, filename) {
  return `${API_BASE}/download/${encodeURIComponent(sessionId)}/${encodeURIComponent(filename)}`;
}

/** Bundled Claim Center HTM Excel — drop file at backend/static/Claim_Center_ADV_10.1_HTM.xlsx */
export const STATIC_HTM_OUTPUT_NAME = "Claim_Center_ADV_10.1_HTM.xlsx";

export function getStaticHtmDownloadUrl() {
  return `${API_BASE}/download/static/claim-center-htm`;
}

export async function validateSources({
  code,
  filename,
  fileMapping,
  filesByFieldName,
  enableLlm = false,
}) {
  const fd = new FormData();
  fd.append("code", code);
  fd.append("filename", filename || "pipeline.py");
  fd.append("enable_llm", enableLlm ? "true" : "false");
  fd.append("file_mapping", JSON.stringify(fileMapping || {}));
  Object.entries(filesByFieldName || {}).forEach(([field, file]) => {
    fd.append(field, file);
  });

  const res = await fetch(`${API_BASE}/validate-sources`, {
    method: "POST",
    credentials: "include",
    body: fd,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    let message = "Validation failed";
    if (body?.detail) {
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    }
    throw new Error(message);
  }
  return res.json();
}
