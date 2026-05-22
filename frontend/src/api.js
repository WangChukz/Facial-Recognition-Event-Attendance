const API = "/api";

/**
 * Extract a human-readable error message from a non-2xx response.
 * Handles three cases:
 *   1. FastAPI JSON error  → { detail: "..." }
 *   2. Nginx / proxy HTML  → strip tags, truncate
 *   3. Plain text          → use as-is
 */
async function extractErrorMessage(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      const json = await response.json();
      // FastAPI wraps validation errors in { detail: [...] } or { detail: "..." }
      if (json.detail) {
        return Array.isArray(json.detail)
          ? json.detail.map((e) => e.msg || JSON.stringify(e)).join("; ")
          : String(json.detail);
      }
      return JSON.stringify(json);
    } catch {
      // fall through
    }
  }

  // HTML (nginx 504 / 502 / etc.) — strip tags and trim
  if (contentType.includes("text/html")) {
    const text = await response.text();
    const plain = text.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    // Return a friendly message instead of raw HTML
    const statusText = response.statusText || "Server error";
    const hint =
      response.status === 504
        ? "Server mất quá nhiều thời gian xử lý. Vui lòng thử lại."
        : response.status === 502 || response.status === 503
        ? "Server tạm thời không phản hồi. Vui lòng thử lại sau."
        : `Lỗi ${response.status}: ${statusText}.`;
    return hint;
  }

  // Plain text fallback
  const text = await response.text();
  return text.trim() || `HTTP ${response.status}`;
}

export async function apiGet(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(await extractErrorMessage(r));
  return r.json();
}

export async function apiPost(path, body, isJson = true) {
  const opts = { method: "POST" };
  if (isJson) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(`${API}${path}`, opts);
  if (!r.ok) throw new Error(await extractErrorMessage(r));
  return r.json();
}

export async function apiPostForm(path, formData) {
  const r = await fetch(`${API}${path}`, { method: "POST", body: formData });
  if (!r.ok) throw new Error(await extractErrorMessage(r));
  return r.json();
}
