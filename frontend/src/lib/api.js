const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

/**
 * Get the current Supabase session token for API auth.
 * Returns empty string if not authenticated (public endpoints still work).
 */
function getAuthToken() {
  if (typeof window === "undefined") return "";
  try {
    // Supabase stores session in localStorage
    const storageKey = Object.keys(localStorage).find((k) =>
      k.startsWith("sb-") && k.endsWith("-auth-token")
    );
    if (storageKey) {
      const session = JSON.parse(localStorage.getItem(storageKey));
      return session?.access_token || "";
    }
  } catch {
    // Silently fail — public endpoints don't need auth
  }
  return "";
}

async function call(path, opts = {}) {
  const controller = new AbortController();
  const timeoutMs = opts.timeout || 30000;
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // Inject auth token
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...opts.headers,
  };

  try {
    const res = await fetch(`${API}${path}`, {
      headers,
      signal: controller.signal,
      ...opts,
    });
    clearTimeout(timer);

    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      if (!res.ok) throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
      return { raw: text };
    }

    if (res.ok) return data;

    // Parse standardized error format (reason/evidence/solution)
    const errMsg =
      data?.reason || data?.detail || data?.message || data?.error || text.slice(0, 200);
    const err = new Error(`API ${res.status}: ${errMsg}`);
    err.reason = data?.reason || "";
    err.evidence = data?.evidence || "";
    err.solution = data?.solution || "";
    err.statusCode = res.status;
    throw err;
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

  // AI Chat — Enhanced with full context injection
  askAI: (message, context = {}) =>
    call("/chat/ask", { method: "POST", body: JSON.stringify({ message, context }) }),

  chatMessage: (message, sessionId = "default", context = {}) =>
    call("/chat/message", { method: "POST", body: JSON.stringify({ message, session_id: sessionId, context }) }),

  // Stats
  getStats: (userId) => call(`/stats${userId ? `?user_id=${userId}` : ""}`),

  // Pre-Deploy Validation
  validatePreDeploy: (projectPath, platform) =>
    call("/validate/pre-deploy", { method: "POST", body: JSON.stringify({ project_path: projectPath, platform }) }),

  // Domain Search (DomScan API)
  searchDomains: (query) =>
    call("/domains/search", { method: "POST", body: JSON.stringify({ query }), timeout: 20000 }),

  suggestDomains: (query) =>
    call("/domains/suggestions", { method: "POST", body: JSON.stringify({ query }), timeout: 20000 }),

  // Payments (Razorpay)
  createPaymentOrder: (domains, totalAmountInr, userId, userEmail) =>
    call("/payments/create-order", {
      method: "POST",
      body: JSON.stringify({ domains, total_amount_inr: totalAmountInr, user_id: userId, user_email: userEmail }),
    }),

  verifyPayment: (orderId, paymentId, signature, userId, userEmail, domains) =>
    call("/payments/verify", {
      method: "POST",
      body: JSON.stringify({
        razorpay_order_id: orderId,
        razorpay_payment_id: paymentId,
        razorpay_signature: signature,
        user_id: userId,
        user_email: userEmail,
        domains,
      }),
    }),

  // Terminal History (REST fallback — no /api/v1 prefix, WebSocket router is at root)
  getTerminalHistory: (sessionId) =>
    fetch(`${API.replace("/api/v1", "")}/terminal/history/${sessionId}`, {
      headers: { ...( getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {}) },
    }).then((r) => r.json()),

  // Code Quality Scanner
  scanQuality: (projectPath, projectId = "") =>
    call("/quality/scan", {
      method: "POST",
      body: JSON.stringify({ project_path: projectPath, project_id: projectId }),
      timeout: 60000,
    }),

  getQualityScan: (projectId) => call(`/quality/scan/${projectId}`),

  aiFixIssue: (filePath, lineNumber, issueDescription, codeSnippet) =>
    call("/quality/fix", {
      method: "POST",
      body: JSON.stringify({
        file_path: filePath,
        line_number: lineNumber,
        issue_description: issueDescription,
        code_snippet: codeSnippet,
      }),
      timeout: 30000,
    }),

  // Rollback System
  getRollbackHistory: (projectId) => call(`/rollback/history/${projectId}`),

  executeRollback: (projectId, versionNumber, userId = "") =>
    call("/rollback/execute", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, version_number: versionNumber, user_id: userId }),
      timeout: 120000,
    }),

  deleteVersion: (projectId, version) =>
    call(`/rollback/history/${projectId}/${version}`, { method: "DELETE" }),
};

// Export WebSocket base URL for TerminalWS component
export { WS_BASE };
