// Thin fetch wrapper over the SolarOps API — mirrors dashboard/api_client.py's
// shape and endpoints (Python side), just written for the browser instead.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const SITE_ID = import.meta.env.VITE_SITE_ID || "site-001";
const API_KEY = import.meta.env.VITE_API_KEY || "solarops-demo-key";

export class ApiError extends Error {
  constructor(statusCode, detail) {
    super(`API error ${statusCode}: ${detail}`);
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

export class ApiUnreachable extends Error {}

async function request(path, { method = "GET", auth = false, body = null } = {}) {
  const headers = {};
  if (auth) headers["X-API-Key"] = API_KEY;
  if (body !== null) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body !== null ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiUnreachable(`Cannot reach the API at ${BASE_URL}. Is it running?`);
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new ApiError(response.status, detail);
  }
  return response.json();
}

export const getState = () => request(`/sites/${SITE_ID}/state`);
export const getForecasts = () => request(`/sites/${SITE_ID}/forecasts`);
export const getAnomalies = () => request(`/sites/${SITE_ID}/anomalies`);
export const getRecommendations = () => request(`/sites/${SITE_ID}/recommendations`);
export const getPendingApprovals = () => request(`/sites/${SITE_ID}/approvals/pending`);
export const getCommands = () => request(`/sites/${SITE_ID}/commands`);
export const runDecisionCycle = () => request(`/sites/${SITE_ID}/decision-cycle`, { method: "POST" });

const OPERATOR_ID = "dashboard-react-operator";

export const approveCommand = (approvalId, reason = "") =>
  request(`/approvals/${approvalId}/approve`, {
    method: "POST",
    auth: true,
    body: { operator_id: OPERATOR_ID, reason },
  });
export const rejectCommand = (approvalId, reason = "") =>
  request(`/approvals/${approvalId}/reject`, {
    method: "POST",
    auth: true,
    body: { operator_id: OPERATOR_ID, reason },
  });

export { SITE_ID, BASE_URL };
