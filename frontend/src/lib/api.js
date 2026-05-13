const API_BASE = "/api";

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function analyzeCode({ code, filename, enableLlm = false }) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
