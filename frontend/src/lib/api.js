const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function call(path, opts = {}) {
  const controller = new AbortController();
  const timeoutMs = opts.timeout || 30000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json", ...opts.headers },
      signal: controller.signal,
      ...opts,
    });
    clearTimeout(timer);

    // Parse response body
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      if (!res.ok) throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
      return { raw: text };
    }

    // 2xx and 202 are OK
    if (res.ok) return data;

    // Non-2xx: extract error message
    const errMsg = data?.detail || data?.message || data?.error || text.slice(0, 200);
    throw new Error(`API ${res.status}: ${errMsg}`);
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw err;
  }
}

export const api = {
  // Auth
  validatePassword: (password) =>
    call("/auth/validate-password", { method: "POST", body: JSON.stringify({ password }) }),

  registerProfile: (data) =>
    call("/auth/register-profile", { method: "POST", body: JSON.stringify(data) }),

  // Analysis — ZIP upload
  analyzeProject: (formData) =>
    fetch(`${API}/analyze/project`, { method: "POST", body: formData }).then((r) => r.json()),

  // Analysis — Folder upload (multiple files)
  analyzeFolder: (formData) =>
    fetch(`${API}/analyze/folder`, { method: "POST", body: formData }).then((r) => r.json()),

  analyzeGitHub: (url) =>
    call("/analyze/github", { method: "POST", body: JSON.stringify({ url }) }),

  // Deploy — Remote (Real APIs)
  deployProject: (data) =>
    call("/deploy/execute", { method: "POST", body: JSON.stringify(data) }),

  getDeployStatus: (id) => call(`/deploy/status/${id}`),

  getDeployList: (userId) => call(`/deploy/list${userId ? `?user_id=${userId}` : ""}`),

  // Deploy — Local (Subprocess) — longer timeout (2 min for npm install)
  deployLocal: (data) =>
    call("/deploy/local", { method: "POST", body: JSON.stringify(data), timeout: 120000 }),

  stopLocal: (pid) =>
    call("/deploy/local/stop", { method: "POST", body: JSON.stringify({ pid }) }),

  listLocal: () => call("/deploy/local/list"),

  // Domain
  searchDomain: (query) =>
    call("/domain/search", { method: "POST", body: JSON.stringify({ query }), timeout: 20000 }),

  // AI Chat
  askAI: (message, context = {}) =>
    call("/chat/ask", { method: "POST", body: JSON.stringify({ message, context }) }),

  // Stats
  getStats: (userId) => call(`/stats${userId ? `?user_id=${userId}` : ""}`),
};
